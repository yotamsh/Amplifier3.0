#!/usr/bin/env python3
"""
Pixel class - Library independent color representation

Provides a zero-overhead color class that extends int, allowing direct usage
with LED strip libraries while providing convenient RGB property access.
"""
from typing import Union


class Pixel(int):
    """Custom color class that packs RGB into integer - zero overhead
    
    This class extends int, so it can be used directly with LED strip libraries
    that expect integer color values, while providing convenient RGB properties.
    
    Usage:
        pixel = Pixel(255, 0, 0)        # Red pixel
        pixel = Pixel(0xFF0000)         # Red pixel from int
        print(pixel.r, pixel.g, pixel.b)  # Access RGB components
        strip[0] = pixel                # Direct assignment (zero overhead)
    """
    
    def __new__(cls, r: int, g: int = None, b: int = None) -> 'Pixel':
        """Create pixel from RGB values or existing int
        
        Args:
            r: Red component (0-255) OR packed color integer
            g: Green component (0-255) OR None if r is packed color
            b: Blue component (0-255) OR None if r is packed color
            
        Returns:
            Pixel object that IS an int (zero overhead)
            
        Examples:
            Pixel(255, 0, 0)     # Red pixel
            Pixel(0xFF0000)      # Red pixel from packed int
            Pixel(strip[0])      # Create from strip color value
        """
        if g is None and b is None:
            # Single int value passed (from PixelStrip or raw color)
            return int.__new__(cls, r)
        elif g is None or b is None:
            # Invalid - if providing RGB, must provide all three
            raise ValueError("Must provide either just int value or all three RGB values")
        else:
            # Clamp RGB values to valid range and pack into 24-bit integer
            r_clamped = r & 0xFF  # Ensure 0-255 range
            g_clamped = g & 0xFF  # Ensure 0-255 range  
            b_clamped = b & 0xFF  # Ensure 0-255 range
            return int.__new__(cls, (r_clamped << 16) | (g_clamped << 8) | b_clamped)
    
    @property
    def r(self) -> int:
        """Red component (0-255)"""
        return (self >> 16) & 0xFF
    
    @property
    def g(self) -> int:
        """Green component (0-255)"""
        return (self >> 8) & 0xFF
    
    @property
    def b(self) -> int:
        """Blue component (0-255)"""
        return self & 0xFF
    
    def __repr__(self) -> str:
        return f"Pixel(r={self.r}, g={self.g}, b={self.b})"
    
    def __str__(self) -> str:
        return f"Pixel({self.r}, {self.g}, {self.b})"
