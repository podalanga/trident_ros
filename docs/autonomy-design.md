# Autonomy design

How the trident robot runs its mission in the arena world, and why it is built this way.
Simulation only.

## The mission

1. Follow a curved black line from the spawn point to a black start square.
2. Inside the room, visit the three drop zones on the front wall and read the QR code at each
   one. The code names the colour that zone accepts.
3. For each of the three pick bays on the left wall: drive up the T mark, read the bay's QR,
   cage the coin, carry it to the drop zone of the same colour and release it there.
4. Obstacle boxes that are not in the map stand in the room the whole time and are driven around.

## What is off the shelf and what is ours

| Concern | Solution | Source |
|---|---|---|
| Odometry | wheel odometry + IMU in an EKF | `robot_localization` |
| Visual SLAM | RGB-D mapping run, then localisation mode | `rtabmap_ros` |
| Planning, control, costmaps, recovery | NavFn + Regulated Pure Pursuit | `navigation2` |
| Sending goals from Python | `BasicNavigator` | `nav2_simple_commander` |
| QR decoding | `barcode_reader` | `zbar_ros` |
| Line following, marker detection | PD steering on the IR centroid | `trident_mission` |
| Pick and drop sequences | IR + odometry | `trident_mission` |
| Mission sequencing | state machine | `trident_mission` |
| Scoring | referee on Gazebo ground truth | `trident_gazebo` |

## Limits of the robot that shape the design

- **No lift.** The jaws turn about a vertical axis only. A drop is a release on a flat black
  square, and a pick is a cage: the closed jaws surround the coin and slide it along the floor.
- **Blind zone in front.** The D435 sits 85 mm above the floor. Its depth image starts at 0.2 m
  and the floor only comes into view 0.15 m ahead of the lens, while a caged coin sits about
  5 cm ahead of it. The last stretch of every approach is therefore driven on the IR array and
  odometry, never on the camera.
- **The camera only looks forward.** The robot never reverses under Nav2. It only backs straight
  out along a stem it has just driven.
- **Low things do not reach the costmap.** Points under 3 cm are treated as floor. That keeps
  the coins and sensor noise from blocking paths, and it means obstacles have to be taller
  than that to be avoided.
- **QR codes are read up close.** `zbar_ros` reports the text of a code but not where it is in
  the image, so a code is only trusted when the robot stands at its station and no neighbour
  is in view.

## Arena

3.6 x 2.4 m, walls 0.3 m high with busy textures so visual SLAM has features to track.
The robot spawns at the origin facing +X. Marking sizes come from the 15 mm IR channel pitch:

- lines are 12 mm wide, less than one pitch
- the start square and the T crossbars are 120 mm wide, more than the whole 105 mm array, so
  every channel goes dark at once and nothing else on the floor can do that
- drop squares are 250 mm, big enough that a coin released when the array reaches the edge
  lies near the centre

Dimensions live in `trident_gazebo/worlds/arena.sdf.xacro`. Two files repeat a few of them:
`trident_mission/config/stations.yaml` (where Nav2 hands over to the line follower) and
`trident_gazebo/config/referee.yaml` (the drop squares).

## Packages

```
trident_description   URDF, meshes, RViz layouts
trident_gazebo        everything that exists only in simulation: worlds, textures,
                      bridge configs, IR array emulation, referee
trident_interfaces    FollowLine action
trident_navigation    configuration and launch for the EKF, RTAB-Map and Nav2 (no code)
trident_mission       line follower, docking sequences, mission state machine
trident_bringup       top level launch files
trident_teleop        joystick teleop
```

`trident_navigation` and `trident_mission` do not know they are in a simulator.

Inside `trident_mission` each file has one job:

| File | Job |
|---|---|
| `line_tracking.py` | line centre, marker detection and steering maths, no ROS |
| `line_follower_node.py` | the `follow_line` action server |
| `line_client.py` | blocking client for that action |
| `navigator.py` | Nav2 goals as (x, y, yaw) |
| `gripper.py` | open and close the jaws |
| `base_motion.py` | straight moves by odometry |
| `qr_reader.py` | steady colour reading from `/barcode` |
| `stations.py` | station poses and the colour to drop zone book, no ROS |
| `docking.py` | approach, pick, drop and read sequences built from the above |
| `mission_node.py` | the state machine |
| `survey_node.py` | drives the mapping route |

## Data flow

```
Gazebo  /wheel/odom, /imu ........ EKF ........ /odom, TF odom -> base_footprint
        colour + depth ........... RTAB-Map ... /map, TF map -> odom
        depth .................... nav_cloud .. /camera/depth/points_nav -> Nav2 costmaps
        /ir/analog ............... line_follower (follow_line action)
        colour ................... zbar_ros ... /barcode

mission  ->  follow_line goals, Nav2 goals, /gripper/command, short /cmd_vel moves
referee  <-  /sim/poses (ground truth), /mission/state
```

Only one thing drives `/cmd_vel` at a time: the mission waits for each step to finish before
starting the next.

## Docking

Nav2 stops within about 2 cm and 3 degrees of a station pose, which is 0.15 m short of the
stem. The line follower then drives straight until the array finds the stem, steers onto it
and stops when all channels go dark.

- **Pick:** jaws open, follow the stem to the crossbar (the coin is now between the jaws),
  read the QR on the wall, close the jaws, back out the distance just driven.
- **Drop:** follow the stem until the array enters the square (the coin is 0.13 m further in),
  open the jaws, back out, close the jaws.

If the marker is not found, the robot backs out and tries the station once more. A bay whose
QR cannot be read is skipped and its coin is left in place.

## Map

The map is built once by `mapping.launch.py`: the survey node sends a fixed list of stops to
Nav2 and spins at each one while RTAB-Map records. The arena is mapped without obstacles, so in
a mission run the boxes are unknown and only exist in the costmaps. Mapping starts at the spawn
pose, which makes the map frame line up with the world frame and lets the station poses be
written in arena coordinates.
