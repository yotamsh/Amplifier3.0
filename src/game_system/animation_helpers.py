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

# Initialize color constants at module load time
from led_system.pixel import Pixel

class AnimationHelpers:
    """Static helper methods for animations"""
    
    # Basic color constants (initialized at class definition)
    ORANGE_RED = Pixel(255, 69, 0)
    BLACK = Pixel(0, 0, 0)
    WHITE = Pixel(255, 255, 255)
    GREEN = Pixel(0, 255, 0)  # Pure green
    
    # Party mode color palette
    RED_WINE = Pixel(139, 0, 45)        # Deep red wine
    GREEN_GRASS = Pixel(34, 139, 34)    # Vibrant grass green
    PURPLE = Pixel(138, 43, 226)        # Rich purple (blue-violet)
    SOFT_WHITE = Pixel(255, 248, 220)   # Soft warm white (cornsilk)
    

    
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


class PyramidMapping:
    """
    Static mapping for A-shaped pyramid LED strip (Strip 1, GPIO 18).
    
    LED flow: LEFT_UP (bottom→top) → TOP_RIGHT → RIGHT_DOWN (top→bottom) → MIDDLE_LEFT
    
    Height buckets: 0-100 (101 total)
      - Bucket 0: Empty (nothing lit)
      - Buckets 1-99: Sides + middle bar (vertically distributed)
      - Bucket 100: Top line only
    
    Usage:
        # Get bottom 50%
        leds = pyramidHeight[0:50]
        
        # Get top line only
        leds = pyramidHeight[100:100]
        
        # Get sides and middle (no top line)
        leds = pyramidHeight[1:99]
    """
    
    # ============ MEASURED VALUES ============
    LEFT_SIDE_COUNT = 116     # Bottom→top (LED 0=bottom/bucket1, 115=top/bucket99)
    TOP_LINE_COUNT = 16       # Top line (all in bucket 100)
    RIGHT_SIDE_COUNT = 116    # Top→bottom (LED 0=top/bucket99, 115=bottom/bucket1)
    MIDDLE_LINE_COUNT = 46    # Middle bar
    MIDDLE_ALIGN_LED = 48     # Aligned with left side LED 48
    
    # Calculate middle bar height: LED 48 from bottom = (48/115) * 98 + 1 ≈ 42
    MIDDLE_BAR_HEIGHT = round((MIDDLE_ALIGN_LED / (LEFT_SIDE_COUNT - 1)) * 98) + 1
    
    # ============ SEGMENT BOUNDARIES ============
    LEFT_START = 0
    LEFT_END = LEFT_SIDE_COUNT                      # 0-115
    
    TOP_START = LEFT_END
    TOP_END = TOP_START + TOP_LINE_COUNT            # 116-131
    
    RIGHT_START = TOP_END
    RIGHT_END = RIGHT_START + RIGHT_SIDE_COUNT      # 132-247
    
    MIDDLE_START = RIGHT_END
    MIDDLE_END = MIDDLE_START + MIDDLE_LINE_COUNT   # 248-293
    
    # ============ HEIGHT BUCKETS (0-100) ============
    _HEIGHT_BUCKETS = [[] for _ in range(101)]
    
    @classmethod
    def _build_buckets(cls):
        """Build height buckets - called once at module load"""
        
        # Bucket 0 stays empty
        
        # Left side: LED 0 (bottom) → bucket 1, LED 115 (top) → bucket 99
        for i in range(cls.LEFT_SIDE_COUNT):
            height_bucket = round((i / (cls.LEFT_SIDE_COUNT - 1)) * 98) + 1
            cls._HEIGHT_BUCKETS[height_bucket].append(cls.LEFT_START + i)
        
        # Top line: all in bucket 100
        for i in range(cls.TOP_LINE_COUNT):
            cls._HEIGHT_BUCKETS[100].append(cls.TOP_START + i)
        
        # Right side: LED 0 (top) → bucket 99, LED 115 (bottom) → bucket 1
        for i in range(cls.RIGHT_SIDE_COUNT):
            height_bucket = round((1 - i / (cls.RIGHT_SIDE_COUNT - 1)) * 98) + 1
            cls._HEIGHT_BUCKETS[height_bucket].append(cls.RIGHT_START + i)
        
        # Middle bar at calculated height (~42%)
        for i in range(cls.MIDDLE_LINE_COUNT):
            cls._HEIGHT_BUCKETS[cls.MIDDLE_BAR_HEIGHT].append(cls.MIDDLE_START + i)
    
    @classmethod
    def get_height_range(cls, start_percent: int, end_percent: int) -> set[int]:
        """
        Get all LED indices in height range [start, end] INCLUSIVE.
        
        Args:
            start_percent: Bottom of range (0-100)
            end_percent: Top of range (0-100, inclusive)
            
        Returns:
            Set of LED indices in this range
        """
        result = set()
        for h in range(start_percent, end_percent + 1):
            result.update(cls._HEIGHT_BUCKETS[h])
        return result
    
    @classmethod
    def get_bottom_percent(cls, percent: int) -> set[int]:
        """Get LEDs in bottom X% of pyramid"""
        return cls.get_height_range(0, percent)
    
    @classmethod
    def get_top_percent(cls, percent: int) -> set[int]:
        """Get LEDs in top X% of pyramid"""
        return cls.get_height_range(100 - percent, 100)


class _PyramidHeightSliceHelper:
    """
    Helper class to enable slice syntax: pyramidHeight[start:end]
    
    Uses INCLUSIVE slicing on both ends (unlike standard Python slices).
    
    Examples:
        pyramidHeight[0:50]    # Buckets 0-50 (bottom half)
        pyramidHeight[100:100] # Bucket 100 only (top line)
        pyramidHeight[1:99]    # Buckets 1-99 (sides+middle, no top line)
        pyramidHeight[25]      # Bucket 25 only (single height)
    """
    
    def __getitem__(self, key) -> set[int]:
        if isinstance(key, slice):
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else 100
            
            # Clamp to valid range
            start = max(0, min(100, start))
            stop = max(0, min(100, stop))
            
            # INCLUSIVE on both ends (unlike standard Python slicing)
            if stop < start:
                return set()
            
            return PyramidMapping.get_height_range(start, stop)
        
        elif isinstance(key, int):
            # Single bucket access
            if not (0 <= key <= 100):
                raise IndexError(f"Pyramid height index {key} out of range (0-100)")
            return set(PyramidMapping._HEIGHT_BUCKETS[key])
        
        else:
            raise TypeError(f"Pyramid height indices must be integers or slices, not {type(key).__name__}")


# Global instance for slice syntax
pyramidHeight = _PyramidHeightSliceHelper()

# Build buckets at module load time (runs once)
PyramidMapping._build_buckets()