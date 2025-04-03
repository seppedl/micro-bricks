"""
Threaded bouncing boxes with frame buffer

Uses a single shot function for second core SPI handler.
This cleans itself when the function exits removing the
need for a garbage collection call.

"""
from gc import collect
collect()

# import libraries
import math
import array
from machine import Pin, SPI
import framebuf
from random import random, seed, randint
from utime import sleep_us, ticks_cpu, ticks_us
import _thread
import st7789 as st7789
from joystick import Joystick

# ============================
# Helper Functions
# ============================
def color565(r, g, b):
    """Convert RGB888 to RGB565."""
    return (((g & 0b00011100) << 3) + ((r & 0b11111000) >> 3) << 8) + (b & 0b11111000) + ((g & 0b11100000) >> 5)


RED = color565(0, 0, 255)
GREEN = color565(0, 255, 0)
YELLOW = color565(0, 255, 255)
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)


def clear_display():
    """Clear the display."""
    global fbuf, display, buffer, buffer_width, buffer_height
    fbuf.fill(BLACK)
    display.blit_buffer(buffer, 0, 0, buffer_width, buffer_height)


# ============================
# Constants and Configuration
# ============================
SCREEN_WIDTH = 135
SCREEN_HEIGHT = 240
SCREEN_ROTATION = 1

PADDLE_WIDTH = 70
PADDLE_HEIGHT = 10
PADDLE_COLOR = WHITE
PADDLE_SPEED = 10

BRICK_WIDTH = 30
BRICK_HEIGHT = 8
BRICK_PADDING = 4
BRICKS_PER_ROW = 7
ROWS = 4

BALL_SPEED = 3

SPLASH_WIDTH = 8
SPLASH_HEIGHT = 5
SPLASH_PADDING = 2


# ============================
# set up SPI and display
spi = SPI(1,
          baudrate=31250000,
          polarity=1,
          phase=1,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(10),
          mosi=Pin(11))

display = st7789.ST7789(
    spi,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    reset=Pin(12, Pin.OUT),
    cs=Pin(9, Pin.OUT),
    dc=Pin(8, Pin.OUT),
    backlight=Pin(13, Pin.OUT),
    rotation=SCREEN_ROTATION)


# FrameBuffer needs 2 bytes for every RGB565 pixel
buffer_width = SCREEN_HEIGHT
buffer_height = SCREEN_WIDTH + 1
buffer_height = 136
buffer = bytearray(buffer_width * buffer_height * 2)
fbuf = framebuf.FrameBuffer(buffer, buffer_width, buffer_height, framebuf.RGB565)

render_frame = False

# ============================
# CLASSES
# ============================

class Paddle:
    def __init__(self):
        self.x = (SCREEN_HEIGHT - PADDLE_WIDTH) // 2
        self.y = SCREEN_WIDTH - PADDLE_HEIGHT - 5
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.speed = PADDLE_SPEED
    
    def move(self, direction: int):
        """
            Move paddle left or right.
            Args: direction: -1 for left, 1 for right
        """
        self.x += self.speed * direction
        if self.x < 0:
            self.x = 0
        elif self.x > SCREEN_HEIGHT - self.width:
            self.x = SCREEN_HEIGHT - self.width
    
    def draw(self):
        """Draw paddle."""
        global fbuf
        fbuf.fill_rect(self.x, self.y, self.width, self.height, PADDLE_COLOR)

    def update(self):
        """Update paddle position."""
        global joystick
        if joystick.joy_left() == 0:
            self.move(-1)
        elif joystick.joy_right() == 0:
            self.move(1)
        self.draw()

    def hit(self, ball: Ball) -> bool:
        """Check if the ball hits the paddle and adjust its position."""
        if (
            self.x <= ball.x <= self.x + self.width 
            and self.y <= ball.y + ball.radius <= self.y + self.height
        ):
            # Adjust the ball's position to be just above the paddle
            ball.y = self.y - ball.radius - 2
            return True
        return False


class Ball:
    def __init__(self, paddle: Paddle, radius: int, color: int): 
        """
        Initialize the ball.

        Args:
            paddle (Paddle): The paddle object to position the ball on.
            radius (int): Radius of the ball.
            color (int): RGB565 color value of the ball.
        """
        self.radius = radius
        self.color = color
        self.reset_pos(paddle)
        self.x_speed = BALL_SPEED
        self.y_speed = -BALL_SPEED

        # Position the ball in the middle of the paddle
        self.x = paddle.x + (paddle.width // 2)
        self.y = paddle.y - radius - 2  # Place the ball just above the paddle

    def reset_pos(self, paddle: Paddle):
        """Reset ball position to the center of the paddle.
        Args:  Paddle: The paddle object to position the ball on.
        """
        self.x = SCREEN_HEIGHT // 2
        self.y = SCREEN_WIDTH // 2 - self.radius - 2
        self.x_speed = BALL_SPEED
        self.y_speed = -BALL_SPEED

    def update_pos(self):
        """Update ball position."""
        self.x += self.x_speed  
        self.y += self.y_speed  

        # Bounce off left or right screen edge
        if self.x < 0:
            self.x = 0
            self.x_speed = -self.x_speed
        elif self.x > SCREEN_HEIGHT:
            self.x = SCREEN_HEIGHT - self.radius
            self.x_speed = -self.x_speed

        # Bounce off top screen edge
        if self.y < BRICK_PADDING + self.radius:
            self.y = BRICK_PADDING + self.radius
            self.y_speed = -self.y_speed

        # Drop through bottom screen edge & return True to indicate we lose a life
        if self.y > SCREEN_WIDTH:
            self.y = SCREEN_WIDTH
            self.y_speed = -self.y_speed
            return True

    def draw(self):
        """Draw ball."""
        global fbuf
        fbuf.ellipse(self.x, self.y, self.radius, self.radius, self.color, True)


class Brick:
    def __init__(self, x: int, y: int, width: int, height: int, color: int):
        """
        Initialize a brick.
        Args:  x (int): x-coordinate of the brick.  
               y (int): y-coordinate of the brick.  
               width (int): width of the brick.  
               height (int): height of the brick.  
               color (int): color of the brick."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        """Draw brick."""
        global fbuf
        fbuf.fill_rect(self.x, self.y, self.width, self.height, self.color)


class BrickRow:
    def __init__(self, brick_width: int, brick_height: int, padding:int, offset_top: int, color: int):
        """
        Initialize a row of bricks.
        Args:  brick_width (int): width of each brick.  
               brick_height (int): height of each brick.
               padding (int): padding between bricks.
               offset_top (int): y-coordinate of the top of the row.
               color (int): color of the bricks.
        """        
        self.brick_width = brick_width
        self.brick_height = brick_height
        self.color = color
        self.padding = padding
        self.offset_top = offset_top
        self.bricks = [Brick(padding + i * (brick_width + padding), offset_top, brick_width, brick_height, color) for i in range(BRICKS_PER_ROW)]
        self.brick_x = [padding + i * (brick_width + padding) for i in range(BRICKS_PER_ROW)]
        self.brick_y = [offset_top] * BRICKS_PER_ROW

    def draw(self):
        global fbuf
        for brick in self.bricks:
            if brick is not None:
                brick.draw()

    def hit(self, ball: Ball) -> bool:
        """
        Check if the ball hits any brick in the row and remove it if hit.
        Args:  ball (Ball): The ball object to check for collision.
        Returns: bool: True if the ball hits a brick, False otherwise.
        """
        for i, brick in enumerate(self.bricks):
            if brick is not None:
                if (brick.x <= ball.x <= brick.x + brick.width) and (brick.y <= ball.y <= brick.y + brick.height):
                    # Remove the brick by setting it to None
                    self.bricks[i] = None
                    return True
        return False

def splash_screen(data_rows: list[int]):
    """
    Display a splash screen using the bits in the data_rows.
    Args:  data_rows (list[int]): List of hex values to display as blocks.
    """
    global fbuf, buffer, buffer_width, buffer_height, joystick, render_frame
    fbuf.fill(BLACK)

    start_x = 5
    start_y = 20

    for row_index, hex_value in enumerate(data_rows):
        binary = bin(hex_value)[2:]  # Convert to binary
        binary = '{:0>22}'.format(binary)  # Pad to 22 columns
        if 0 <= row_index <= 1:
            color = RED
        elif 2 <= row_index <= 4:
            color = YELLOW 
        else:
            color = GREEN
        for bit_index, bit in enumerate(binary):
            if bit == '1':  # Only draw a block for '1'
                x = start_x + bit_index * (SPLASH_WIDTH + SPLASH_PADDING)
                y = start_y + row_index * (SPLASH_WIDTH + SPLASH_PADDING)
                fbuf.fill_rect(x, y, SPLASH_WIDTH, SPLASH_HEIGHT, color)
    fbuf.text("Press A to start", 5, 100, WHITE) 
    fbuf.text("Press B to exit", 5, 120, WHITE) 

    # Wait for the frame to be rendered & update the display
    while render_frame:
        pass
    display.blit_buffer(buffer, 0, 0, buffer_width, buffer_height)


def main_loop():
    global fbuf, buffer, buffer_width, buffer_height, joystick
    global render_frame

    state = 0  # 0 = start screen, 1 = game, 2 = game over, 3 = game win

    try:
        while True:
            if state == 0:  # Startup screen & init game state
                bricks = []
                for row in range(ROWS):
                    if row == 0:
                        color = RED
                    elif row == 1:
                        color = YELLOW
                    else:
                        color = GREEN
                    bricks.append(
                        BrickRow(BRICK_WIDTH, 
                                BRICK_HEIGHT, 
                                BRICK_PADDING, 
                                10 + row * (BRICK_HEIGHT + BRICK_PADDING), 
                                color))
                score = 0
                lives = 3

                paddle = Paddle()
                ball = Ball(paddle, radius=5, color=WHITE)
                # Create a list of small balls to represent lives
                lives_balls = []
                for i in range(0, lives):  
                    life_ball = Ball(paddle, radius=3, color=WHITE)
                    life_ball.x = 5 + (i - 1) * 7  
                    life_ball.y = 7
                    life_ball.x_speed = 0  
                    lives_balls.append(life_ball)

                render_frame = False
                splash_screen([0x060046, 0x056B54, 0x054A64, 0x064A46, 0x054A62, 0x054A52, 0x074B56])
                
                if joystick.button_a() == 0:  # Transition to game state when A is pressed
                    state = 1
                    lives = 3
                    score = 0

            elif state == 1 and lives > 0 and score < 28:  # Game state
                paddle.update()
                if ball.update_pos():  # If ball is out of bounds, lose a life and reset ball position
                    lives -= 1
                    lives_balls.pop()
                    ball.reset_pos(paddle)  # Reset ball position to the center of the paddle

                if paddle.hit(ball):
                    ball.y_speed = -abs(ball.y_speed)
                for row in bricks:
                    if row.hit(ball):
                        ball.y_speed = -ball.y_speed
                        score += 1
                        break
                for i in range(1, len(lives_balls)):
                    lives_balls[i].draw()
                for row in bricks:
                    row.draw()
                ball.draw()
                paddle.draw()

                while render_frame:
                    pass
                render_frame = True
                # Start SPI handler on core 1
                spi_thread = _thread.start_new_thread(render_thread, ())

            if state == 1 and (lives == 0 or score == 28):  # Game over or win:
                if lives > 0: 
                    state= 3 # Winning state
                else:
                    state = 2 # Losing state
            if state == 2:  # Game over screen
                splash_screen([0x0276DC, 0x025490, 0x025494, 0x0256DC, 0x025298, 0x025294, 0x0376D4])

            if state == 3:  # Game win screen
                splash_screen([0x04548, 0x04548, 0x04568, 0x05578, 0x05558, 0x05548, 0x03948])   

            if state != 1 and joystick.button_a() == 0:  # Transition to start state when A is pressed
                state = 0
                sleep_us(1_000_000)  # Debounce delay

            if joystick.button_b() == 0:  # Exit game when B is pressed
                break 
    except KeyboardInterrupt:
        pass


def render_thread():
    global fbuf, buffer, buffer_width, buffer_height, render_frame, spi
    global display, SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_ROTATION

    display.blit_buffer(buffer, 0, 0, buffer_width, buffer_height)
    fbuf.fill(0)

    render_frame = False
    # thread will exit and self clean removing need for garbage collection


if __name__ == "__main__":
    joystick = Joystick()
    main_loop()

    # Clean up
    clear_display()
    buffer = None
    fbuf = None
