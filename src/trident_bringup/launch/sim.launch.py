"""Full trident simulation: Gazebo, RViz and optional joystick teleop.

ros2 launch trident_bringup sim.launch.py
ros2 launch trident_bringup sim.launch.py world:=empty rviz:=false
ros2 launch trident_bringup sim.launch.py teleop:=true controller:=ps4
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    description_share = get_package_share_directory('trident_description')
    gazebo_share = get_package_share_directory('trident_gazebo')
    teleop_share = get_package_share_directory('trident_teleop')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_share, 'launch', 'sim.launch.py')),
        launch_arguments={'world': LaunchConfiguration('world'),
                          'headless': LaunchConfiguration('headless')}.items())

    teleop = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(teleop_share, 'launch', 'teleop.launch.py')),
        launch_arguments={'controller': LaunchConfiguration('controller'),
                          'joy_dev': LaunchConfiguration('joy_dev')}.items(),
        condition=IfCondition(LaunchConfiguration('teleop')))

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='maze',
                              description='World name in trident_gazebo/worlds (maze or empty)'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run the Gazebo server without its GUI'),
        DeclareLaunchArgument('rviz', default_value='true', description='Open RViz'),
        DeclareLaunchArgument('teleop', default_value='false',
                              description='Start joystick teleop with the simulation'),
        DeclareLaunchArgument('controller', default_value='xbox', choices=['xbox', 'ps4'],
                              description='Controller mapping used when teleop is on'),
        DeclareLaunchArgument('joy_dev', default_value='/dev/input/js0',
                              description='Joystick device used when teleop is on'),

        sim,
        teleop,

        Node(package='rviz2', executable='rviz2',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', os.path.join(description_share, 'rviz', 'sim.rviz')],
             parameters=[{'use_sim_time': True}]),
    ])
