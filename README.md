# trident_ros

ROS 2 Humble + Gazebo Fortress simulation of the trident differential drive robot
(gripper, Intel D435 depth camera, IR line array, IMU), with joystick teleop for Xbox and PS4
controllers and an autonomous pick and place mission built on RTAB-Map and Nav2.
Everything runs in an unprivileged Docker container.

## Layout

```
docker/                  Dockerfile, compose.yaml and run.sh
src/
  trident_description/   URDF (xacro), meshes, RViz configs
  trident_gazebo/        worlds, textures, ROS to Gazebo bridge, simulation launch, referee
  trident_teleop/        controller configs and teleop launch
  trident_interfaces/    FollowLine action
  trident_navigation/    EKF odometry, RTAB-Map and Nav2 configuration and launch
  trident_mission/       line follower, pick and drop sequences, mission state machine
  trident_bringup/       top level launch files
docs/autonomy-design.md  how the mission is put together and why
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
./docker/run.sh teleop xbox                    # or ps4, or generic
./docker/run.sh teleop ps4 /dev/input/js1      # if the pad is not js0
```

Other commands: `display` (RViz with joint sliders), `sim line`, `sim empty`, `sim arena`,
`shell`, `clean`, `down`.
`./docker/run.sh help` lists them all. Inside the container shell the same script is at
`/ws/docker/run.sh`, and plain `ros2 launch` works as well.

## Autonomous mission

The arena world holds a curved line into a room with three pick bays and three drop zones.
The robot follows the line to the start square, reads the QR code at each drop zone, then
carries every coin from its bay to the zone whose QR names the same colour, driving around
obstacle boxes that are not in its map.

```bash
./docker/run.sh map        # once: the robot surveys the empty arena, about 4 minutes
./docker/run.sh mission    # the full run, about 7 minutes
```

The image needs the navigation packages. If yours was built before they were added to the
Dockerfile, run `./docker/run.sh image`, then `down` and `up`, and `build` once more.

`map` writes `maps/arena.db` and exits by itself when the survey route is done. Run it again
whenever the arena dimensions change. `mission` prints its state and the referee's score:

```
[mission]: PICK bay 3
[mission]: DROP blue coin to drop 1
[referee]: 3 of 3 coins home: blue, green, red
[referee]: Mission DONE. Referee verdict: PASS (3 of 3 coins home: blue, green, red)
```

Shuffle a run with launch arguments. `pick_order` and `drop_order` are permutations of `RGB`
for bays and drop zones 1 to 3, `obstacles` is a preset (`a`, `b`, `c` or `none`):

```bash
./docker/run.sh mission pick_order:=GBR drop_order:=RGB obstacles:=b
./docker/run.sh mission headless:=true rviz:=false
```

How it works, in short:

- **Odometry:** wheel encoders and the IMU fused by `robot_localization`.
- **Localisation:** RTAB-Map visual SLAM on the D435, localising in the saved map.
- **Driving between stations:** Nav2 (NavFn planner, Regulated Pure Pursuit), obstacles from
  the depth image, replanning once a second.
- **Last 15 cm:** the camera cannot see the floor that close, so the IR array follows the
  stem of each T mark up to its crossbar.
- **QR codes:** `zbar_ros`, read only from the station in front of the code.
- **Gripper:** no lift, so a coin is caged by the closed jaws and slid to its square.

`./docker/run.sh test` runs the unit tests of the mission logic. The design, the limits of the
robot it works around and the package layout are written up in
[docs/autonomy-design.md](docs/autonomy-design.md).

## Controls

| Action | Xbox | PS4 | Generic |
|---|---|---|---|
| Enable driving (hold) | LB | L1 | LB / L1 |
| Turbo (hold) | RB | R1 | RB / R1 |
| Forward / back | left stick | left stick | left stick |
| Turn | right stick | right stick | right stick |
| Close gripper | A | Cross | A |
| Open gripper | B | Circle | B |

Normal speed is 0.2 m/s and 1.5 rad/s, turbo is 0.5 m/s and 3.0 rad/s.

Which mapping to pick depends on how Linux sees the pad, not on the brand printed on it:

- `xbox`: Xbox pads on USB or the Xbox wireless dongle (xpad driver, 11 buttons).
- `ps4`: DualShock 4 on USB or Bluetooth.
- `generic`: SHANWAN, 8BitDo and other Android mode pads, and Xbox pads over Bluetooth
  (generic HID layout, 14 or 15 buttons).

If the gripper buttons work but the robot does not drive, the mapping is the wrong one: the
enable button sits on a different index. Check with `ros2 topic echo /joy` while pressing LB.
Mappings live in `src/trident_teleop/config/`.

## Launch files

| Launch | Purpose | Main arguments |
|---|---|---|
| `trident_bringup sim.launch.py` | sim + RViz + teleop | `world`, `rviz`, `teleop`, `controller`, `joy_dev`, `headless`, `follow`, `follow_distance`, `follow_height` |
| `trident_bringup mapping.launch.py` | survey the arena and save the map | `database`, `headless`, `rviz` |
| `trident_bringup mission.launch.py` | the full mission with referee | `database`, `pick_order`, `drop_order`, `obstacles`, `headless`, `rviz` |
| `trident_bringup autonomy.launch.py` | arena + EKF + RTAB-Map + Nav2, goals from RViz | `mode`, `database`, `obstacles`, `headless`, `rviz` |
| `trident_gazebo sim.launch.py` | Gazebo, spawn, bridge | `world`, `x`, `y`, `yaw`, `headless`, `follow`, `follow_distance`, `follow_height`, `ekf`, `ir_noise`, `pick_order`, `drop_order`, `obstacles` |
| `trident_navigation odometry.launch.py` | EKF of wheel odometry and IMU | |
| `trident_navigation slam.launch.py` | RTAB-Map | `mode`, `database` |
| `trident_navigation navigation.launch.py` | Nav2 | |
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
| `/camera/depth/color/points` | point cloud, built from the depth image in the optical frame |
| `/ir/analog` | std_msgs/Float32MultiArray, 8 IR line sensor voltages (0 V dark to 5 V white) |
| `/imu` | sensor_msgs/Imu, arena world only |
| `/wheel/odom` | raw wheel odometry when the EKF is in use (`ekf:=true`), which then publishes `/odom` |
| `/map`, `/tf` (map to odom) | from RTAB-Map |
| `/barcode` | std_msgs/String, text of the QR code in view |
| `follow_line` | trident_interfaces/FollowLine action |
| `/mission/state`, `/referee/score` | std_msgs/String |

## Worlds

- `maze` (default): 20 x 20 m walled arena with box obstacles, taken from the TurtleBot 4
  simulator (Apache-2.0). Good for obstacle avoidance tests.
- `line`: light floor with a black 20 mm line loop, for the IR line sensor array.
- `empty`: ground plane and one box in front of the robot.
- `arena`: 3.6 x 2.4 m mission field with textured walls: entry line, start square, three
  T-marked pick bays with coins, three drop squares and a QR code at every station. It is a
  xacro file, so its dimensions sit in one place at the top.

Add a new world by dropping `<name>.sdf` (or `<name>.sdf.xacro`) into
`src/trident_gazebo/worlds/` and rebuilding.
It needs the Sensors system plugin for the cameras and the IR array to work (see `empty.sdf`).

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
