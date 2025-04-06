from screen import Screen, WHITE

PADDLE_WIDTH = 70
PADDLE_HEIGHT = 10
PADDLE_COLOR = WHITE
PADDLE_SPEED = 10


class Paddle:
    def __init__(self, screen: Screen):
        """Initialize the paddle."""
        self.screen_width = screen.width
        self.screen_height = screen.height
        self.x = (self.screen_width - PADDLE_WIDTH) // 2
        self.y = self.screen_height - PADDLE_HEIGHT - 5
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
        elif self.x > self.screen_width - self.width:
            self.x = self.screen_width - self.width
    
    def draw(self, screen: Screen):
        """Draw paddle."""
        screen.fbuf.fill_rect(self.x, self.y, self.width, self.height, PADDLE_COLOR)

    def update(self, screen: Screen, joystick: Joystick):
        """Update paddle position."""
        if joystick.joy_left() == 0:
            self.move(-1)
        elif joystick.joy_right() == 0:
            self.move(1)
        self.draw(screen)

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
