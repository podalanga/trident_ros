#!/usr/bin/env bash
# Runs one mission with the Gazebo and RViz windows open and saves screenshots of both.
# Run on the host with the container up:  capture_gui.sh <output folder>
# The Gazebo camera shows the whole arena first and moves to pick bay 1 for the first pick.
OUT=${1:-/tmp/trident_shots}
mkdir -p "$OUT"

in_container() { docker exec trident_ros bash -c "source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; $*"; }

camera() {   # x y z roll pitch yaw
    local q
    q=$(python3 -c "
import math,sys
r,p,y=map(float,sys.argv[1:])
cr,sr,cp,sp,cy,sy=math.cos(r/2),math.sin(r/2),math.cos(p/2),math.sin(p/2),math.cos(y/2),math.sin(y/2)
print(f'x: {sr*cp*cy-cr*sp*sy}, y: {cr*sp*cy+sr*cp*sy}, z: {cr*cp*sy-sr*sp*cy}, w: {cr*cp*cy+sr*sp*sy}')" "$4" "$5" "$6")
    in_container "ign service -s /gui/move_to/pose --reqtype ignition.msgs.GUICamera \
        --reptype ignition.msgs.Boolean --timeout 2000 \
        --req 'pose: {position: {x: $1, y: $2, z: $3}, orientation: {$q}}'" > /dev/null 2>&1
}

shot() {     # name
    local gz rviz
    gz=$(xdotool search --name 'Gazebo' | tail -1)
    rviz=$(xdotool search --name 'RViz' | tail -1)
    [ -n "$gz" ] && import -window "$gz" "$OUT/gazebo_$1.png" 2>/dev/null
    [ -n "$rviz" ] && import -window "$rviz" "$OUT/rviz_$1.png" 2>/dev/null
}

docker exec -d trident_ros bash -c "source /opt/ros/humble/setup.bash; source /ws/install/setup.bash; \
    ros2 launch trident_bringup mission.launch.py database:=/ws/maps/arena.db > /tmp/gui_mission.log 2>&1"
sleep 22
camera -0.9 -1.5 2.3 0 0.62 0.70
for i in $(seq 1 10); do sleep 8; shot "a$(printf %02d $i)"; done          # line, survey
camera 1.15 0.95 0.45 0 0.55 0.95
for i in $(seq 1 6); do sleep 6; shot "b$(printf %02d $i)"; done           # first pick, close
camera -0.9 -1.5 2.3 0 0.62 0.70
for i in $(seq 1 16); do sleep 10; shot "c$(printf %02d $i)"; done         # deliveries

docker exec trident_ros bash -c "pkill -INT -f 'ros2 launch'; sleep 8; pkill -KILL -f 'ign gazebo'; \
    pkill -KILL -f /opt/ros/humble/lib; pkill -KILL -f /ws/install; rm -f /dev/shm/fastrtps_* /dev/shm/sem.fastrtps_*"
