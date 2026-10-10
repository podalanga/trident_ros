"""Gazebo Fortress simulation of the trident robot (no RViz, no teleop).

ros2 launch trident_gazebo sim.launch.py
ros2 launch trident_gazebo sim.launch.py world:=line
ros2 launch trident_gazebo sim.launch.py x:=-9.0 y:=-9.0 headless:=true
ros2 launch trident_gazebo sim.launch.py follow:=true follow_distance:=0.6
ros2 launch trident_gazebo sim.launch.py world:=arena pick_order:=GBR drop_order:=RGB obstacles:=b
"""
import os
import tempfile

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument, ExecuteProcess,
                            IncludeLaunchDescription, OpaqueFunction)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

# Arguments handed to worlds written as xacro. Plain .sdf worlds ignore them.
WORLD_ARGS = ('pick_order', 'drop_order', 'obstacles')


def resolve_world(context, gazebo_share):
    """Return the path of the world file, expanding <name>.sdf.xacro into a temp file first."""
    name = LaunchConfiguration('world').perform(context)
    worlds = os.path.join(gazebo_share, 'worlds')
    template = os.path.join(worlds, name + '.sdf.xacro')
    if not os.path.exists(template):
        return os.path.join(worlds, name + '.sdf')

    mappings = {arg: LaunchConfiguration(arg).perform(context) for arg in WORLD_ARGS}
    mappings['textures'] = os.path.join(gazebo_share, 'textures')
    world_file = os.path.join(tempfile.gettempdir(), f'trident_{name}.sdf')
    with open(world_file, 'w') as out:
        out.write(xacro.process_file(template, mappings=mappings).toxml())
    return world_file


def launch_gazebo(context):
    gazebo_share = get_package_share_directory('trident_gazebo')
    headless = LaunchConfiguration('headless').perform(context) == 'true'
    # -r starts the sim running, -s skips the GUI when headless
    flags = '-r -s ' if headless else '-r '
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': flags + resolve_world(context, gazebo_share)}.items())]


def bridge(name, config, **kwargs):
    return Node(package='ros_gz_bridge', executable='parameter_bridge', name=name, output='screen',
                parameters=[{'config_file': config, 'use_sim_time': True}], **kwargs)


def generate_launch_description():
    description_share = get_package_share_directory('trident_description')
    config = os.path.join(get_package_share_directory('trident_gazebo'), 'config')
    use_ekf = LaunchConfiguration('ekf')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(description_share, 'launch', 'rsp.launch.py')),
        launch_arguments={'use_sim_time': 'true'}.items())

    # Gazebo's own follow offset is 5 m back and 3 m up, far too wide for a robot this small.
    # The GUI takes a while to open, so the follow request is retried until it answers, then
    # the offset is set (it is ignored unless a follow target exists). Offset is in the robot
    # frame, so the camera stays behind the robot as it turns.
    ign_bool = '--reptype ignition.msgs.Boolean --timeout 1000'
    follow_camera = ExecuteProcess(
        cmd=['bash', '-c', [
            'for i in $(seq 60); do ign service -s /gui/follow --reqtype ignition.msgs.StringMsg ',
            ign_bool, ' --req \'data: "trident"\' 2>/dev/null | grep -q true && break; sleep 1; done; ',
            'ign service -s /gui/follow/offset --reqtype ignition.msgs.Vector3d ', ign_bool,
            " --req 'x: -", LaunchConfiguration('follow_distance'),
            ', y: 0, z: ', LaunchConfiguration('follow_height'), "'"]],
        condition=IfCondition(PythonExpression(
            ["'", LaunchConfiguration('follow'), "' == 'true' and '",
             LaunchConfiguration('headless'), "' != 'true'"])),
        output='screen')

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='maze',
                              description='World in trident_gazebo/worlds: maze, line, empty or arena'),
        DeclareLaunchArgument('x', default_value='0.0', description='Spawn x in metres'),
        DeclareLaunchArgument('y', default_value='0.0', description='Spawn y in metres'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='Spawn heading in radians'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Run the Gazebo server without its GUI'),
        DeclareLaunchArgument('follow', default_value='false',
                              description='Make the Gazebo GUI camera follow the robot'),
        DeclareLaunchArgument('follow_distance', default_value='0.4',
                              description='Follow camera distance behind the robot in metres'),
        DeclareLaunchArgument('follow_height', default_value='0.25',
                              description='Follow camera height above the robot in metres'),
        DeclareLaunchArgument('ekf', default_value='false',
                              description='Bridge wheel odometry and IMU for an EKF instead of '
                                          'taking /odom and its transform straight from Gazebo'),
        DeclareLaunchArgument('ir_noise', default_value='0.0',
                              description='Standard deviation of the IR readings in volts'),
        DeclareLaunchArgument('pick_order', default_value='RGB',
                              description='Arena only: coin colours of bays 1 to 3'),
        DeclareLaunchArgument('drop_order', default_value='BRG',
                              description='Arena only: colours of drop zones 1 to 3'),
        DeclareLaunchArgument('obstacles', default_value='a',
                              description='Arena only: obstacle preset a, b, c or none'),

        # Lets Gazebo resolve package://trident_description/meshes/...
        AppendEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', os.path.dirname(description_share)),

        OpaqueFunction(function=launch_gazebo),
        rsp,
        follow_camera,

        # Spawn the robot from the /robot_description topic, slightly above the floor
        Node(package='ros_gz_sim', executable='create', output='screen',
             arguments=['-topic', 'robot_description', '-name', 'trident',
                        '-x', LaunchConfiguration('x'), '-y', LaunchConfiguration('y'),
                        '-z', '0.01', '-Y', LaunchConfiguration('yaw')]),

        bridge('bridge_common', os.path.join(config, 'bridge_common.yaml')),
        bridge('bridge_odom', os.path.join(config, 'bridge_odom_raw.yaml'),
               condition=UnlessCondition(use_ekf)),
        bridge('bridge_odom', os.path.join(config, 'bridge_odom_ekf.yaml'),
               condition=IfCondition(use_ekf)),

        # These two do not use time, so they stay off the 1 kHz /clock topic
        Node(package='trident_gazebo', executable='gripper_mimic.py', output='screen'),

        Node(package='trident_gazebo', executable='ir_array.py', output='screen',
             parameters=[{'noise_stddev': LaunchConfiguration('ir_noise')}]),

        # Coloured point cloud from the depth image, in the optical frame like a real RealSense
        Node(package='depth_image_proc', executable='point_cloud_xyzrgb_node', output='screen',
             parameters=[{'use_sim_time': True}],
             remappings=[('rgb/camera_info', '/camera/color/camera_info'),
                         ('rgb/image_rect_color', '/camera/color/image_raw'),
                         ('depth_registered/image_rect', '/camera/depth/image_rect_raw'),
                         ('points', '/camera/depth/color/points')]),
    ])
