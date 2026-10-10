#!/usr/bin/env python3
"""Scores a mission run from Gazebo's ground truth.

Subscribes:  /sim/poses       tf2_msgs/TFMessage   poses of the coins (bridged from Gazebo)
             /mission/state   std_msgs/String      to know when the run is over
Publishes:   /referee/score   std_msgs/String      one line per change, for example
                                                   "2 of 3 coins home: red, blue"

A coin is home when its centre lies inside the drop square whose QR names its colour.
drop_order is the same RGB permutation the world was launched with.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage

COLOUR_OF = {'R': 'red', 'G': 'green', 'B': 'blue'}


class Referee(Node):
    def __init__(self):
        super().__init__('referee')
        drop_order = self.declare_parameter('drop_order', 'BRG').value
        self.zone_x = self.declare_parameter('zone_x', 3.0).value
        zone_ys = self.declare_parameter('zone_ys', [0.7, 0.2, -0.3]).value
        self.half = self.declare_parameter('zone_size', 0.25).value / 2.0

        # Which square each colour belongs in
        self.target_y = {COLOUR_OF[letter]: y for letter, y in zip(drop_order, zone_ys)}
        self.home = set()
        self.reported = None

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.score_pub = self.create_publisher(String, '/referee/score', latched)
        self.create_subscription(TFMessage, '/sim/poses', self.on_poses, 10)
        self.create_subscription(String, '/mission/state', self.on_state, latched)

    def on_poses(self, msg: TFMessage):
        for transform in msg.transforms:
            name = transform.child_frame_id
            if not name.startswith('coin_'):
                continue
            colour = name[len('coin_'):]
            position = transform.transform.translation
            inside = (abs(position.x - self.zone_x) <= self.half
                      and abs(position.y - self.target_y[colour]) <= self.half)
            if inside:
                self.home.add(colour)
            else:
                self.home.discard(colour)
        self.report()

    def report(self):
        names = ', '.join(sorted(self.home)) or 'none'
        line = f'{len(self.home)} of {len(self.target_y)} coins home: {names}'
        if line != self.reported:
            self.reported = line
            self.score_pub.publish(String(data=line))
            self.get_logger().info(line)

    def on_state(self, msg: String):
        if msg.data in ('DONE', 'FAILED'):
            verdict = 'PASS' if len(self.home) == len(self.target_y) else 'FAIL'
            self.get_logger().info(f'Mission {msg.data}. Referee verdict: {verdict} ({self.reported})')


def main():
    rclpy.init()
    node = Referee()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
