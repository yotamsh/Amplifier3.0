#!/usr/bin/env python3
"""
PixelStrip Adapter - rpi_ws281x wrapper implementing LedStrip interface

Provides zero-overhead adaptation between our LedStrip interface and the
rpi_ws281x PixelStrip library. This is the only file that depends on rpi_ws281x.
"""
from typing import Union, List
from .interfaces import LedStrip
from .pixel import Pixel

# Import rpi_ws281x at module level within adapter
try:
    from rpi_ws281x import PixelStrip
except ImportError:
    # Handle gracefully for development on non-Pi systems
    PixelStrip = None


class PixelStripAdapter(LedStrip):
    """Adapter that wraps rpi_ws281x PixelStrip to implement LedStrip interface
    
    This adapter provides zero runtime overhead by leveraging the fact that
    our Pixel class IS an int, which PixelStrip can use directly.
    
    Features:
    - Zero conversion overhead (Pixel IS int)
    - Enhanced slice assignment with list support
    - Proper error handling for invalid operations
    - Graceful ImportError handling for development
    """
    
    def __init__(self, led_count: int, gpio_pin: int, freq_hz: int = 800000, 
                 dma: int = 10, invert: bool = False, brightness: int = 255, 
                 channel: int = 0) -> None:
        """Initialize PixelStrip with all standard parameters
        
        Args:
            led_count: Number of LEDs in the strip
            gpio_pin: GPIO pin connected to strip data line (must be PWM pin)
            freq_hz: Signal frequency in hertz (default 800kHz)
            dma: DMA channel to use (default 10)
            invert: Whether to invert the signal (default False)
            brightness: Global brightness 0-255 (default 255)
            channel: PWM channel to use (default 0)
            
        Raises:
            ImportError: If rpi_ws281x is not available
            RuntimeError: If PixelStrip initialization fails
        """
        if PixelStrip is None:
            raise ImportError("rpi_ws281x not available - run on Raspberry Pi")
            
        self._strip = PixelStrip(led_count, gpio_pin, freq_hz, dma, 
                               invert, brightness, channel)
        self._strip.begin()
    
    def __getitem__(self, pos: Union[int, slice]) -> Union[Pixel, List[Pixel]]:
        """Get pixel color(s) with proper type conversion
        
        Args:
            pos: Single position or slice
            
        Returns:
            Single Pixel for int position, List[Pixel] for slice
        """
        result = self._strip[pos]
        if isinstance(pos, slice):
            # Convert List[int] to List[Pixel]
            return [Pixel(color) for color in result]
        else:
            # Convert int to Pixel
            return Pixel(result)
    
    def __setitem__(self, pos: Union[int, slice], color: Union[Pixel, List[Pixel]]) -> None:
        """Set pixel(s) with enhanced slice assignment and validation
        
        Args:
            pos: Single position or slice
            color: Single Pixel or List[Pixel]
            
        Raises:
            TypeError: If trying to assign list to single position
            ValueError: If color list length doesn't match slice length
        """
        if isinstance(pos, slice):
            if isinstance(color, list):
                # ✅ SUPPORTED: strip[0:3] = [pixel1, pixel2, pixel3]
                indices = range(*pos.indices(self._strip.size))
                if len(color) != len(indices):
                    raise ValueError(f"Color list length ({len(color)}) must match slice length ({len(indices)})")
                
                # Direct assignment - Pixel IS int, so zero overhead
                for i, pixel in zip(indices, color):
                    self._strip[i] = pixel
            else:
                # ✅ SUPPORTED: strip[0:10] = pixel (same color for all)
                self._strip[pos] = color
        else:
            # Single position
            if isinstance(color, list):
                # ❌ NOT SUPPORTED: strip[5] = [pixel1, pixel2] (invalid)
                raise TypeError("Cannot assign list of colors to single position")
            else:
                # ✅ SUPPORTED: strip[5] = pixel
                self._strip[pos] = color
    
    def show(self) -> None:
        """Update the physical display with current buffer
        
        Delegates directly to PixelStrip.show() which renders the LED data.
        This operation typically takes ~10ms per strip to complete.
        """
        self._strip.show()
    
    def num_pixels(self) -> int:
        """Return number of pixels in the strip
        
        Returns:
            Total number of controllable pixels
        """
        return self._strip.numPixels()
