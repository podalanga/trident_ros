"""Stations of the arena and the record of which drop zone takes which colour. No ROS here."""
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

COLOURS = ('red', 'green', 'blue')


@dataclass(frozen=True)
class Station:
    """A pick bay or a drop zone, given by the pose in front of its stem."""
    name: str
    x: float
    y: float
    yaw: float


@dataclass(frozen=True)
class Arena:
    bays: List[Station]
    drops: List[Station]


def load_arena(path: str) -> Arena:
    with open(path) as stream:
        data = yaml.safe_load(stream)
    return Arena(bays=[Station(**entry) for entry in data['bays']],
                 drops=[Station(**entry) for entry in data['drops']])


class ZoneBook:
    """Remembers the colour read at each drop zone and looks zones up by colour."""

    def __init__(self):
        self._zone_by_colour: Dict[str, Station] = {}

    def record(self, zone: Station, colour: str):
        if colour not in COLOURS:
            raise ValueError(f'unknown colour {colour!r}')
        self._zone_by_colour[colour] = zone

    def zone_for(self, colour: str) -> Optional[Station]:
        return self._zone_by_colour.get(colour)

    def missing(self) -> List[str]:
        return [colour for colour in COLOURS if colour not in self._zone_by_colour]
