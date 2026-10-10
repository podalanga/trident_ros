"""EKF that fuses wheel odometry and the IMU into /odom and the odom to base_footprint transform.

ros2 launch trident_navigation odometry.launch.py

Needs /wheel/odom and /imu, which the simulation provides when started with ekf:=true.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('trident_navigation'), 'config', 'ekf.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
             output='screen',
             parameters=[config, {'use_sim_time': LaunchConfiguration('use_sim_time')}],
             remappings=[('odometry/filtered', '/odom')]),
    ])
