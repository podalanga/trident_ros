"""Run the full mission in the arena: entry line, drop zone survey, three coins delivered.

ros2 launch trident_bringup mission.launch.py database:=/ws/maps/arena.db
ros2 launch trident_bringup mission.launch.py pick_order:=GBR drop_order:=RGB obstacles:=b

Needs the map from mapping.launch.py. The referee prints the score as coins arrive.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup = get_package_share_directory('trident_bringup')
    gazebo_config = os.path.join(get_package_share_directory('trident_gazebo'), 'config')
    mission_config = os.path.join(get_package_share_directory('trident_mission'), 'config')
    mission_params = os.path.join(mission_config, 'mission.yaml')
    sim_time = {'use_sim_time': True}

    passed_on = ('database', 'headless', 'rviz', 'pick_order', 'drop_order', 'obstacles')

    return LaunchDescription([
        DeclareLaunchArgument('database',
                              default_value=os.path.expanduser('~/.ros/trident_arena.db'),
                              description='RTAB-Map database written by the mapping run'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('pick_order', default_value='RGB',
                              description='Coin colours of bays 1 to 3'),
        DeclareLaunchArgument('drop_order', default_value='BRG',
                              description='Colours of drop zones 1 to 3'),
        DeclareLaunchArgument('obstacles', default_value='a',
                              description='Obstacle preset a, b, c or none'),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(bringup, 'launch', 'autonomy.launch.py')),
            launch_arguments={'mode': 'localization',
                              **{name: LaunchConfiguration(name) for name in passed_on}}.items()),

        Node(package='zbar_ros', executable='barcode_reader', output='screen',
             parameters=[sim_time],
             remappings=[('image', '/camera/color/image_raw')]),

        Node(package='trident_mission', executable='line_follower', output='screen',
             parameters=[mission_params, sim_time]),

        Node(package='trident_mission', executable='mission', output='screen',
             parameters=[mission_params, sim_time,
                         {'stations_file': os.path.join(mission_config, 'stations.yaml')}]),

        # Referee: ground truth in, score out. Kept apart from everything the robot uses.
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='bridge_referee',
             output='screen',
             parameters=[{'config_file': os.path.join(gazebo_config, 'bridge_referee.yaml')},
                         sim_time]),
        Node(package='trident_gazebo', executable='referee.py', output='screen',
             parameters=[os.path.join(gazebo_config, 'referee.yaml'), sim_time,
                         {'drop_order': LaunchConfiguration('drop_order')}]),
    ])
