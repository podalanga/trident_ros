"""Thin wrapper around Nav2's BasicNavigator: goals as (x, y, yaw) in the map frame."""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.parameter import Parameter
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


def make_pose(x: float, y: float, yaw: float, frame: str = 'map') -> PoseStamped:
    """Pose with a zero stamp, which Nav2 reads as "use the newest transform"."""
    pose = PoseStamped()
    pose.header.frame_id = frame
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


class Navigator:
    def __init__(self, use_sim_time: bool = True):
        self.nav = BasicNavigator()
        self.nav.set_parameters([Parameter('use_sim_time', value=use_sim_time)])
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.nav)

    def wait_until_ready(self):
        # There is no AMCL to wait for (RTAB-Map localises), so wait on the controller instead
        self.nav.waitUntilNav2Active(localizer='controller_server')

    def wait_until_localized(self, base_frame: str = 'base_footprint'):
        """Block until RTAB-Map has recognised the surroundings and published map to odom."""
        while rclpy.ok() and not self.tf_buffer.can_transform('map', base_frame, Time()):
            rclpy.spin_once(self.nav, timeout_sec=0.1)

    def go_to(self, x: float, y: float, yaw: float) -> bool:
        self.nav.goToPose(make_pose(x, y, yaw))
        return self._wait()

    def spin(self, angle: float) -> bool:
        self.nav.spin(spin_dist=angle, time_allowance=60)
        return self._wait()

    def _wait(self) -> bool:
        while rclpy.ok() and not self.nav.isTaskComplete():
            pass   # isTaskComplete spins the node for 0.1 s on every call
        return self.nav.getResult() == TaskResult.SUCCEEDED

    def shutdown(self):
        self.nav.destroy_node()
