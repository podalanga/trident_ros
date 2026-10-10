"""Colour named by the QR code in front of the camera, from zbar_ros on /barcode."""
import time
from typing import Optional

from rclpy.node import Node
from std_msgs.msg import String

from trident_mission.stations import COLOURS


class QrReader:
    def __init__(self, node: Node, agree: int = 3):
        # Number of identical decodes in a row needed before a reading is trusted
        self.agree = agree
        self.recent = []
        node.create_subscription(String, '/barcode', self._on_barcode, 10)

    def _on_barcode(self, msg: String):
        self.recent.append(msg.data.strip().lower())

    def read(self, timeout: float) -> Optional[str]:
        """Wait for a steady decode. Only codes seen after this call count, so a code
        passed on the way here is never reported by mistake."""
        self.recent = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            latest = self.recent[-self.agree:]
            if len(latest) == self.agree and len(set(latest)) == 1 and latest[0] in COLOURS:
                return latest[0]
            time.sleep(0.05)
        return None
