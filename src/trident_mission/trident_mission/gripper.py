"""Open and close the jaws through /gripper/command (drive jaw angle in rad)."""
from rclpy.node import Node
from std_msgs.msg import Float64

from trident_mission.clock import sleep_for


class Gripper:
    def __init__(self, node: Node, open_angle: float, closed_angle: float, travel_time: float):
        self.open_angle = open_angle
        self.closed_angle = closed_angle
        self.travel_time = travel_time
        self.node = node
        self.pub = node.create_publisher(Float64, '/gripper/command', 10)

    def open(self):
        self._move(self.open_angle)

    def close(self):
        self._move(self.closed_angle)

    def _move(self, angle: float):
        self.pub.publish(Float64(data=angle))
        # There is no position feedback worth waiting on, the servo just needs its time
        sleep_for(self.node, self.travel_time)
