"""Sleeping on the node's clock, so waits stay the right length when the simulation runs slow."""
import time

from rclpy.duration import Duration
from rclpy.node import Node


def sleep_for(node: Node, seconds: float):
    clock = node.get_clock()
    deadline = clock.now() + Duration(seconds=seconds)
    while clock.now() < deadline:
        time.sleep(0.01)
