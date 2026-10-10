"""Robot state publisher for the trident model.

ros2 launch trident_description rsp.launch.py
ros2 launch trident_description rsp.launch.py use_sim_time:=true
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('trident_description')
    xacro_file = os.path.join(share, 'urdf', 'trident.urdf.xacro')

    # Run xacro at launch time so edits to the model need no extra step
    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use the Gazebo clock instead of wall time'),

        Node(package='robot_state_publisher', executable='robot_state_publisher',
             output='screen',
             parameters=[{'robot_description': robot_description,
                          'use_sim_time': ParameterValue(
                              LaunchConfiguration('use_sim_time'), value_type=bool)}]),
    ])
