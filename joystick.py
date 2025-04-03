from machine import Pin
class Joystick:
    def __init__(self):
        # Map buttons
        self.button_a = Pin(15, Pin.IN, Pin.PULL_UP)
        self.button_b = Pin(17, Pin.IN, Pin.PULL_UP)
        # Map joystick
        self.joy_up = Pin(2,Pin.IN, Pin.PULL_UP)
        self.joy_down = Pin(18,Pin.IN, Pin.PULL_UP)
        self.joy_left = Pin(16 ,Pin.IN, Pin.PULL_UP)
        self.joy_right = Pin(20 ,Pin.IN, Pin.PULL_UP)
        self.joy_click = Pin(3, Pin.IN, Pin.PULL_UP)
