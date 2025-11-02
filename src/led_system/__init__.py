#!/usr/bin/env python3
"""
LED System - Library independent LED strip control

This package provides a clean, library-independent abstraction for controlling
LED strips. The main components are:

- Pixel: Zero-overhead color class that extends int
- LedStrip: Abstract interface for LED strip control
- PixelStripAdapter: rpi_ws281x implementation of LedStrip

Usage:
    from led_system import LedStrip, PixelStripAdapter, Pixel
    
    # Create strip adapter
    strip = PixelStripAdapter(led_count=300, gpio_pin=18)
    
    # Use clean interface
    strip[0] = Pixel(255, 0, 0)         # Red pixel
    strip[1:5] = Pixel(0, 255, 0)       # Green pixels
    strip[5:8] = [Pixel(255,0,0), Pixel(0,255,0), Pixel(0,0,255)]
    strip.show()
    
    # Access color components
    color = strip[0]
    print(f"RGB: {color.r}, {color.g}, {color.b}")
"""

from .pixel import Pixel
from .interfaces import LedStrip
from .pixel_strip_adapter import PixelStripAdapter

__all__ = ['Pixel', 'LedStrip', 'PixelStripAdapter']

__version__ = '1.0.0'
__author__ = 'LED System'
__description__ = 'Library independent LED strip control abstraction'
