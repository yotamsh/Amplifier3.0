"""
GPIO + Keyboard sampler for debugging over SSH
"""

import sys
import select
from typing import List, Set

from .interfaces import IButtonSampler
from .gpio_sampler import GPIOSampler


class GPIOWithKeyboardSampler(IButtonSampler):
    """
    GPIO + Keyboard toggle sampler for debugging.
    
    Combines GPIO input with keyboard toggles (works over SSH):
    - Reads GPIO state from GPIOSampler
    - Reads keyboard digit keys 0-9 as toggles (press once=ON, press again=OFF)
    - Returns OR of both states
    
    Keyboard works over SSH using stdin (non-blocking select).
    Each keypress toggles that button's state on/off.
    
    Example:
        sampler = GPIOWithKeyboardSampler(
            button_pins=[22, 23, 24],
            pull_mode=GPIO.PUD_OFF,
            logger=logger
        )
        # Now pressing '0' toggles button 0, '1' toggles button 1, etc.
    """
    
    def __init__(self, 
                 button_pins: List[int],
                 pull_mode: int,
                 logger):
        """
        Initialize GPIO+Keyboard sampler.
        
        Args:
            button_pins: List of GPIO pin numbers (BCM mode)
            pull_mode: GPIO pull resistor mode
            logger: ClassLogger instance for logging
        """
        self._gpio_sampler = GPIOSampler(button_pins, pull_mode, logger)
        self._logger = logger
        self._keyboard_toggles: List[bool] = [False] * len(button_pins)
        self._button_count = len(button_pins)
        
        # Track if stdin is available for keyboard input
        self._stdin_available = self._check_stdin_available()
    
    def _check_stdin_available(self) -> bool:
        """Check if stdin is available for keyboard input"""
        try:
            # Test if stdin is accessible
            select.select([sys.stdin], [], [], 0)
            return True
        except Exception:
            return False
    
    def get_button_count(self) -> int:
        """Get number of buttons configured"""
        return self._button_count
    
    def setup(self) -> None:
        """Initialize GPIO and keyboard input"""
        # Setup GPIO via delegate
        self._gpio_sampler.setup()
        
        # Log keyboard debug mode
        if self._stdin_available:
            self._logger.info("🎮 Keyboard debug enabled: Press digit keys 0-9 to toggle buttons (works over SSH)")
            self._logger.info("   Each keypress toggles button ON/OFF")
        else:
            self._logger.warning("Keyboard input not available (stdin not accessible)")
    
    def _check_keyboard_input(self) -> None:
        """
        Check for keyboard input and toggle button states.
        Non-blocking check using select (works over SSH).
        """
        if not self._stdin_available:
            return
        
        try:
            # Non-blocking check for stdin input
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                
                # Check if it's a digit key
                if key.isdigit():
                    button_index = int(key)
                    
                    # Only toggle if this button exists
                    if button_index < self._button_count:
                        # Toggle the button state
                        self._keyboard_toggles[button_index] = not self._keyboard_toggles[button_index]
                        
                        state_name = "ON" if self._keyboard_toggles[button_index] else "OFF"
                        self._logger.info(f"Keyboard: Button {button_index} toggled {state_name} (key '{key}')")
        except Exception:
            pass  # Silent fail - don't interrupt main loop
    
    def read_button(self, button_index: int) -> bool:
        """
        Read button state: GPIO OR keyboard toggle.
        
        Checks for keyboard input on each read (non-blocking).
        
        Args:
            button_index: Button number (0-based)
            
        Returns:
            True if button pressed via GPIO OR keyboard toggle is ON
        """
        # Check for new keyboard input (updates toggles)
        self._check_keyboard_input()
        
        # Read GPIO state
        gpio_pressed = self._gpio_sampler.read_button(button_index)
        
        # Read keyboard toggle state
        keyboard_pressed = self._keyboard_toggles[button_index]
        
        # Return OR - either GPIO or keyboard activates the button
        return gpio_pressed or keyboard_pressed
    
    def cleanup(self) -> None:
        """Cleanup GPIO and keyboard resources"""
        try:
            # Cleanup GPIO
            self._gpio_sampler.cleanup()
            
            # Reset keyboard toggles
            self._keyboard_toggles = [False] * self._button_count
            
            if self._logger:
                self._logger.info("GPIO+Keyboard sampler cleaned up")
        except Exception:
            pass  # Silent fail during cleanup
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self.cleanup()


