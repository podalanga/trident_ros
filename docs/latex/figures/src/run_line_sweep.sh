#!/usr/bin/env bash
# Entry line followed on its own, for a list of IR noise levels and speeds.
# Usage (in the container): run_line_sweep.sh <noise volts>:<speed m/s> [more pairs]
# Results land in /ws/docs/latex/data/line/n<noise>_v<speed>/.

source /opt/ros/humble/setup.bash
source /ws/install/setup.bash

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA=/ws/docs/latex/data/line
CONFIG=/ws/install/trident_gazebo/share/trident_gazebo/config
MISSION=/ws/install/trident_mission/share/trident_mission/config/mission.yaml

stop_all() {
    pkill -INT -f run_logger.py 2>/dev/null
    pkill -INT -f 'ros2 launch trident_gazebo' 2>/dev/null
    sleep 6
    pkill -KILL -f 'ign gazebo' 2>/dev/null
    pkill -KILL -f '/opt/ros/humble/lib' 2>/dev/null
    pkill -KILL -f '/ws/install' 2>/dev/null
    # Killed processes leave their Fast DDS shared memory behind. Left alone it fills
    # /dev/shm after a few runs and the nodes of the next run can no longer reach each other.
    rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null
    sleep 3
}

for pair in "$@"; do
    noise=${pair%%:*}; speed=${pair##*:}
    out=$DATA/n${noise}_v${speed}
    rm -rf "$out"; mkdir -p "$out"
    stop_all

    ros2 launch trident_gazebo sim.launch.py world:=arena headless:=true obstacles:=none \
        ir_noise:=$noise > "$out/launch.log" 2>&1 &
    ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$CONFIG/bridge_referee.yaml \
        -p use_sim_time:=true > /dev/null 2>&1 &
    ros2 run trident_mission line_follower --ros-args --params-file $MISSION \
        -p use_sim_time:=true > "$out/follower.log" 2>&1 &
    python3 "$HERE/run_logger.py" --ros-args -p use_sim_time:=true -p out:="$out" \
        > "$out/logger.log" 2>&1 &
    sleep 20
    timeout 120 ros2 action send_goal /follow_line trident_interfaces/action/FollowLine \
        "{max_distance: 3.0, speed: $speed}" > "$out/result.txt" 2>&1
    sleep 2
    grep -E 'reached_marker|distance' "$out/result.txt" | tr '\n' ' '; echo "$pair"
    stop_all
done
