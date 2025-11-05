"""
Helper utilities for animations
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from led_system.pixel import Pixel


class AnimationHelpers:
    """Static helper methods for animations"""
    
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
