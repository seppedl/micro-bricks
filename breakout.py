"""
Threaded breakout game using frame buffer

Author: Seppe De Loore - 2025
"""

from random import randint
from utime import sleep_us
from screen import Screen, RED, YELLOW, GREEN, WHITE
from paddle import Paddle, PADDLE_WIDTH, PADDLE_HEIGHT
from ball import Ball
from bricks import BrickRow, create_bricks, BRICK_PADDING
import _thread

from joystick import Joystick

# ============================
# Constants and Configuration
# ============================

SCREEN_HEIGHT = 135
SCREEN_WIDTH = 240
SCREEN_ROTATION = 1 # Landscape mode

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

# load environment variables
try:
    DISABLE_B = 0
    with open(".env", "r") as file:
        for line in file:
            key, value = line.strip().split("=")
            if key == "DISABLE_B":
                DISABLE_B = int(value)
except:
    DISABLE_B = 0


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


def splash_screen(screen: Screen, data_rows: list[int], text: list[str], high_score: High_score):
    """
    Display a splash screen using the bits in the data_rows.
    Args:  data_rows (list[int]): List of hex values to display as blocks.
           text (list[str]): List of strings to display as text.
    """
    screen.clear(refresh=False)

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
                screen.fbuf.fill_rect(x, y, SPLASH_WIDTH, SPLASH_HEIGHT, color)
    screen.fbuf.text("High: " + str(high_score.high_score), 160, 120, WHITE)
    screen.fbuf.text(text[0], 5, 100, WHITE)
    screen.fbuf.text(text[1], 5, 120, WHITE) 

    # Wait for the frame to be rendered & update the display
    while screen.render_frame: 
        pass
    screen.display.blit_buffer(screen.buffer, 0, 0, screen.buffer_width, screen.buffer_height)


def create_lives(screen: Screen, paddle: Paddle, lives: int) -> list[Ball]:
    """
    Create a list of small balls to represent lives.
    Args:
        screen (Screen): The screen object.
        paddle (Paddle): The paddle object.
        lives (int): Number of lives left.
    Returns:
        list[Ball]: List of Ball objects representing lives.
    """
    lives_balls = []
    for i in range(0, lives):
        life_ball = Ball(screen, paddle, radius=3, color=WHITE, brick_padding=BRICK_PADDING)
        life_ball.x = 5 + (i - 1) * 7
        life_ball.y = 7
        life_ball.x_speed = 0
        lives_balls.append(life_ball)
    return lives_balls


def main_loop(screen, joystick):
    game_state = START_SCREEN  # Start at the splash screen
    paddle = Paddle(screen)
    high_score = High_score()
    level = 1
    ball_stuck = True  # Ball starts stuck to the paddle

    try:
        while True:
            if game_state == START_SCREEN:  # Startup screen & init game state
                # Generate bricks
                bricks = create_bricks()
                lives = 3  
                lives_balls = create_lives(screen, paddle, lives)
                score = 0
                current_score = 0
                level = 1
                ball_stuck = True  # Reset ball to be stuck to the paddle
                # Initialize paddle and ball
                ball = Ball(screen, paddle, radius=5, color=WHITE, brick_padding=BRICK_PADDING)
                paddle.width = PADDLE_WIDTH
                paddle.height = PADDLE_HEIGHT

                screen.render_frame = False
                splash_screen(
                    screen,
                    [0x060046, 0x056B54, 0x054A64, 0x064A46, 0x054A62, 0x054A52, 0x074B56],
                    ["Press A to start", "Press B to exit" if DISABLE_B == 0 else " "], 
                    high_score
                )

                if joystick.button_a() == 0:  # Transition to PLAYING state when A is pressed
                    game_state = PLAYING
                    sleep_us(DEBOUNCE)  # Debounce delay

            elif game_state == PLAYING and lives > 0 and score < 28:  # Game loop
                paddle.update(screen, joystick) 
                if ball_stuck:
                    # Keep the ball stuck to the paddle
                    ball.x = paddle.x + (paddle.width // 2)
                    ball.y = paddle.y - ball.radius - 2
                    screen.fbuf.text("Press A to launch!", 50, SCREEN_HEIGHT // 2 + 5, WHITE)
                    # Launch the ball when "A" is pressed
                    if joystick.button_a() == 0:
                        ball_stuck = False
                        ball.y_speed = -ball.speed
                        ball.x_speed = ball.speed if randint(0, 1) == 0 else -ball.speed
                else:
                    if ball.update_pos():  # If ball is out, lose a life and reset ball
                        lives -= 1
                        lives_balls.pop()
                        ball.reset_pos(paddle) 
                        ball_stuck = True  

                if paddle.hit(ball):
                    ball.y_speed = -abs(ball.y_speed)
                for row in bricks:
                    if row.hit(ball):
                        ball.y_speed = -ball.y_speed
                        score += 1
                        break
                for i in range(1, len(lives_balls)):
                    lives_balls[i].draw(screen)
                for row in bricks:
                    row.draw(screen)
                ball.draw(screen)
                paddle.draw(screen)

                while screen.render_frame:
                    pass
                screen.render_frame = True
                # Start SPI handler on core 1
                spi_thread = _thread.start_new_thread(screen.render_thread, ())

            elif game_state == PLAYING and (lives == 0 or score == 28):  # Game over or win
                if lives == 0:
                    game_state = GAME_OVER  # Losing state
                elif score == 28:
                    level += 1
                    game_state = GAME_NEXT_LEVEL  # Transition to next level

            if game_state == GAME_OVER:  # Game over screen
                current_score += score
                score = 0
                high_score.update_high_score(current_score)
                splash_screen(
                    screen,
                    [0x0276DC, 0x025490, 0x025494, 0x0256DC, 0x025298, 0x025294, 0x0376D4],
                    ["Press A to restart", "Press B to exit" if DISABLE_B == 0 else " "],
                    high_score
                )
                if joystick.button_a() == 0:  # Restart game when A is pressed
                    game_state = START_SCREEN
                    sleep_us(DEBOUNCE) 

            if game_state == GAME_NEXT_LEVEL:  # Next level screen
                current_score += score
                score = 0
                high_score.update_high_score(current_score)
                splash_screen(
                    screen,
                    [0x04548, 0x04548, 0x04568, 0x05578, 0x05558, 0x05548, 0x03948],
                    ["Press A for next level: " + str(level),  "Press B to exit" if DISABLE_B == 0 else " "],
                    high_score
                )
                if joystick.button_a() == 0:  # Start next level when A is pressed
                    # Reinitialize bricks and ball for the next level
                    bricks = create_bricks()
                    ball.reset_pos(paddle)
                    paddle.width = max(paddle.width - 10, PADDLE_WIDTH // 2)  # Decrease paddle size
                    paddle.height = PADDLE_HEIGHT
                    game_state = PLAYING
                    lives += 1
                    lives_balls = create_lives(screen, paddle, lives)
                    score = 0
                    ball_stuck = True 
                    sleep_us(DEBOUNCE)
            
            if DISABLE_B == 0 and joystick.button_b() == 0: 
                break
    except KeyboardInterrupt:
        pass



if __name__ == "__main__":
    try:
        joystick = Joystick()
        screen = Screen(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_ROTATION)
        main_loop(screen, joystick)
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up resources
        screen.clear()
        screen.cleanup()
