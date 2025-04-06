from screen import Screen, RED, YELLOW, GREEN
from ball import Ball

BRICK_WIDTH = 30
BRICK_HEIGHT = 8
BRICK_PADDING = 4
BRICKS_PER_ROW = 7
ROWS = 4


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

    def draw(self, screen: Screen):
        """Draw brick."""
        screen.fbuf.fill_rect(self.x, self.y, self.width, self.height, self.color)


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

    def draw(self, screen: Screen):
        """Draw all bricks in the row."""
        for brick in self.bricks:
            if brick is not None:
                brick.draw(screen)

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
