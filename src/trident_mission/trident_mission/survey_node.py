"""Drives a fixed route through the arena so RTAB-Map can build its map.

Reads the stops from a YAML file (parameter route_file), sends each one to Nav2 and spins
once on arrival. Exits when the route is done, which lets the mapping launch shut down and
RTAB-Map save its database.
"""
import math

import rclpy
import yaml
from rclpy.node import Node

from trident_mission.navigator import Navigator


def main():
    rclpy.init()
    node = Node('survey')
    route_file = node.declare_parameter('route_file', '').value
    with open(route_file) as stream:
        stops = yaml.safe_load(stream)['stops']

    navigator = Navigator()
    navigator.wait_until_ready()
    for number, (x, y, yaw) in enumerate(stops, start=1):
        node.get_logger().info(f'Stop {number} of {len(stops)}: ({x:.2f}, {y:.2f})')
        if not navigator.go_to(x, y, yaw):
            node.get_logger().warn('Could not reach this stop, moving on')
        navigator.spin(2.0 * math.pi)

    node.get_logger().info('Survey finished')
    navigator.shutdown()
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
