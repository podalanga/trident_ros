#!/usr/bin/env python3
"""Gripper mimic for Gazebo Fortress, which ignores the URDF <mimic> tag.

Subscribes:  /gripper/command        std_msgs/Float64  drive-jaw angle in rad (+ closes)
Publishes:   /gripper/drive_cmd      std_msgs/Float64  +angle
             /gripper/follower_cmd   std_msgs/Float64  -angle  (equal gears, opposite rotation)

Example:  ros2 topic pub --once /gripper/command std_msgs/msg/Float64 "{data: -0.8}"   # open
          ros2 topic pub --once /gripper/command std_msgs/msg/Float64 "{data: 0.09}"   # close
"""
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


class GripperMimic(Node):
    def __init__(self):
        super().__init__('gripper_mimic')
        # Defaults match grip_lower / grip_upper in the xacro
        self.lower = self.declare_parameter('lower', -1.0).value
        self.upper = self.declare_parameter('upper', 0.09).value
        self.multiplier = self.declare_parameter('multiplier', -1.0).value
        self.drive_pub = self.create_publisher(Float64, '/gripper/drive_cmd', 10)
        self.follower_pub = self.create_publisher(Float64, '/gripper/follower_cmd', 10)
        self.create_subscription(Float64, '/gripper/command', self.on_command, 10)

    def on_command(self, msg: Float64):
        # NaN and inf would pass straight through the clamp below
        if not math.isfinite(msg.data):
            self.get_logger().warn(f'ignored non-finite command {msg.data}')
            return
        angle = min(max(msg.data, self.lower), self.upper)
        if angle != msg.data:
            self.get_logger().warn(f'clamped {msg.data:.3f} -> {angle:.3f} rad')
        self.drive_pub.publish(Float64(data=angle))
        self.follower_pub.publish(Float64(data=self.multiplier * angle))


def main():
    rclpy.init()
    node = GripperMimic()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
