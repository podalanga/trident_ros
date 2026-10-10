# trident_ros

ROS 2 Humble + Gazebo Fortress simulation of the trident differential drive robot
(gripper, Intel D435 depth camera), with joystick teleop for Xbox and PS4 controllers.
Everything runs in an unprivileged Docker container.

## Layout

```
docker/                  Dockerfile, compose.yaml and run.sh
src/
  trident_description/   URDF (xacro), meshes, RViz configs
  trident_gazebo/        worlds, ROS to Gazebo bridge, simulation launch
  trident_teleop/        controller configs and teleop launch
  trident_bringup/       top level launch: sim + RViz + optional teleop
```

## Quick start

```bash
./docker/run.sh image      # build the Docker image (once)
./docker/run.sh up         # start the container
./docker/run.sh build      # colcon build
./docker/run.sh sim        # Gazebo + RViz in the maze world
```

In a second terminal, with the controller plugged in:

```bash
./docker/run.sh teleop xbox                    # or ps4
./docker/run.sh teleop ps4 /dev/input/js1      # if the pad is not js0
```

Other commands: `display` (RViz with joint sliders), `sim empty`, `shell`, `clean`, `down`.
`./docker/run.sh help` lists them all. Inside the container shell the same script is at
`/ws/docker/run.sh`, and plain `ros2 launch` works as well.

## Controls

| Action | Xbox | PS4 |
|---|---|---|
| Enable driving (hold) | LB | L1 |
| Turbo (hold) | RB | R1 |
| Forward / back | left stick | left stick |
| Turn | right stick | right stick |
| Close gripper | A | Cross |
| Open gripper | B | Circle |

Normal speed is 0.2 m/s and 1.5 rad/s, turbo is 0.5 m/s and 3.0 rad/s.
Mappings live in `src/trident_teleop/config/`. If a button does something unexpected,
check the indices with `ros2 topic echo /joy`.

## Launch files

| Launch | Purpose | Main arguments |
|---|---|---|
| `trident_bringup sim.launch.py` | sim + RViz + teleop | `world`, `rviz`, `teleop`, `controller`, `joy_dev`, `headless` |
| `trident_gazebo sim.launch.py` | Gazebo, spawn, bridge | `world`, `x`, `y`, `yaw`, `headless` |
| `trident_description display.launch.py` | model check in RViz | |
| `trident_teleop teleop.launch.py` | joystick teleop | `controller`, `joy_dev` |

## Topics

| Topic | Type |
|---|---|
| `/cmd_vel` | geometry_msgs/Twist (in) |
| `/odom`, `/tf` (odom to base_footprint) | from the diff drive plugin |
| `/joint_states` | from Gazebo |
| `/gripper/command` | std_msgs/Float64, drive jaw angle in rad (-1.0 open, 0.09 closed) |
| `/camera/color/image_raw`, `/camera/color/camera_info` | D435 colour |
| `/camera/depth/image_rect_raw` | D435 depth |
| `/camera/depth/color/points` | point cloud |

## Worlds

- `maze` (default): 20 x 20 m walled arena with box obstacles, taken from the TurtleBot 4
  simulator (Apache-2.0). Good for obstacle avoidance tests.
- `empty`: ground plane and one box in front of the robot.

Add a new world by dropping `<name>.sdf` into `src/trident_gazebo/worlds/` and rebuilding.
It needs the Sensors system plugin for the camera to work (see `empty.sdf`).

## GPU

`docker/compose.yaml` uses the NVIDIA GPU by default (needs the nvidia container toolkit and a
working `nvidia-smi` on the host). To run on Intel or AMD integrated graphics instead, follow the
"GPU option 2" comment in that file: comment the `deploy` block and the four NVIDIA environment
lines, uncomment the `devices` block, then run `./docker/run.sh down` and `up` again.

The container is not privileged. It gets the GPU, the X11 socket with a per-session cookie
(`docker/.xauth`, no `xhost +`), and `/dev/input` for controllers.

## License

Apache License 2.0, see [LICENSE](LICENSE). Copyright 2025 podalanga.
The maze world is adapted from the TurtleBot 4 simulator, also Apache 2.0.
