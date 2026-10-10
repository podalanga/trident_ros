"""Blocking client for the follow_line action."""
import time
from typing import Tuple

from rclpy.action import ActionClient
from rclpy.node import Node
from trident_interfaces.action import FollowLine


class LineClient:
    def __init__(self, node: Node):
        self.client = ActionClient(node, FollowLine, 'follow_line')

    def wait_until_ready(self):
        self.client.wait_for_server()

    def follow(self, max_distance: float, speed: float = 0.0) -> Tuple[bool, float]:
        """Follow the line to the next marker. Returns (reached_marker, distance driven)."""
        goal = FollowLine.Goal(max_distance=max_distance, speed=speed)
        handle = self._wait(self.client.send_goal_async(goal))
        result = self._wait(handle.get_result_async()).result
        return result.reached_marker, result.distance

    @staticmethod
    def _wait(future):
        # The node is spun by a background executor, so polling is enough here
        while not future.done():
            time.sleep(0.02)
        return future.result()
