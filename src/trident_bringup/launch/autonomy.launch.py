"""Arena simulation with the full navigation stack: EKF odometry, RTAB-Map and Nav2.

ros2 launch trident_bringup autonomy.launch.py mode:=mapping obstacles:=none
ros2 launch trident_bringup autonomy.launch.py mode:=localization

Shared base of mapping.launch.py and mission.launch.py, usable on its own to send goals
from RViz.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def include(package, launch_file, **arguments):
    path = os.path.join(get_package_share_directory(package), 'launch', launch_file)
    return IncludeLaunchDescription(PythonLaunchDescriptionSource(path),
                                    launch_arguments=arguments.items())


def generate_launch_description():
    rviz_config = os.path.join(get_package_share_directory('trident_description'), 'rviz',
                               'autonomy.rviz')

    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='localization',
                              choices=['mapping', 'localization'],
                              description='Build the map or localise in the saved one'),
        DeclareLaunchArgument('database',
                              default_value=os.path.expanduser('~/.ros/trident_arena.db'),
                              description='RTAB-Map database file'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run the Gazebo server without its GUI'),
        DeclareLaunchArgument('rviz', default_value='true', description='Open RViz'),
        DeclareLaunchArgument('pick_order', default_value='RGB',
                              description='Coin colours of bays 1 to 3'),
        DeclareLaunchArgument('drop_order', default_value='BRG',
                              description='Colours of drop zones 1 to 3'),
        DeclareLaunchArgument('obstacles', default_value='a',
                              description='Obstacle preset a, b, c or none'),
        DeclareLaunchArgument('ir_noise', default_value='0.05',
                              description='Standard deviation of the IR readings in volts'),

        include('trident_gazebo', 'sim.launch.py',
                world='arena', ekf='true',
                headless=LaunchConfiguration('headless'),
                pick_order=LaunchConfiguration('pick_order'),
                drop_order=LaunchConfiguration('drop_order'),
                obstacles=LaunchConfiguration('obstacles'),
                ir_noise=LaunchConfiguration('ir_noise')),
        include('trident_navigation', 'odometry.launch.py'),
        include('trident_navigation', 'slam.launch.py',
                mode=LaunchConfiguration('mode'), database=LaunchConfiguration('database')),
        include('trident_navigation', 'navigation.launch.py'),

        Node(package='rviz2', executable='rviz2',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', rviz_config],
             parameters=[{'use_sim_time': True}]),
    ])
