"""Gazebo Fortress simulation of the trident robot (no RViz, no teleop).

ros2 launch trident_gazebo sim.launch.py
ros2 launch trident_gazebo sim.launch.py world:=empty
ros2 launch trident_gazebo sim.launch.py x:=-9.0 y:=-9.0 headless:=true
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                            IncludeLaunchDescription)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    description_share = get_package_share_directory('trident_description')
    gazebo_share = get_package_share_directory('trident_gazebo')
    bridge_cfg = os.path.join(gazebo_share, 'config', 'ros_gz_bridge.yaml')

    # World is picked by name from this package's worlds folder
    world_file = PathJoinSubstitution(
        [gazebo_share, 'worlds', [LaunchConfiguration('world'), '.sdf']])

    # -r starts the sim running, -s skips the GUI when headless
    gz_flags = PythonExpression(
        ["'-r -s ' if '", LaunchConfiguration('headless'), "' == 'true' else '-r '"])

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': [gz_flags, world_file]}.items())

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(description_share, 'launch', 'rsp.launch.py')),
        launch_arguments={'use_sim_time': 'true'}.items())

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='maze',
                              description='World name in trident_gazebo/worlds (maze or empty)'),
        DeclareLaunchArgument('x', default_value='0.0', description='Spawn x in metres'),
        DeclareLaunchArgument('y', default_value='0.0', description='Spawn y in metres'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='Spawn heading in radians'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run the Gazebo server without its GUI'),

        # Lets Gazebo resolve package://trident_description/meshes/...
        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', os.path.dirname(description_share)),

        gz_sim,
        rsp,

        # Spawn the robot from the /robot_description topic, slightly above the floor
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-topic', 'robot_description', '-name', 'trident',
                        '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'),
                        '-z', '0.01', '-Y', LaunchConfiguration('yaw')]),

        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': bridge_cfg, 'use_sim_time': True}]),

        Node(package='trident_gazebo', executable='gripper_mimic.py', output='screen',
             parameters=[{'use_sim_time': True}]),
    ])
