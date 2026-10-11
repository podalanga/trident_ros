#!/usr/bin/env bash
# Runs a batch of headless missions inside the container and records each one.
# Usage (in the container): run_missions.sh <name> <pick> <drop> <obstacles> [more sets of four]
# Results land in /ws/docs/latex/data/runs/<name>/.

source /opt/ros/humble/setup.bash
source /ws/install/setup.bash

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA=/ws/docs/latex/data/runs
LIMIT=${LIMIT:-1200}     # wall clock seconds allowed per run

stop_all() {
    pkill -INT -f 'ros2 launch trident_bringup' 2>/dev/null
    sleep 8
    pkill -KILL -f 'ros2 launch trident_bringup' 2>/dev/null
    pkill -KILL -f 'ign gazebo' 2>/dev/null
    pkill -KILL -f '/opt/ros/humble/lib' 2>/dev/null
    pkill -KILL -f '/ws/install' 2>/dev/null
    # Killed processes leave their Fast DDS shared memory behind. Left alone it fills
    # /dev/shm after a few runs and the nodes of the next run can no longer reach each other.
    rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_* 2>/dev/null
    sleep 3
}

while [ $# -ge 4 ]; do
    name=$1; pick=$2; drop=$3; obstacles=$4
    shift 4
    out=$DATA/$name
    rm -rf "$out"
    mkdir -p "$out"
    echo "pick_order=$pick drop_order=$drop obstacles=$obstacles" > "$out/config.txt"
    stop_all

    ros2 launch trident_bringup mission.launch.py database:=/ws/maps/arena.db \
        headless:=true rviz:=false pick_order:=$pick drop_order:=$drop obstacles:=$obstacles \
        > "$out/launch.log" 2>&1 &
    timeout "$LIMIT" python3 "$HERE/run_logger.py" --ros-args -p use_sim_time:=true -p out:="$out" \
        > "$out/logger.log" 2>&1
    echo "logger exit $?" >> "$out/config.txt"
    grep -E 'Referee verdict|\[mission\]: (DONE|FAILED)' "$out/launch.log" | tail -2
    stop_all
done
