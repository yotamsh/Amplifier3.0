"""
Concrete animation implementations for the game system
"""

import math
from typing import List, Tuple, TYPE_CHECKING

from .base_classes import Animation

if TYPE_CHECKING:
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel


class RainbowAnimation(Animation):
    """
    Continuous rainbow cycle animation.
    
    Creates a flowing rainbow pattern across specified LED range
    with configurable speed and hue shifting.
    """
    
    def __init__(self, led_range: Tuple[int, int], speed_ms: int = 50, hue_shift_per_frame: int = 8):
        """
        Initialize rainbow animation.
        
        Args:
            led_range: (start_led, end_led) tuple defining LED range
            speed_ms: Animation update interval in milliseconds  
            hue_shift_per_frame: Degrees to shift hue each frame
        """
        super().__init__(speed_ms, f"Rainbow({led_range[0]}-{led_range[1]})")
        self.led_range: Tuple[int, int] = led_range
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
    
    def advance(self, dt: float) -> None:
        """Advance rainbow hue offset"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render rainbow pattern to LED strips"""
        if not led_strips:
            return
            
        strip = led_strips[0]  # Use first strip
        start_led, end_led = self.led_range
        led_count = end_led - start_led
        
        if led_count <= 0:
            return
            
        for i in range(led_count):
            led_index = start_led + i
            if led_index < strip.num_pixels():
                # Calculate hue based on position and offset
                hue = (i * 360 / led_count + self.hue_offset) % 360
                color = self._hsv_to_pixel(hue, 1.0, 1.0)
                strip[led_index] = color
    
    def _hsv_to_pixel(self, h: float, s: float, v: float) -> 'Pixel':
        """Convert HSV to Pixel RGB"""
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        h = h % 360  # Wrap hue
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:  # 300 <= h < 360
            r, g, b = c, 0, x
        
        r_int = int((r + m) * 255)
        g_int = int((g + m) * 255)
        b_int = int((b + m) * 255)
        
        return Pixel(r_int, g_int, b_int)


class BreathingAnimation(Animation):
    """
    Smooth breathing/pulsing animation with configurable color and brightness range.
    
    Uses sine wave for natural breathing effect across entire strip or specified range.
    """
    
    def __init__(self, color: 'Pixel', speed_ms: int = 100, 
                 brightness_range: Tuple[float, float] = (0.1, 1.0),
                 led_range: Tuple[int, int] = None):
        """
        Initialize breathing animation.
        
        Args:
            color: Base color to pulse
            speed_ms: Animation update interval
            brightness_range: (min_brightness, max_brightness) tuple
            led_range: LED range to affect, None for entire strip
        """
        super().__init__(speed_ms, "Breathing")
        self.base_color: 'Pixel' = color
        self.brightness_range: Tuple[float, float] = brightness_range
        self.led_range: Tuple[int, int] = led_range
        self.phase: float = 0.0
    
    def advance(self, dt: float) -> None:
        """Advance breathing phase"""
        # Convert dt to appropriate phase increment
        phase_speed = 2.0  # Radians per second for breathing speed
        self.phase += phase_speed * dt
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render breathing effect to LED strips"""
        if not led_strips:
            return
            
        # Calculate current brightness using sine wave
        min_brightness, max_brightness = self.brightness_range
        brightness_range = max_brightness - min_brightness
        current_brightness = min_brightness + brightness_range * (0.5 + 0.5 * math.sin(self.phase))
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create dimmed color
        dimmed_color = Pixel(
            int(self.base_color.red * current_brightness),
            int(self.base_color.green * current_brightness),
            int(self.base_color.blue * current_brightness)
        )
        
        # Apply to all strips
        for strip in led_strips:
            if self.led_range:
                start_led, end_led = self.led_range
                for i in range(start_led, min(end_led, strip.num_pixels())):
                    strip[i] = dimmed_color
            else:
                # Apply to entire strip
                strip[:] = dimmed_color


class StaticColorAnimation(Animation):
    """
    Simple static color animation for testing and simple effects.
    """
    
    def __init__(self, color: 'Pixel', led_range: Tuple[int, int] = None):
        """
        Initialize static color animation.
        
        Args:
            color: Color to display
            led_range: LED range to affect, None for entire strip
        """
        super().__init__(1000, "StaticColor")  # Slow update since it's static
        self.color: 'Pixel' = color
        self.led_range: Tuple[int, int] = led_range
    
    def advance(self, dt: float) -> None:
        """No advancement needed for static color"""
        pass
    
    def render(self, led_strips: List['LedStrip']) -> None:
        """Render static color to LED strips"""
        for strip in led_strips:
            if self.led_range:
                start_led, end_led = self.led_range
                for i in range(start_led, min(end_led, strip.num_pixels())):
                    strip[i] = self.color
            else:
                strip[:] = self.color
