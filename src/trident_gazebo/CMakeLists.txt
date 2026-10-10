cmake_minimum_required(VERSION 3.8)
project(trident_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch worlds
  DESTINATION share/${PROJECT_NAME})

install(PROGRAMS scripts/gripper_mimic.py scripts/ir_array.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
