#!/usr/bin/env bash
# Helper for the trident simulation. Works from the host and from inside the container.
# Run "./docker/run.sh help" for the list of commands.
set -euo pipefail

DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(dirname "$DOCKER_DIR")"
SERVICE=trident

usage() {
    cat <<USAGE
Usage: ./docker/run.sh <command> [args]

Container (host only):
  image                 Build the Docker image
  up                    Start the container in the background
  down                  Stop and remove the container
  shell                 Open a bash shell in the container

Workspace:
  build                 colcon build of the packages in src/
  clean                 Remove build/, install/ and log/

Robot:
  display               RViz with joint sliders, no simulation
  sim [world] [args]    Gazebo + RViz. World is maze (default) or empty
  teleop <xbox|ps4> [device]
                        Joystick teleop. Device defaults to /dev/input/js0

Extra "name:=value" launch arguments can follow sim and teleop, for example:
  ./docker/run.sh sim empty rviz:=false
USAGE
}

in_container() { [ -n "${TRIDENT_IN_CONTAINER:-}" ]; }

compose() { docker compose --project-directory "$DOCKER_DIR" "$@"; }

group_id() { getent group "$1" | cut -d: -f3; }

# Host settings that compose.yaml reads: user ids and the groups owning the device files
write_env() {
    cat > "$DOCKER_DIR/.env" <<ENV
HOST_UID=$(id -u)
HOST_GID=$(id -g)
VIDEO_GID=$(group_id video)
RENDER_GID=$(group_id render)
DISPLAY=${DISPLAY:-:0}
ENV
}

# Copy the X11 cookie with a wildcard hostname so the container may use the display.
# This avoids opening the X server to everyone with "xhost +".
write_xauth() {
    local file="$DOCKER_DIR/.xauth"
    : > "$file"
    chmod 600 "$file"
    xauth nlist "${DISPLAY:-:0}" | sed -e 's/^..../ffff/' | xauth -f "$file" nmerge - 2>/dev/null \
        || echo "Warning: could not copy the X11 cookie, GUI windows may not open." >&2
}

# Run a command in the container shell with ROS and the workspace sourced
run_in_container() {
    if in_container; then
        bash -ic "$*"
    else
        compose exec "$SERVICE" bash -ic "$*"
    fi
}

host_only() {
    if in_container; then
        echo "'$1' has to be run on the host, not inside the container." >&2
        exit 1
    fi
}

cmd="${1:-help}"
shift || true

case "$cmd" in
    image)
        host_only image
        write_env
        compose build
        ;;
    up)
        host_only up
        write_env
        write_xauth
        if ! compose up -d; then
            echo >&2
            echo "Container failed to start. If the error mentions nvidia, the NVIDIA driver is" >&2
            echo "not available: check nvidia-smi, or switch docker/compose.yaml to the iGPU block." >&2
            exit 1
        fi
        ;;
    down)
        host_only down
        compose down
        ;;
    shell)
        host_only shell
        compose exec "$SERVICE" bash
        ;;
    build)
        # --base-paths keeps colcon away from anything outside src/, such as reference/
        run_in_container "cd /ws && colcon build --symlink-install --base-paths src"
        ;;
    clean)
        rm -rf "$WS_DIR/build" "$WS_DIR/install" "$WS_DIR/log"
        ;;
    display)
        run_in_container "ros2 launch trident_description display.launch.py"
        ;;
    sim)
        world=maze
        # First argument is the world name unless it is already a launch argument
        if [ $# -gt 0 ] && [[ "$1" != *:=* ]]; then
            world="$1"
            shift
        fi
        run_in_container "ros2 launch trident_bringup sim.launch.py world:=$world $*"
        ;;
    teleop)
        controller="${1:-}"
        if [ "$controller" != xbox ] && [ "$controller" != ps4 ]; then
            echo "Pick a controller: ./docker/run.sh teleop <xbox|ps4> [device]" >&2
            exit 1
        fi
        shift
        joy_dev=/dev/input/js0
        if [ $# -gt 0 ] && [[ "$1" != *:=* ]]; then
            joy_dev="$1"
            shift
        fi
        run_in_container \
            "ros2 launch trident_teleop teleop.launch.py controller:=$controller joy_dev:=$joy_dev $*"
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        echo "Unknown command: $cmd" >&2
        usage >&2
        exit 1
        ;;
esac
