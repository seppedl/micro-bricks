"""
Threaded breakout game with frame buffer

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
from helpers import Joystick, color565

# ============================
# Helper Functions
# ============================

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
SCREEN_HEIGHT = 135
SCREEN_WIDTH = 240
SCREEN_ROTATION = 1 # Landscape mode

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

# Game states
START_SCREEN = 0
PLAYING = 1
GAME_OVER = 2
GAME_WIN = 3
GAME_NEXT_LEVEL = 4

DEBOUNCE = 300_000

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
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    reset=Pin(12, Pin.OUT),
    cs=Pin(9, Pin.OUT),
    dc=Pin(8, Pin.OUT),
    backlight=Pin(13, Pin.OUT),
    rotation=SCREEN_ROTATION)


# FrameBuffer needs 2 bytes for every RGB565 pixel
buffer_width = SCREEN_WIDTH
buffer_height = SCREEN_HEIGHT + 1
buffer = bytearray(buffer_width * buffer_height * 2)
fbuf = framebuf.FrameBuffer(buffer, buffer_width, buffer_height, framebuf.RGB565)

render_frame = False

# ============================
# CLASSES
# ============================

class Paddle:
    def __init__(self):
        self.x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
        self.y = SCREEN_HEIGHT - PADDLE_HEIGHT - 5
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
        elif self.x > SCREEN_WIDTH - self.width:
            self.x = SCREEN_WIDTH - self.width
    
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
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2 - self.radius - 2
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
        elif self.x > SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.x_speed = -self.x_speed

        # Bounce off top screen edge
        if self.y < BRICK_PADDING + self.radius:
            self.y = BRICK_PADDING + self.radius
            self.y_speed = -self.y_speed

        # Drop through bottom screen edge & return True to indicate we lose a life
        if self.y > SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT
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
               color (int): color of the brick.
        """
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
        """Draw all bricks in the row."""
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


class High_score:
    def __init__(self):
        self.high_score = 0
        self._load_high_score()

    def _load_high_score(self):
        """
        Load the high score from a file.
        Returns: int: The high score.
        """
        try: 
            with open("high_score.txt", "r") as file: 
                self.high_score = int(file.read())
        except OSError:  
            self.high_score = 0 
        return self.high_score

    def _save_high_score(self):
        """
        Save the high score to a file.
        """
        with open("high_score.txt", "w") as file:
            file.write(str(self.high_score))

    def update_high_score(self, current_score: int):
        """
        Update the high score if the current score is higher.
        Args:  score (int): The current score.
        """
        if current_score > self.high_score:
            self.high_score = current_score
            self._save_high_score()


def splash_screen(data_rows: list[int], text: list[str], high_score: High_score):
    """
    Display a splash screen using the bits in the data_rows.
    Args:  data_rows (list[int]): List of hex values to display as blocks.
           text (list[str]): List of strings to display as text.
    """
    global fbuf, buffer, buffer_width, buffer_height, joystick, render_frame
    fbuf.fill(BLACK)

    start_x = 5
    start_y = 20

    for row_index, hex_value in enumerate(data_rows):
        if 0 <= row_index <= 1:
            color = RED
        elif 2 <= row_index <= 4:
            color = YELLOW 
        else:
            color = GREEN

        for bit_index in range(22):  # Iterate over 22 bits
            if (hex_value >> (21 - bit_index)) & 1:  
                x = start_x + bit_index * (SPLASH_WIDTH + SPLASH_PADDING)
                y = start_y + row_index * (SPLASH_WIDTH + SPLASH_PADDING)
                fbuf.fill_rect(x, y, SPLASH_WIDTH, SPLASH_HEIGHT, color)
    fbuf.text("High: " + str(high_score.high_score), 160, 120, WHITE)
    fbuf.text(text[0], 5, 100, WHITE)
    fbuf.text(text[1], 5, 120, WHITE) 

    # Wait for the frame to be rendered & update the display
    while render_frame:
        pass
    display.blit_buffer(buffer, 0, 0, buffer_width, buffer_height)


def create_bricks() -> list[BrickRow]:
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
    return bricks


def create_lives(lives: int) -> list[Ball]:
    """
    Create a list of small balls to represent lives
    Args:  lives (int): Number of lives left
    """
    lives_balls = []
    for i in range(0, lives):
        life_ball = Ball(Paddle(), radius=3, color=WHITE)
        life_ball.x = 5 + (i - 1) * 7
        life_ball.y = 7
        life_ball.x_speed = 0
        lives_balls.append(life_ball)
    return lives_balls


def main_loop():
    global fbuf, buffer, buffer_width, buffer_height, joystick
    global render_frame

    game_state = START_SCREEN  # Start at the splash screen
    paddle = Paddle()
    high_score =High_score()
    level = 1

    try:
        while True:
            if game_state == START_SCREEN:  # Startup screen & init game state
                # Generate bricks
                bricks = create_bricks()
                lives = 3  
                lives_balls = create_lives(lives)
                score = 0
                current_score = 0
                level = 1
                # Initialize paddle and ball
                ball = Ball(paddle, radius=5, color=WHITE)
                paddle.width = PADDLE_WIDTH
                paddle.height = PADDLE_HEIGHT

                render_frame = False
                splash_screen(
                    [0x060046, 0x056B54, 0x054A64, 0x064A46, 0x054A62, 0x054A52, 0x074B56],
                    ["Press A to start", "Press B to exit"], 
                    high_score
                )

                if joystick.button_a() == 0:  # Transition to PLAYING state when A is pressed
                    game_state = PLAYING
                    sleep_us(DEBOUNCE)  # Debounce delay

            elif game_state == PLAYING and lives > 0 and score < 28:  # Game loop
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

            elif game_state == PLAYING and (lives == 0 or score == 28):  # Game over or win
                if lives == 0:
                    game_state = GAME_OVER  # Losing state
                elif score == 28:
                    level += 1
                    game_state = GAME_NEXT_LEVEL  # Transition to next level

            if game_state == GAME_OVER:  # Game over screen
                high_score.update_high_score(current_score)
                splash_screen(
                    [0x0276DC, 0x025490, 0x025494, 0x0256DC, 0x025298, 0x025294, 0x0376D4],
                    ["Press A to restart", "Press B to exit"],
                    high_score
                )
                if joystick.button_a() == 0:  # Restart game when A is pressed
                    game_state = START_SCREEN
                    sleep_us(DEBOUNCE) 

            if game_state == GAME_NEXT_LEVEL:  # Next level screen
                current_score += score
                high_score.update_high_score(current_score)
                splash_screen(
                    [0x04548, 0x04548, 0x04568, 0x05578, 0x05558, 0x05548, 0x03948],
                    ["Press A for next level: " + str(level),  "Press B to exit"],
                    high_score
                )
                if joystick.button_a() == 0:  # Start next level when A is pressed
                    # Reinitialize bricks and ball for the next level
                    bricks = create_bricks()
                    ball.reset_pos(paddle)
                    paddle.width = max(PADDLE_WIDTH - 10, PADDLE_WIDTH // 2)  # Decrease paddle size
                    paddle.height = PADDLE_HEIGHT
                    game_state = PLAYING
                    lives += 1
                    lives_balls = create_lives(lives)
                    score = 0
                    sleep_us(DEBOUNCE)  # Debounce delay
            
            if joystick.button_b() == 0:  # Exit game when B is pressed
                break
    except KeyboardInterrupt:
        pass


def render_thread():
    """"Threaded function to handle SPI rendering on a separate core."""
    global fbuf, buffer, buffer_width, buffer_height, render_frame
    global display, SCREEN_HEIGHT, SCREEN_WIDTH, SCREEN_ROTATION

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
