#!/usr/bin/env python3
"""Open and close the gripper from joystick buttons.

Subscribes:  /joy              sensor_msgs/Joy
Publishes:   /gripper/command  std_msgs/Float64  drive-jaw angle in rad (+ closes)

Button indices and angles come from the controller yaml in trident_teleop/config.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64


class GripperTeleop(Node):
    def __init__(self):
        super().__init__('gripper_teleop')
        self.close_button = self.declare_parameter('close_button', 0).value
        self.open_button = self.declare_parameter('open_button', 1).value
        self.close_angle = self.declare_parameter('close_angle', 0.09).value
        self.open_angle = self.declare_parameter('open_angle', -1.0).value

        self.prev_buttons = []
        self.command_pub = self.create_publisher(Float64, '/gripper/command', 10)
        self.create_subscription(Joy, '/joy', self.on_joy, 10)

    def pressed(self, buttons, index):
        """True only on the message where the button goes from up to down."""
        if index >= len(buttons):
            return False
        was_down = index < len(self.prev_buttons) and self.prev_buttons[index]
        return bool(buttons[index]) and not was_down

    def on_joy(self, msg: Joy):
        if self.pressed(msg.buttons, self.close_button):
            self.command_pub.publish(Float64(data=self.close_angle))
        elif self.pressed(msg.buttons, self.open_button):
            self.command_pub.publish(Float64(data=self.open_angle))
        self.prev_buttons = list(msg.buttons)


def main():
    rclpy.init()
    node = GripperTeleop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
