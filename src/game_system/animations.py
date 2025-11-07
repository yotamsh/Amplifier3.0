"""
Animation base class and concrete implementations for the game system
"""

import math
import time
from abc import ABC, abstractmethod
from typing import List, Tuple, TYPE_CHECKING

from .animation_helpers import AnimationHelpers

if TYPE_CHECKING:
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel


class Animation(ABC):
    """
    Abstract base class for time-based animations.
    
    Provides non-blocking, time-based animation updates with configurable speed.
    Each animation operates on a single LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int):
        """
        Initialize animation with timing control.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Update interval in milliseconds
        """
        self.strip: 'LedStrip' = strip
        self.speed_ms: int = speed_ms
        self.last_update: float = time.time()
    
    def get_name(self) -> str:
        """Get animation name from class name"""
        return self.__class__.__name__
    
    def update_if_needed(self) -> bool:
        """
        Update animation if enough time has passed.
        
        Returns:
            True if animation was updated, False if skipped
        """
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            self.advance()
            self.strip.show()
            self.last_update = now
            return True
        return False
    
    @abstractmethod
    def advance(self) -> None:
        """
        Advance animation by one frame (override in subclasses).
        
        Should update the strip's pixel data but not call show().
        """
        pass


class RainbowAnimation(Animation):
    """
    Continuous rainbow cycle animation.
    
    Creates a flowing rainbow pattern across the entire LED strip
    with configurable speed and hue shifting.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50, hue_shift_per_frame: int = 8):
        """
        Initialize rainbow animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds  
            hue_shift_per_frame: Degrees to shift hue each frame
        """
        super().__init__(strip, speed_ms)
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Update all strip pixels
        num_pixels = self.strip.num_pixels()
        
        for i in range(num_pixels):
            # Calculate hue based on position and offset
            hue = (i * 360 / num_pixels + self.hue_offset) % 360
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.strip[i] = color


class BreathingAnimation(Animation):
    """
    Smooth breathing/pulsing animation with configurable color and brightness range.
    
    Uses sine wave for natural breathing effect across the entire LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', speed_ms: int = 100, 
                 brightness_range: Tuple[float, float] = (0.1, 1.0)):
        """
        Initialize breathing animation.
        
        Args:
            strip: LED strip to operate on
            color: Base color to pulse
            speed_ms: Animation update interval
            brightness_range: (min_brightness, max_brightness) tuple
        """
        super().__init__(strip, speed_ms)
        self.base_color: 'Pixel' = color
        self.brightness_range: Tuple[float, float] = brightness_range
        self.phase: float = 0.0
        self.phase_speed: float = 0.1  # Phase increment per frame (adjust for breathing speed)
    
    def advance(self) -> None:
        """Advance breathing phase and update strip pixels"""
        self.phase += self.phase_speed
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        
        # Calculate current brightness using sine wave
        min_brightness, max_brightness = self.brightness_range
        brightness_range = max_brightness - min_brightness
        current_brightness = min_brightness + brightness_range * (0.5 + 0.5 * math.sin(self.phase))
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create dimmed color
        dimmed_color = Pixel(
            int(self.base_color.r * current_brightness),
            int(self.base_color.g * current_brightness),
            int(self.base_color.b * current_brightness)
        )
        
        # Update entire strip
        self.strip[:] = dimmed_color


class StaticColorAnimation(Animation):
    """
    Simple static color animation for testing and simple effects.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel'):
        """
        Initialize static color animation.
        
        Args:
            strip: LED strip to operate on
            color: Color to display
        """
        super().__init__(strip, 1000)  # Slow update since it's static
        self.color: 'Pixel' = color
        self._initialized: bool = False
    
    def advance(self) -> None:
        """Set static color once, then no changes needed"""
        if not self._initialized:
            # Update entire strip once
            self.strip[:] = self.color
            self._initialized = True


class AmplifyAnimation(Animation):
    """
    Rainbow animation that only illuminates LED segments corresponding to pressed buttons.
    
    Each button controls a segment of the LED strip. Only pressed button segments
    show the rainbow pattern, while unpressed segments remain black.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50, 
                 hue_shift_per_frame: int = 12):
        """
        Initialize amplify animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons that control segments
            speed_ms: Animation update interval in milliseconds
            hue_shift_per_frame: Degrees to shift hue each frame (higher = faster)
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
        
        # Calculate LEDs per button (constant for this animation instance)
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
    
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """
        Update which buttons are currently pressed.
        
        Args:
            pressed_buttons: List of boolean values indicating button press state
        """
        self.pressed_buttons = pressed_buttons.copy()
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels based on button state"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Update all strip pixels
        num_pixels = self.strip.num_pixels()
        
        for led_pos in range(num_pixels):
            # Calculate which button segment this LED belongs to
            button_index = led_pos // self.leds_per_button
            
            # Check if this button is pressed (with bounds checking)
            if button_index < self.button_count and self.pressed_buttons[button_index]:
                # Calculate rainbow hue based on LED position and offset
                hue = (led_pos * 360 / num_pixels + self.hue_offset) % 360
                color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                self.strip[led_pos] = color
            else:
                # Button not pressed or out of bounds - set LED to black
                self.strip[led_pos] = Pixel(0, 0, 0)
