from machine import Pin, SPI
import _thread
from st7789 import ST7789
from framebuf import FrameBuffer, RGB565
import gc


def color565(red: int, green: int, blue: int) -> int:
    """Convert RGB888 to RGB565."""
    return (
        (((green & 0b00011100) << 3) + ((red & 0b11111000) >> 3) << 8) 
        + (blue & 0b11111000) 
        + ((green & 0b11100000) >> 5)
        )


RED = color565(0, 0, 255)
GREEN = color565(0, 255, 0)
YELLOW = color565(0, 255, 255)
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)


class Screen:
    """Class to handle the ST7789 display and framebuffer."""
    def __init__(self, width: int, height: int, rotation: int):
        self.spi: SPI = SPI(1,
            baudrate=31250000,
            polarity=1,
            phase=1,
            bits=8,
            firstbit=SPI.MSB,
            sck=Pin(10),
            mosi=Pin(11))
        self.width: int = width 
        self.height: int = height
        self.rotation: int = rotation
        self.display = ST7789(
            self.spi,
            self.height,
            self.width,
            reset=Pin(12, Pin.OUT),
            cs=Pin(9, Pin.OUT),
            dc=Pin(8, Pin.OUT),
            backlight=Pin(13, Pin.OUT),
            rotation=self.rotation)
        # FrameBuffer needs 2 bytes for every RGB565 pixel
        self.buffer_width = self.width
        self.buffer_height = self.height + 1
        self.buffer = bytearray(self.buffer_width * self.buffer_height * 2)
        self.fbuf: FrameBuffer = FrameBuffer(self.buffer, self.buffer_width, self.buffer_height, RGB565)
        self.render_frame = False
    
    def refresh(self):
        self.display.blit_buffer(self.buffer, 0, 0, self.buffer_width, self.buffer_height)

    def clear(self, refresh: bool = True):
        if self.fbuf is None:
            return
        self.fbuf.fill(BLACK)
        if refresh:
            self.refresh()

    def render_thread(self):
        """Threaded function to handle SPI rendering on a separate core."""
        self.display.blit_buffer(self.buffer, 0, 0, self.buffer_width, self.buffer_height)
        self.fbuf.fill(BLACK)
        self.render_frame = False
        # thread will exit and self clean removing need for garbage collection

    def cleanup(self):
        """Free resources used by the framebuffer and SPI."""
        self.buffer = None
        self.fbuf = None
        self.spi.deinit()
        gc.collect()
