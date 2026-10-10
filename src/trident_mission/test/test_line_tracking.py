import pytest

from trident_mission.line_tracking import (ArrayGeometry, MarkerDetector, Steering, dark_count,
                                           line_offset)

GEOMETRY = ArrayGeometry()
WHITE = [5.0] * 8


def with_dark(channels, volts=0.0):
    reading = list(WHITE)
    for channel in channels:
        reading[channel] = volts
    return reading


def test_no_line_gives_no_offset():
    assert line_offset(WHITE, GEOMETRY) is None


def test_line_between_the_middle_channels_is_centred():
    assert line_offset(with_dark([3, 4], volts=3.5), GEOMETRY) == pytest.approx(0.0)


def test_line_under_the_leftmost_channel_is_positive():
    assert line_offset(with_dark([7]), GEOMETRY) == pytest.approx(3.5 * 0.015)


def test_line_under_the_rightmost_channel_is_negative():
    assert line_offset(with_dark([0]), GEOMETRY) == pytest.approx(-3.5 * 0.015)


def test_noise_below_the_floor_level_is_ignored():
    noisy = [4.8, 5.0, 4.9, 5.0, 0.0, 5.0, 4.7, 5.0]
    assert line_offset(noisy, GEOMETRY) == pytest.approx(0.5 * 0.015)


def test_dark_count():
    assert dark_count(WHITE, GEOMETRY) == 0
    assert dark_count(with_dark(range(8)), GEOMETRY) == 8
    assert dark_count(with_dark([3, 4], volts=3.5), GEOMETRY) == 0


def test_marker_needs_a_streak():
    detector = MarkerDetector(min_channels=6, min_samples=2)
    assert not detector.update(8)
    assert detector.update(8)


def test_marker_streak_is_broken_by_a_line_sample():
    detector = MarkerDetector(min_channels=6, min_samples=2)
    detector.update(8)
    assert not detector.update(2)
    assert not detector.update(8)


def test_steering_turns_toward_the_line_and_saturates():
    steering = Steering(kp=40.0, kd=0.0, max_turn=1.5)
    assert steering.turn_rate(0.01, 0.05) == pytest.approx(0.4)
    assert steering.turn_rate(-0.01, 0.05) == pytest.approx(-0.4)
    assert steering.turn_rate(0.5, 0.05) == pytest.approx(1.5)


def test_steering_derivative_damps_a_closing_error():
    steering = Steering(kp=40.0, kd=2.0, max_turn=5.0)
    steering.turn_rate(0.02, 0.05)
    # Offset shrinking by 5 mm in 50 ms: the derivative term pulls the command down
    assert steering.turn_rate(0.015, 0.05) == pytest.approx(40.0 * 0.015 - 2.0 * 0.1)
