"""Short straight moves measured on odometry, for backing off a stem without turning."""
import math
import time

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node


class BaseMotion:
    def __init__(self, node: Node, rate_hz: float = 20.0):
        self.period = 1.0 / rate_hz
        self.position = None
        self.cmd_pub = node.create_publisher(Twist, '/cmd_vel', 1)
        node.create_subscription(Odometry, '/odom', self._on_odom, 10)

    def _on_odom(self, msg: Odometry):
        self.position = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def drive(self, distance: float, speed: float):
        """Drive distance metres in a straight line, backwards when it is negative."""
        while self.position is None:
            time.sleep(self.period)
        start = self.position
        command = Twist()
        command.linear.x = math.copysign(speed, distance)
        while math.dist(start, self.position) < abs(distance):
            self.cmd_pub.publish(command)
            time.sleep(self.period)
        self.cmd_pub.publish(Twist())
