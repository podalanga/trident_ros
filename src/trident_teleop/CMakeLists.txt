cmake_minimum_required(VERSION 3.8)
project(trident_teleop)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME})

install(PROGRAMS scripts/gripper_teleop.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
