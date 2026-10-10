"""Line maths for the IR array. No ROS in here, so it can be unit tested on its own.

Channel 0 is the rightmost sensor and the last channel the leftmost, matching the URDF.
Offsets are in metres, positive when the line is to the left of the array centre.
"""
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class ArrayGeometry:
    pitch: float = 0.015      # m between neighbouring channels
    v_ref: float = 5.0        # V read on a white floor


def darkness(volts: Sequence[float], v_ref: float) -> list:
    """Turn voltages into 0 (white) to 1 (black)."""
    return [min(max(1.0 - v / v_ref, 0.0), 1.0) for v in volts]


def line_offset(volts: Sequence[float], geometry: ArrayGeometry,
                min_darkness: float = 0.15) -> Optional[float]:
    """Darkness weighted centre of the line, or None when no channel sees it.

    Readings below min_darkness are treated as floor, which keeps sensor noise from
    dragging the centre around.
    """
    weights = [d if d >= min_darkness else 0.0 for d in darkness(volts, geometry.v_ref)]
    total = sum(weights)
    if total == 0.0:
        return None
    middle = (len(weights) - 1) / 2.0
    return sum(w * (i - middle) for i, w in enumerate(weights)) * geometry.pitch / total


def dark_count(volts: Sequence[float], geometry: ArrayGeometry, dark_level: float = 0.5) -> int:
    """How many channels sit over black."""
    return sum(1 for d in darkness(volts, geometry.v_ref) if d >= dark_level)


class MarkerDetector:
    """Reports a marker once enough channels have been dark for a few samples in a row.

    A single line never darkens more than two channels, so a square or a crossbar is the
    only thing that trips this. The streak requirement rejects one-off noisy samples.
    """

    def __init__(self, min_channels: int = 6, min_samples: int = 2):
        self.min_channels = min_channels
        self.min_samples = min_samples
        self.streak = 0

    def update(self, dark_channels: int) -> bool:
        self.streak = self.streak + 1 if dark_channels >= self.min_channels else 0
        return self.streak >= self.min_samples

    def reset(self):
        self.streak = 0


class Steering:
    """PD controller from line offset to turn rate."""

    def __init__(self, kp: float, kd: float, max_turn: float):
        self.kp = kp
        self.kd = kd
        self.max_turn = max_turn
        self.last_offset: Optional[float] = None

    def turn_rate(self, offset: float, dt: float) -> float:
        slope = 0.0
        if self.last_offset is not None and dt > 0.0:
            slope = (offset - self.last_offset) / dt
        self.last_offset = offset
        turn = self.kp * offset + self.kd * slope
        return min(max(turn, -self.max_turn), self.max_turn)

    def reset(self):
        self.last_offset = None
