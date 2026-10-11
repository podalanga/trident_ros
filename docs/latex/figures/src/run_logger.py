#!/usr/bin/env python3
"""Records one simulation run for the report. It only listens, it never commands the robot.

Writes into the folder given by the out parameter:
  track.csv    10 Hz: sim time, true pose, SLAM pose (map to base_footprint), odometry pose
  events.csv   mission states, referee lines and gripper commands, each with the true pose
  coins.csv    final true position of every coin

The node exits a few seconds after the mission reports DONE or FAILED.
"""
import csv
import math
import os

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from rclpy.time import Time
from std_msgs.msg import Float64, String
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class RunLogger(Node):
    def __init__(self):
        super().__init__('run_logger')
        self.out = self.declare_parameter('out', '/tmp/run').value
        self.settle = self.declare_parameter('settle', 3.0).value
        os.makedirs(self.out, exist_ok=True)

        self.track_file = open(os.path.join(self.out, 'track.csv'), 'w', newline='')
        self.track = csv.writer(self.track_file)
        self.track.writerow(['t', 'x', 'y', 'yaw', 'map_x', 'map_y', 'map_yaw',
                             'odom_x', 'odom_y', 'odom_yaw'])
        self.events_file = open(os.path.join(self.out, 'events.csv'), 'w', newline='')
        self.events = csv.writer(self.events_file)
        self.events.writerow(['t', 'kind', 'text', 'x', 'y', 'yaw'])

        self.truth = None
        self.odom = (math.nan, math.nan, math.nan)
        self.coins = {}
        self.last_row = -1.0
        self.finished_at = None
        self.done = False

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(TFMessage, '/sim/poses', self.on_poses, 10)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(String, '/mission/state', self.on_state, latched)
        self.create_subscription(String, '/referee/score', self.on_score, latched)
        self.create_subscription(Float64, '/gripper/command', self.on_gripper, 10)

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def event(self, kind, text):
        pose = self.truth or (math.nan, math.nan, math.nan)
        self.events.writerow([f'{self.now():.3f}', kind, text] + [f'{v:.4f}' for v in pose])
        self.events_file.flush()

    def on_state(self, msg):
        self.event('state', msg.data)
        if msg.data in ('DONE', 'FAILED'):
            self.finished_at = self.now()

    def on_score(self, msg):
        self.event('score', msg.data)

    def on_gripper(self, msg):
        self.event('gripper', f'{msg.data:.2f}')

    def on_odom(self, msg):
        p = msg.pose.pose
        self.odom = (p.position.x, p.position.y, yaw_of(p.orientation))

    def slam_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform('map', 'base_footprint', Time()).transform
        except Exception:
            return (math.nan, math.nan, math.nan)
        return (tf.translation.x, tf.translation.y, yaw_of(tf.rotation))

    def on_poses(self, msg):
        for transform in msg.transforms:
            name = transform.child_frame_id
            t = transform.transform.translation
            if name == 'trident':
                self.truth = (t.x, t.y, yaw_of(transform.transform.rotation))
            elif name.startswith('coin_'):
                self.coins[name] = (t.x, t.y)
        now = self.now()
        if self.truth is not None and now - self.last_row >= 0.1:
            self.last_row = now
            row = [now, *self.truth, *self.slam_pose(), *self.odom]
            self.track.writerow([f'{v:.4f}' for v in row])
        if self.finished_at is not None and now - self.finished_at > self.settle:
            self.finish()

    def finish(self):
        if self.done:
            return
        self.done = True
        with open(os.path.join(self.out, 'coins.csv'), 'w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['coin', 'x', 'y'])
            for name, (x, y) in sorted(self.coins.items()):
                writer.writerow([name, f'{x:.4f}', f'{y:.4f}'])
        self.track_file.close()
        self.events_file.close()


def main():
    rclpy.init()
    node = RunLogger()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        node.finish()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
