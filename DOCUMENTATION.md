# Program Documentation

## Overview
This program is a simple game implemented in MicroPython for the Raspberry Pi Pico with a Pico-LCD-1.14 display. The game involves controlling a paddle to control a ball to break a brick wall and score points. The program includes a splash screen, game over screen, and a main game loop.

## Framebuffer
The program uses a framebuffer to draw the game graphics. The framebuffer is a 2D array that represents the pixels on the display. The program uses the micropyhton `framebuf` module to create and manipulate the framebuffer. The framebuffer is then copied to the display using the `blit` method.

If the program crashes, the framebuffer is not always reset, causing the program to crash due to lack of memeory. 
A hard reset is required to fix this issue.

## Multithreading
The program uses multithreading to handle the game logic and the display updates separately. The `threading` module is used to create and manage the threads. The game logic is run in a separate thread from the display updates to ensure smooth gameplay and responsive controls.

## Game Logic
The game logic is implemented in the `game_loop` function. This function runs in a separate thread and handles the following tasks:
- Updating the game state based on user input andgame flow.
- Updating ball position, paddle position, and bricks on the screen.
- Checking for collisions between the ball, borders, paddle and bricks.
- Updating the score based on the player's performance
- Sending the updated game state to the display thread for rendering.
