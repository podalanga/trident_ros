#!/usr/bin/env python3
"""Analog IR line sensor array built from the per-channel floor cameras.

Subscribes:  /ir/raw/ch<N>  sensor_msgs/Image       tiny image of the floor under channel N
Publishes:   /ir/analog     std_msgs/Float32MultiArray  one voltage per channel

Each reading is continuous: 0 V on a black surface up to v_ref (5 V) on a white one, with values in
between when a channel sits over the edge of a line. Set invert to true for sensors whose
output goes high on dark surfaces, and noise_stddev (volts) to add Gaussian noise per reading.
"""
import random
from functools import partial

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray


class IrArray(Node):
    def __init__(self):
        super().__init__('ir_array')
        self.channels = self.declare_parameter('channels', 8).value
        self.v_ref = self.declare_parameter('v_ref', 5.0).value
        # Image brightness (0 to 255) that counts as a fully white floor
        self.white_level = self.declare_parameter('white_level', 230.0).value
        self.invert = self.declare_parameter('invert', False).value
        self.noise_stddev = self.declare_parameter('noise_stddev', 0.0).value
        rate = self.declare_parameter('rate', 20.0).value

        self.readings = [0.0] * self.channels
        for index in range(self.channels):
            self.create_subscription(Image, f'/ir/raw/ch{index}',
                                     partial(self.on_image, index), qos_profile_sensor_data)
        self.analog_pub = self.create_publisher(Float32MultiArray, '/ir/analog', 10)
        self.create_timer(1.0 / rate, self.publish)

    def on_image(self, index, msg: Image):
        if not msg.data:
            return
        # Mean of all bytes is the average brightness of the spot under this channel
        level = sum(msg.data) / len(msg.data) / self.white_level
        level = min(max(level, 0.0), 1.0)
        if self.invert:
            level = 1.0 - level
        self.readings[index] = level * self.v_ref

    def publish(self):
        # Noise is added here, not in on_image, so every published sample gets a fresh draw
        noisy = [min(max(volts + random.gauss(0.0, self.noise_stddev), 0.0), self.v_ref)
                 for volts in self.readings]
        self.analog_pub.publish(Float32MultiArray(data=noisy))


def main():
    rclpy.init()
    node = IrArray()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
