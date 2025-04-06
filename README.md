# Breakout Game for Raspberry Pi Pico
This is a simple Breakout game implemented in MicroPython for the Raspberry Pi Pico. The game uses the Pico-LCD-1.14 dDisplay for graphics and input.


## Features
- Classic Breakout gameplay
- Simple and intuitive controls
- Basic collision detection
- Score tracking
- Splash screen and game over screens

## Requirements
- Raspberry Pi Pico
- Pico-LCD-1.14 display
- MicroPython firmware installed on the Pico

## Installation and Setup
1. Connect the Pico-LCD-1.14 display to the Raspberry Pi Pico following the wiring diagram provided in the display's documentation.
2. Download the MicroPython firmware for the Raspberry Pi Pico from the official MicroPython website and install it on the Pico. You can use the Thonny IDE to upload the firmware.
3. Clone or download this repository to your local machine.
4. Open the Thonny IDE and connect to your Raspberry Pi Pico.
5. Copy the contents of the repository to the Pico's file system. You can do this by dragging and dropping the files from your local machine to the Thonny file explorer.
6. Once the files are copied, reset the Pico to start the game (main.py will run automatically and start breakout.py).

## .env file
In the .env file the user can control the behaviour of the joystick B-button.
DISABLE_B = 0 | 1 # Values: 0 =  pressing B quits the program, 1 = pressing B does nothing.