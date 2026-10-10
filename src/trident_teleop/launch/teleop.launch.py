"""Joystick teleop for the trident robot: base on /cmd_vel, gripper on /gripper/command.

ros2 launch trident_teleop teleop.launch.py controller:=xbox
ros2 launch trident_teleop teleop.launch.py controller:=ps4 joy_dev:=/dev/input/js1
ros2 launch trident_teleop teleop.launch.py controller:=generic
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('trident_teleop')

    # One yaml per controller holds the parameters for all three nodes
    config = PathJoinSubstitution(
        [share, 'config', [LaunchConfiguration('controller'), '.yaml']])

    return LaunchDescription([
        DeclareLaunchArgument('controller', default_value='xbox',
                              choices=['xbox', 'ps4', 'generic'],
                              description='Which controller mapping to load'),
        DeclareLaunchArgument('joy_dev', default_value='/dev/input/js0',
                              description='Joystick device, see ls /dev/input/js*'),

        Node(package='joy_linux', executable='joy_linux_node', output='screen',
             parameters=[config, {'dev': LaunchConfiguration('joy_dev')}]),

        Node(package='teleop_twist_joy', executable='teleop_node',
             name='teleop_twist_joy_node', output='screen',
             parameters=[config]),

        Node(package='trident_teleop', executable='gripper_teleop.py', output='screen',
             parameters=[config]),
    ])
