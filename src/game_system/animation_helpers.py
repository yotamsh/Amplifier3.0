"""
Helper utilities for animations
"""

import math
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from led_system.pixel import Pixel
else:
    from led_system.pixel import Pixel


class AnimationHelpers:
    """Static helper methods for animations"""
    
    # Color constants
    ORANGE_RED = None  # Will be initialized after Pixel import
    BLACK = None
    WHITE = None
    
    # Party mode color palette
    RED_WINE = None     # Deep red wine color
    GREEN_GRASS = None  # Vibrant grass green
    PURPLE = None       # Rich purple
    SOFT_WHITE = None   # Soft warm white
    
    @staticmethod
    def _init_colors():
        """Initialize color constants (called once)"""
        if AnimationHelpers.ORANGE_RED is None:
            from led_system.pixel import Pixel
            AnimationHelpers.ORANGE_RED = Pixel(255, 69, 0)
            AnimationHelpers.BLACK = Pixel(0, 0, 0)
            AnimationHelpers.WHITE = Pixel(255, 255, 255)
            
            # Party mode color palette
            AnimationHelpers.RED_WINE = Pixel(139, 0, 45)      # Deep red wine
            AnimationHelpers.GREEN_GRASS = Pixel(34, 139, 34)  # Vibrant grass green
            AnimationHelpers.PURPLE = Pixel(138, 43, 226)      # Rich purple (blue-violet)
            AnimationHelpers.SOFT_WHITE = Pixel(255, 248, 220) # Soft warm white (cornsilk)
    
    @staticmethod
    def beat8(bpm: int) -> int:
        """
        FastLED-style beat wave generator.
        
        Returns a sine wave value between 0-255 based on current time and BPM.
        Useful for creating rhythmic blinking effects.
        
        Args:
            bpm: Beats per minute (higher = faster oscillation)
        
        Returns:
            Value between 0-255 following sine wave
            
        Example:
            # Short blink every ~3 seconds (20 BPM)
            if AnimationHelpers.beat8(20) > 240:
                pixel = Pixel(255, 69, 0)  # OrangeRed blink
            else:
                pixel = Pixel(0, 0, 0)     # Off
        """
        # Convert BPM to frequency in Hz
        frequency = bpm / 60.0
        
        # Get current time in seconds
        current_time = time.time()
        
        # Calculate sine wave value (0 to 1)
        phase = 2 * math.pi * frequency * current_time
        sine_value = (math.sin(phase) + 1) / 2  # Normalize to 0-1
        
        # Scale to 0-255
        return int(sine_value * 255)
    
    @staticmethod
    def hsv_to_pixel(h: float, s: float, v: float) -> 'Pixel':
        """
        Convert HSV to Pixel RGB.
        
        Args:
            h: Hue (0-360 degrees)
            s: Saturation (0.0-1.0)
            v: Value/Brightness (0.0-1.0)
            
        Returns:
            Pixel with RGB values
        """
        
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
    
    @staticmethod
    def fade_to_black(strip: 'LedStrip', fade_amount: int) -> None:
        """
        Fade all pixels in a strip toward black using simple factor-based fading.
        
        Args:
            strip: LED strip to fade
            fade_amount: Fade strength (0-255, where 255 = fade to black completely, 0 = no fade)
        """
        from led_system.pixel import Pixel
        
        num_pixels = strip.num_pixels()
        
        # Convert fade_amount to factor (0.0 = no fade, 1.0 = fade to black completely)
        fade_factor = fade_amount / 255.0
        
        for i in range(num_pixels):
            current_pixel = strip[i]
            
            # Apply simple factor-based fading toward black
            faded_r = int(current_pixel.r * (1.0 - fade_factor))
            faded_g = int(current_pixel.g * (1.0 - fade_factor))
            faded_b = int(current_pixel.b * (1.0 - fade_factor))
            
            strip[i] = Pixel(faded_r, faded_g, faded_b)
    
    @staticmethod
    def fade_to_black_hsv(strip: 'LedStrip', fade_amount: int, min_brightness: float = 0.0) -> None:
        """
        Fade all pixels using HSV color space to preserve hue and saturation.
        
        Only reduces brightness (V component) while keeping color unchanged.
        Black pixels remain black (no unwanted lighting).
        
        Args:
            strip: LED strip to fade
            fade_amount: Fade strength (0-255, where 255 = fade significantly, 0 = no fade)
            min_brightness: Absolute minimum brightness (0.0-1.0, where 1.0 = full brightness)
        """
        from led_system.pixel import Pixel
        
        num_pixels = strip.num_pixels()
        fade_factor = fade_amount / 255.0
        
        for i in range(num_pixels):
            current_pixel = strip[i]
            
            # Skip black pixels to avoid unwanted lighting
            if current_pixel.r == 0 and current_pixel.g == 0 and current_pixel.b == 0:
                continue
            
            # Convert RGB to HSV
            h, s, v = AnimationHelpers._rgb_to_hsv(current_pixel.r, current_pixel.g, current_pixel.b)
            
            # Skip if already at or below target brightness (optimization)
            if v <= min_brightness:
                continue
            
            # Fade only the V (brightness) component with absolute minimum threshold
            new_v = max(min_brightness, v * (1.0 - fade_factor))
            
            # Convert back to RGB
            new_r, new_g, new_b = AnimationHelpers._hsv_to_rgb(h, s, new_v)
            
            strip[i] = Pixel(new_r, new_g, new_b)
    
    @staticmethod
    def _rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
        """Convert RGB (0-255) to HSV (H:0-360, S:0-1, V:0-1)"""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        diff = max_val - min_val
        
        # Value (brightness)
        v = max_val
        
        # Saturation
        s = 0 if max_val == 0 else diff / max_val
        
        # Hue
        if diff == 0:
            h = 0
        elif max_val == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif max_val == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:  # max_val == b
            h = (60 * ((r - g) / diff) + 240) % 360
            
        return h, s, v
    
    @staticmethod
    def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
        """Convert HSV (H:0-360, S:0-1, V:0-1) to RGB (0-255)"""
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r_prime, g_prime, b_prime = c, x, 0
        elif 60 <= h < 120:
            r_prime, g_prime, b_prime = x, c, 0
        elif 120 <= h < 180:
            r_prime, g_prime, b_prime = 0, c, x
        elif 180 <= h < 240:
            r_prime, g_prime, b_prime = 0, x, c
        elif 240 <= h < 300:
            r_prime, g_prime, b_prime = x, 0, c
        else:  # 300 <= h < 360
            r_prime, g_prime, b_prime = c, 0, x
        
        r = int((r_prime + m) * 255)
        g = int((g_prime + m) * 255)
        b = int((b_prime + m) * 255)
        
        return r, g, b