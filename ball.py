from random import randint

from screen import Screen, WHITE
from paddle import Paddle

BALL_SPEED = 3


class Ball:
    def __init__(self, screen: Screen, paddle: Paddle, radius: int, color: int = WHITE, brick_padding: int = 0, speed: int = BALL_SPEED): 
        self.screen_width = screen.width
        self.screen_height = screen.height
        self.radius = radius
        self.color = color
        self.speed = speed
        self.x_speed = self.speed if randint(0, 1) == 0 else -self.speed
        self.y_speed = -self.speed
        self.brick_padding = brick_padding
        self.reset_pos(paddle)

    def reset_pos(self, paddle: Paddle):
        """Reset ball position to the center of the paddle."""
        self.x = self.screen_width // 2
        self.y = self.screen_height // 2 - self.radius - 2
        self.x_speed = self.speed if randint(0, 1) == 0 else -self.speed
        self.y_speed = -self.speed

    def update_pos(self):
        """Update ball position."""
        self.x += self.x_speed  
        self.y += self.y_speed  

        # Bounce off left or right screen edge
        if self.x < 0:
            self.x = 0
            self.x_speed = -self.x_speed
        elif self.x > self.screen_width - self.radius:
            self.x = self.screen_width - self.radius
            self.x_speed = -self.x_speed

        # Bounce off top screen edge
        if self.y < self.brick_padding + self.radius:
            self.y = self.brick_padding + self.radius
            self.y_speed = -self.y_speed

        # Drop through bottom screen edge & return True to indicate we lose a life
        if self.y > self.screen_height:
            self.y = self.screen_height
            self.y_speed = -self.y_speed
            return True

    def draw(self, screen: Screen):
        """Draw ball."""
        screen.fbuf.ellipse(self.x, self.y, self.radius, self.radius, self.color, True)
