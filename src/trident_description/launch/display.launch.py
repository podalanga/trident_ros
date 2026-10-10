"""RViz check of the model with joint sliders (no simulation).

ros2 launch trident_description display.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('trident_description')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'rsp.launch.py')))

    return LaunchDescription([
        rsp,

        # Sliders stand in for the simulator and publish /joint_states
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui'),

        Node(package='rviz2', executable='rviz2',
             arguments=['-d', os.path.join(share, 'rviz', 'display.rviz')]),
    ])
