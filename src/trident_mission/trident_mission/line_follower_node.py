"""Line follower on the IR array, offered as the follow_line action.

Subscribes:  /ir/analog   std_msgs/Float32MultiArray   one voltage per channel
             /odom        nav_msgs/Odometry            to measure the distance driven
Publishes:   /cmd_vel     geometry_msgs/Twist          only while a goal is running
Action:      follow_line  trident_interfaces/FollowLine

A goal drives forward and steers onto the line until the array reaches a marker or the
distance limit. With no line in view yet it drives straight, so a goal can start a little
short of a stem.
"""
import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float32MultiArray
from trident_interfaces.action import FollowLine

from trident_mission.line_tracking import (ArrayGeometry, MarkerDetector, Steering, dark_count,
                                           line_offset)


class LineFollower(Node):
    def __init__(self):
        super().__init__('line_follower')
        self.speed = self.declare_parameter('speed', 0.10).value
        self.search_turn = self.declare_parameter('search_turn', 0.6).value
        self.min_darkness = self.declare_parameter('min_darkness', 0.15).value
        self.dark_level = self.declare_parameter('dark_level', 0.5).value
        self.rate_hz = self.declare_parameter('rate', 20.0).value
        self.geometry = ArrayGeometry(pitch=self.declare_parameter('pitch', 0.015).value,
                                      v_ref=self.declare_parameter('v_ref', 5.0).value)
        self.steering = Steering(kp=self.declare_parameter('kp', 45.0).value,
                                 kd=self.declare_parameter('kd', 2.0).value,
                                 max_turn=self.declare_parameter('max_turn', 1.5).value)
        self.marker = MarkerDetector(
            min_channels=self.declare_parameter('marker_channels', 6).value,
            min_samples=self.declare_parameter('marker_samples', 2).value)

        self.volts = None
        self.position = None

        group = ReentrantCallbackGroup()
        self.create_subscription(Float32MultiArray, '/ir/analog', self.on_ir,
                                 qos_profile_sensor_data, callback_group=group)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10, callback_group=group)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 1)
        self.server = ActionServer(self, FollowLine, 'follow_line', self.follow,
                                   cancel_callback=lambda _: CancelResponse.ACCEPT,
                                   callback_group=group)

    def on_ir(self, msg: Float32MultiArray):
        self.volts = list(msg.data)

    def on_odom(self, msg: Odometry):
        self.position = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def follow(self, goal_handle):
        goal = goal_handle.request
        speed = goal.speed if goal.speed > 0.0 else self.speed
        rate = self.create_rate(self.rate_hz)
        period = 1.0 / self.rate_hz

        while rclpy.ok() and (self.volts is None or self.position is None):
            rate.sleep()

        self.steering.reset()
        self.marker.reset()
        start = self.position
        last_offset = None
        result = FollowLine.Result()

        while rclpy.ok():
            result.distance = math.dist(start, self.position)
            if goal_handle.is_cancel_requested:
                self.stop()
                goal_handle.canceled()
                return result
            if self.marker.update(dark_count(self.volts, self.geometry, self.dark_level)):
                result.reached_marker = True
                break
            if result.distance >= goal.max_distance:
                break

            offset = line_offset(self.volts, self.geometry, self.min_darkness)
            command = Twist()
            command.linear.x = speed
            if offset is not None:
                command.angular.z = self.steering.turn_rate(offset, period)
                last_offset = offset
            elif last_offset is not None:
                # The line slid off one end of the array: swing back toward that side
                command.angular.z = math.copysign(self.search_turn, last_offset)
            self.cmd_pub.publish(command)

            goal_handle.publish_feedback(FollowLine.Feedback(
                offset=offset if offset is not None else float('nan'), distance=result.distance))
            rate.sleep()

        self.stop()
        goal_handle.succeed()
        return result

    def stop(self):
        self.cmd_pub.publish(Twist())


def main():
    rclpy.init()
    node = LineFollower()
    try:
        rclpy.spin(node, executor=MultiThreadedExecutor())
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
