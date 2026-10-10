"""Mission state machine: entry line, drop zone survey, then three pick and place runs.

Publishes:  /mission/state   std_msgs/String   current state, latched

  FOLLOW_ENTRY_LINE   line follower up to the start square
  SURVEY_DROP_ZONES   visit each drop zone and read which colour it takes
  PICK                fetch the coin of the next bay and read its colour
  DROP                take it to the zone of that colour
  DONE / FAILED

The steps themselves live in docking.py. This file only decides what happens next.
"""
import threading

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile
from std_msgs.msg import String

from trident_mission.base_motion import BaseMotion
from trident_mission.docking import DockSettings, Docking
from trident_mission.gripper import Gripper
from trident_mission.line_client import LineClient
from trident_mission.navigator import Navigator
from trident_mission.qr_reader import QrReader
from trident_mission.stations import ZoneBook, load_arena


class Mission(Node):
    def __init__(self):
        super().__init__('mission')
        self.arena = load_arena(self.declare_parameter('stations_file', '').value)
        self.entry_speed = self.declare_parameter('entry_speed', 0.10).value
        self.entry_reach = self.declare_parameter('entry_reach', 3.0).value
        settings = DockSettings(
            speed=self.declare_parameter('dock_speed', 0.05).value,
            reach=self.declare_parameter('dock_reach', 0.60).value,
            attempts=self.declare_parameter('dock_attempts', 2).value,
            qr_timeout=self.declare_parameter('qr_timeout', 4.0).value)
        gripper = Gripper(self,
                          open_angle=self.declare_parameter('gripper_open', -1.0).value,
                          closed_angle=self.declare_parameter('gripper_closed', 0.09).value,
                          travel_time=self.declare_parameter('gripper_travel_time', 1.0).value)

        self.navigator = Navigator()
        self.line = LineClient(self)
        self.docking = Docking(self.navigator, self.line, BaseMotion(self), gripper,
                               QrReader(self), settings, self.get_logger().warn)
        self.zones = ZoneBook()

        latched = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.state_pub = self.create_publisher(String, '/mission/state', latched)

    def enter(self, state: str, detail: str = ''):
        self.state_pub.publish(String(data=state))
        self.get_logger().info(f'{state} {detail}'.rstrip())

    def run(self) -> bool:
        self.line.wait_until_ready()

        self.enter('FOLLOW_ENTRY_LINE')
        reached, _ = self.line.follow(self.entry_reach, self.entry_speed)
        if not reached:
            self.enter('FAILED', 'start square not found')
            return False

        self.navigator.wait_until_ready()
        self.navigator.wait_until_localized()

        self.enter('SURVEY_DROP_ZONES')
        for zone in self.arena.drops:
            colour = self.docking.read_colour(zone)
            if colour is None:
                self.get_logger().warn(f'{zone.name}: QR not read')
                continue
            self.zones.record(zone, colour)
            self.get_logger().info(f'{zone.name} takes {colour}')

        delivered = []
        for bay in self.arena.bays:
            self.enter('PICK', bay.name)
            colour = self.docking.pick(bay)
            if colour is None:
                self.get_logger().warn(f'{bay.name}: nothing picked')
                continue
            zone = self.zones.zone_for(colour)
            if zone is None:
                # Holding a coin with no known home: set it down here and move on
                self.get_logger().warn(f'{bay.name}: no drop zone known for {colour}')
                self.docking.release(back_off=0.15)
                continue
            self.enter('DROP', f'{colour} coin to {zone.name}')
            if self.docking.drop(zone):
                delivered.append(colour)

        complete = len(delivered) == len(self.arena.bays)
        self.enter('DONE' if complete else 'FAILED',
                   f'delivered {len(delivered)} of {len(self.arena.bays)}: {", ".join(delivered)}')
        return complete


def main():
    rclpy.init()
    mission = Mission()
    # Callbacks run on a background thread so run() can be written as plain blocking steps
    executor = MultiThreadedExecutor()
    executor.add_node(mission)
    threading.Thread(target=executor.spin, daemon=True).start()
    try:
        mission.run()
    except KeyboardInterrupt:
        pass
    mission.navigator.shutdown()
    mission.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
