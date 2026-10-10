# ROS 2 Humble desktop (RViz included) with Gazebo Fortress, the teleop drivers and the
# autonomy stack: EKF odometry, RTAB-Map, Nav2 and a QR reader
FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-ros-gz \
        ros-humble-xacro \
        ros-humble-joint-state-publisher-gui \
        ros-humble-joy-linux \
        ros-humble-teleop-twist-joy \
        ros-humble-depth-image-proc \
        ros-humble-robot-localization \
        ros-humble-rtabmap-ros \
        ros-humble-navigation2 \
        ros-humble-nav2-bringup \
        ros-humble-nav2-simple-commander \
        ros-humble-zbar-ros \
        python3-qrcode \
        python3-pytest \
        python3-colcon-common-extensions \
        liburdfdom-tools \
        mesa-utils \
    && rm -rf /var/lib/apt/lists/*

# Same UID/GID as the host user, so files built in the mounted workspace stay yours
ARG USERNAME=ros
ARG UID=1000
ARG GID=1000
RUN groupadd --gid ${GID} ${USERNAME} \
    && useradd --uid ${UID} --gid ${GID} --create-home --shell /bin/bash ${USERNAME}

# run.sh uses this to tell the container apart from the host
ENV TRIDENT_IN_CONTAINER=1

USER ${USERNAME}
WORKDIR /ws

# Every shell gets ROS, plus the workspace overlay once it has been built.
# .hushlogin silences the bash sudo hint, which complains about unnamed host groups.
RUN touch ~/.hushlogin \
    && echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc \
    && echo '[ -f /ws/install/setup.bash ] && source /ws/install/setup.bash' >> ~/.bashrc

CMD ["sleep", "infinity"]
