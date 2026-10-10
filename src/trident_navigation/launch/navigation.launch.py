"""Nav2 planning and control on top of the RTAB-Map map.

ros2 launch trident_navigation navigation.launch.py

Needs the map to odom transform and /map from slam.launch.py, and /odom from
odometry.launch.py. There is no AMCL or map server here: RTAB-Map does both jobs.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    config = os.path.join(get_package_share_directory('trident_navigation'), 'config')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # The tree has to be given as an absolute path, which is only known at launch time
    params = RewrittenYaml(
        source_file=os.path.join(config, 'nav2.yaml'),
        param_rewrites={
            'default_nav_to_pose_bt_xml': os.path.join(config, 'navigate_no_backup.xml')},
        convert_types=True)

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('nav2_bringup'), 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time, 'params_file': params}.items())

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        # The full 848 x 480 cloud is far more than a costmap needs. This one keeps every
        # fourth pixel and merges points into 2 cm cells.
        Node(package='rtabmap_util', executable='point_cloud_xyz', name='nav_cloud',
             output='screen',
             parameters=[{'use_sim_time': use_sim_time, 'decimation': 4, 'voxel_size': 0.02,
                          'min_depth': 0.2, 'max_depth': 3.0, 'approx_sync': False}],
             remappings=[('depth/image', '/camera/depth/image_rect_raw'),
                         ('depth/camera_info', '/camera/color/camera_info'),
                         ('cloud', '/camera/depth/points_nav')]),

        nav2,
    ])
