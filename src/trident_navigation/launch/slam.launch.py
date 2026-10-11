"""RTAB-Map visual SLAM, either building the map or localising in a saved one.

ros2 launch trident_navigation slam.launch.py mode:=mapping database:=/ws/maps/arena.db
ros2 launch trident_navigation slam.launch.py mode:=localization database:=/ws/maps/arena.db

Mapping starts from an empty database, so the map frame begins at the robot's start pose.
Localisation loads the database read only and publishes map to odom once it recognises a view.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

DEFAULT_DATABASE = os.path.expanduser('~/.ros/trident_arena.db')

CAMERA_TOPICS = [('rgb/image', '/camera/color/image_raw'),
                 ('rgb/camera_info', '/camera/color/camera_info'),
                 ('depth/image', '/camera/depth/image_rect_raw')]


def generate_launch_description():
    config = os.path.join(get_package_share_directory('trident_navigation'), 'config',
                          'rtabmap.yaml')
    common = [config, {'use_sim_time': LaunchConfiguration('use_sim_time'),
                       'database_path': LaunchConfiguration('database')}]
    mapping = PythonExpression(["'", LaunchConfiguration('mode'), "' == 'mapping'"])

    def rtabmap(extra, **kwargs):
        return Node(package='rtabmap_slam', executable='rtabmap', name='rtabmap', output='screen',
                    parameters=common + [extra], remappings=CAMERA_TOPICS, **kwargs)

    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='localization',
                              choices=['mapping', 'localization']),
        DeclareLaunchArgument('database', default_value=DEFAULT_DATABASE,
                              description='RTAB-Map database file'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        # -d wipes the old database so every mapping run starts clean.
        # A node is added every 10 cm or 0.2 rad of travel.
        rtabmap({'Mem/IncrementalMemory': 'true',
                 'RGBD/LinearUpdate': '0.10', 'RGBD/AngularUpdate': '0.20'},
                arguments=['-d'], condition=IfCondition(mapping)),

        # The whole saved map is loaded up front so the robot can localise from anywhere.
        # Every new fix is checked against the last 50 views and the odometry between them.
        # That history is what rejects a look-alike view, such as the QR code of the same
        # colour on another wall. Views are only added while moving, so standing in front
        # of a QR code does not flush the history.
        # The robot spawns where the mapping run began, so it starts at the map origin.
        # Otherwise RTAB-Map resumes from the pose where the previous run was shut down.
        rtabmap({'Mem/IncrementalMemory': 'false', 'Mem/InitWMWithAllNodes': 'true',
                 'RGBD/StartAtOrigin': 'true',
                 'RGBD/LinearUpdate': '0.05', 'RGBD/AngularUpdate': '0.05',
                 'RGBD/MaxOdomCacheSize': '50'},
                condition=UnlessCondition(mapping)),
    ])
