from pathlib import Path

import pytest

from trident_mission.stations import Station, ZoneBook, load_arena

STATIONS = Path(__file__).resolve().parent.parent / 'config' / 'stations.yaml'


def test_arena_file_has_three_bays_and_three_drops():
    arena = load_arena(str(STATIONS))
    assert len(arena.bays) == 3
    assert len(arena.drops) == 3
    assert arena.bays[0] == Station(name='bay 1', x=1.5, y=1.0, yaw=1.5708)


def test_zone_book_matches_colours_to_zones():
    book = ZoneBook()
    first, second = Station('drop 1', 0, 0, 0), Station('drop 2', 0, 1, 0)
    book.record(first, 'blue')
    book.record(second, 'red')
    assert book.zone_for('red') is second
    assert book.zone_for('blue') is first
    assert book.zone_for('green') is None
    assert book.missing() == ['green']


def test_zone_book_rejects_unknown_colours():
    with pytest.raises(ValueError):
        ZoneBook().record(Station('drop 1', 0, 0, 0), 'purple')
