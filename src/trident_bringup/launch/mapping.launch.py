"""Build the arena map: the robot drives a survey route on its own while RTAB-Map records.

ros2 launch trident_bringup mapping.launch.py database:=/ws/maps/arena.db

The arena is mapped empty, so the obstacles of a later mission run are new to the robot.
Everything shuts down when the route is finished and the database is saved on the way out.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup = get_package_share_directory('trident_bringup')
    route = os.path.join(get_package_share_directory('trident_mission'), 'config', 'survey.yaml')

    survey = Node(package='trident_mission', executable='survey', output='screen',
                  parameters=[{'use_sim_time': True, 'route_file': route}])

    return LaunchDescription([
        DeclareLaunchArgument('database',
                              default_value=os.path.expanduser('~/.ros/trident_arena.db'),
                              description='Where to write the RTAB-Map database'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(bringup, 'launch', 'autonomy.launch.py')),
            launch_arguments={'mode': 'mapping', 'obstacles': 'none',
                              'database': LaunchConfiguration('database'),
                              'headless': LaunchConfiguration('headless'),
                              'rviz': LaunchConfiguration('rviz')}.items()),
        survey,
        RegisterEventHandler(OnProcessExit(target_action=survey,
                                           on_exit=[EmitEvent(event=Shutdown())])),
    ])
