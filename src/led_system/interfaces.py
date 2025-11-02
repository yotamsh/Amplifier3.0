#!/usr/bin/env python3
"""
LED Strip Interface - Abstract base class for LED strip control

Defines the contract for LED strip implementations, supporting Python slice
notation and providing a clean, library-independent API.
"""
from abc import ABC, abstractmethod
from typing import Union, List
from .pixel import Pixel


class LedStrip(ABC):
    """Abstract interface for LED strip control using Python slice notation
    
    This interface provides a clean, library-independent API for controlling
    LED strips. Implementations can wrap different LED libraries while providing
    a consistent interface.
    
    Supported Operations:
        strip[5] = Pixel(255, 0, 0)                    # Single pixel
        strip[0:10] = Pixel(0, 255, 0)                 # Slice to same color
        strip[0:3] = [pixel1, pixel2, pixel3]          # Slice to different colors
        strip[:] = Pixel(0, 0, 0)                      # Clear all
        
        color = strip[5]                               # Get single pixel
        colors = strip[0:10]                           # Get slice of pixels
    
    Invalid Operations:
        strip[5] = [pixel1, pixel2]                    # Position + list (TypeError)
    """
    
    @abstractmethod
    def __getitem__(self, pos: Union[int, slice]) -> Union[Pixel, List[Pixel]]:
        """Get pixel color(s). Returns single Pixel or list for slice.
        
        Args:
            pos: Single position (int) or slice object
            
        Returns:
            Single Pixel for int position, List[Pixel] for slice
            
        Examples:
            color = strip[5]        # Get single pixel
            colors = strip[0:10]    # Get slice of pixels
        """
        pass
    
    @abstractmethod  
    def __setitem__(self, pos: Union[int, slice], color: Union[Pixel, List[Pixel]]) -> None:
        """Set pixel(s) to color(s). Supports multiple assignment patterns.
        
        Args:
            pos: Single position (int) or slice object
            color: Single Pixel or List[Pixel] (must match slice length)
            
        Raises:
            TypeError: If trying to assign list to single position
            ValueError: If color list length doesn't match slice length
            
        Supported Patterns:
            strip[5] = Pixel(255, 0, 0)                    # Single position
            strip[0:10] = Pixel(255, 0, 0)                 # Slice to same color
            strip[0:3] = [Pixel(255,0,0), Pixel(0,255,0)]  # Slice to different colors
            
        Invalid Patterns:
            strip[5] = [pixel1, pixel2]                    # Position + list
        """
        pass
    
    @abstractmethod
    def show(self) -> None:
        """Update the physical display with current buffer.
        
        This method must be called after setting pixel colors to make
        the changes visible on the actual LED strip hardware.
        """
        pass
    
    @abstractmethod
    def num_pixels(self) -> int:
        """Return number of pixels in the strip.
        
        Returns:
            Total number of controllable pixels in the strip
        """
        pass
