"""
GPIO-based button sampler implementation using RPi.GPIO
"""

import sys
from typing import List

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("⚠️  RPi.GPIO not available - this module is for Raspberry Pi only")

from .interfaces import IButtonSampler


class GPIOSampler(IButtonSampler):
    """
    Pure GPIO button sampling implementation for production.
    
    Reads raw GPIO states from configured pins.
    Follows Single Responsibility Principle - only concerned with hardware sampling.
    """
    
    def __init__(self, 
                 button_pins: List[int], 
                 pull_mode: int,
                 logger):
        """
        Initialize GPIO sampler.
        
        Args:
            button_pins: List of GPIO pin numbers (BCM mode)
            pull_mode: GPIO pull resistor mode (GPIO.PUD_OFF, GPIO.PUD_UP, GPIO.PUD_DOWN)
            logger: ClassLogger instance for logging
        """
        if 'RPi.GPIO' not in sys.modules:
            raise ImportError("RPi.GPIO is required but not available")
        
        self._button_pins = button_pins.copy()
        self._pull_mode = pull_mode
        self._logger = logger
        self._initialized = False
    
    def get_button_count(self) -> int:
        """Get number of buttons configured"""
        return len(self._button_pins)
    
    def setup(self) -> None:
        """Initialize GPIO pins for input"""
        try:
            # Set BCM mode (using GPIO pin numbers, not physical pin numbers)
            GPIO.setmode(GPIO.BCM)
            
            # Configure each button pin as input
            for pin in self._button_pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=self._pull_mode)
            
            self._initialized = True
            
            pull_mode_name = {
                GPIO.PUD_OFF: "no pulls",
                GPIO.PUD_UP: "pull-up",
                GPIO.PUD_DOWN: "pull-down"
            }.get(self._pull_mode, f"mode_{self._pull_mode}")
            
            pin_mapping = ", ".join(f"Btn{i}=GPIO{pin}" for i, pin in enumerate(self._button_pins))
            self._logger.info(f"GPIO sampler initialized: {len(self._button_pins)} pins ({pull_mode_name})")
            self._logger.info(f"Pin mapping: {pin_mapping}")
            
        except Exception as e:
            self._logger.error(f"GPIO sampler setup failed: {e}")
            raise
    
    def read_button(self, button_index: int) -> bool:
        """
        Read GPIO state of a single button.
        
        Args:
            button_index: Button number (0-based)
            
        Returns:
            True if GPIO pin is HIGH (button pressed), False otherwise
        """
        pin = self._button_pins[button_index]
        return GPIO.input(pin) == GPIO.HIGH
    
    def cleanup(self) -> None:
        """Cleanup GPIO resources"""
        try:
            if self._initialized:
                GPIO.cleanup()
                self._initialized = False
                if self._logger:
                    self._logger.info("GPIO sampler cleaned up")
        except Exception:
            pass  # Silent fail during cleanup
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self.cleanup()

