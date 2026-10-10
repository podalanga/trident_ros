"""Pick and drop sequences at a station.

Nav2 brings the robot to the pose in front of a stem. From there the camera can no longer
see the floor ahead, so the line follower drives the stem up to its marker and everything
after that is timed jaw moves and odometry.
"""
from dataclasses import dataclass
from typing import Callable, Optional

from trident_mission.base_motion import BaseMotion
from trident_mission.gripper import Gripper
from trident_mission.line_client import LineClient
from trident_mission.navigator import Navigator
from trident_mission.qr_reader import QrReader
from trident_mission.stations import Station


@dataclass(frozen=True)
class DockSettings:
    speed: float          # m/s on the stem
    reach: float          # m, farthest the line follower may go looking for the marker
    attempts: int         # tries per station before giving up
    qr_timeout: float     # s to wait for a steady QR decode


class Docking:
    def __init__(self, navigator: Navigator, line: LineClient, base: BaseMotion,
                 gripper: Gripper, qr: QrReader, settings: DockSettings,
                 log: Callable[[str], None]):
        self.navigator = navigator
        self.line = line
        self.base = base
        self.gripper = gripper
        self.qr = qr
        self.settings = settings
        self.log = log

    def approach(self, station: Station) -> Optional[float]:
        """Drive to the station's marker. Returns the distance covered on the stem, which is
        what retreat() needs to get back out, or None when the marker was never reached."""
        for attempt in range(1, self.settings.attempts + 1):
            if not self.navigator.go_to(station.x, station.y, station.yaw):
                self.log(f'{station.name}: navigation failed (attempt {attempt})')
                continue
            reached, distance = self.line.follow(self.settings.reach, self.settings.speed)
            if reached:
                return distance
            self.log(f'{station.name}: no marker found (attempt {attempt})')
            self.retreat(distance)
        return None

    def retreat(self, distance: float):
        """Back straight out along the stem just driven."""
        self.base.drive(-distance, self.settings.speed)

    def read_colour(self, station: Station) -> Optional[str]:
        """Go up to a station, read its QR and come back out."""
        distance = self.approach(station)
        if distance is None:
            return None
        colour = self.qr.read(self.settings.qr_timeout)
        self.retreat(distance)
        return colour

    def pick(self, bay: Station) -> Optional[str]:
        """Collect the coin of a bay. Returns its colour, or None if nothing was picked.
        A coin whose QR cannot be read is left where it is: without a colour there is
        nowhere to take it."""
        self.gripper.open()
        distance = self.approach(bay)
        if distance is None:
            self.gripper.close()
            return None
        colour = self.qr.read(self.settings.qr_timeout)
        if colour is None:
            # Back out with the jaws still open so the coin stays in its bay
            self.retreat(distance)
            self.gripper.close()
            return None
        self.gripper.close()
        self.retreat(distance)
        return colour

    def drop(self, zone: Station) -> bool:
        """Carry the held coin into a drop square and leave it there."""
        distance = self.approach(zone)
        if distance is None:
            return False
        self.release(back_off=distance)
        return True

    def release(self, back_off: float):
        """Let go of the coin where the robot stands and back away from it."""
        self.gripper.open()
        self.retreat(back_off)
        self.gripper.close()
