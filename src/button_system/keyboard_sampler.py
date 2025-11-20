"""
Pure keyboard sampler for testing without GPIO hardware
"""

import sys
import select
from typing import List

from .interfaces import IButtonSampler


class KeyboardSampler(IButtonSampler):
    """
    Pure keyboard toggle sampler for testing without GPIO.
    
    Simulates button input using keyboard digit keys 0-9 as toggles.
    Works over SSH using stdin (non-blocking select).
    Each keypress toggles that button's state on/off.
    
    Uses the same approach as GPIOWithKeyboardSampler but without GPIO.
    Does NOT use raw terminal mode - works with normal terminal settings.
    
    Perfect for:
    - Testing on development machines without GPIO hardware
    - Remote debugging over SSH
    - Development on macOS/Linux without Raspberry Pi
    
    Example:
        sampler = KeyboardSampler(
            num_buttons=10,
            logger=logger
        )
        # Now pressing '0' toggles button 0, '1' toggles button 1, etc.
    """
    
    def __init__(self, 
                 num_buttons: int,
                 logger):
        """
        Initialize keyboard sampler.
        
        Args:
            num_buttons: Number of virtual buttons (max 10 for digit keys 0-9)
            logger: ClassLogger instance for logging
        """
        if num_buttons > 10:
            raise ValueError("KeyboardSampler supports max 10 buttons (digit keys 0-9)")
        
        self._button_count = num_buttons
        self._logger = logger
        self._keyboard_toggles: List[bool] = [False] * num_buttons
        
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
        """Initialize keyboard input"""
        # Log keyboard debug mode
        if self._stdin_available:
            self._logger.info("🎮 Keyboard sampler initialized (NO GPIO)")
            self._logger.info(f"   {self._button_count} virtual buttons mapped to digit keys 0-{self._button_count-1}")
            self._logger.info("   Press digit keys to toggle buttons ON/OFF")
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
        Read button state from keyboard toggle.
        
        Checks for keyboard input on each read (non-blocking).
        
        Args:
            button_index: Button number (0-based)
            
        Returns:
            True if button toggle is ON, False if OFF
        """
        # Check for new keyboard input (updates toggles)
        self._check_keyboard_input()
        
        # Return keyboard toggle state
        return self._keyboard_toggles[button_index]
    
    def cleanup(self) -> None:
        """Cleanup keyboard resources"""
        try:
            # Reset keyboard toggles
            self._keyboard_toggles = [False] * self._button_count
            
            if self._logger:
                self._logger.info("Keyboard sampler cleaned up")
        except Exception:
            pass  # Silent fail during cleanup
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self.cleanup()
