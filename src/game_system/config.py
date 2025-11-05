"""
Game system configuration
"""

from dataclasses import dataclass
from typing import List, Optional

# Import RPi.GPIO only when available (Raspberry Pi only)
try:
    import RPi.GPIO as GPIO
except ImportError:
    # Mock GPIO for non-Pi systems (development/testing)
    class _MockGPIO:
        PUD_OFF = 0
        PUD_UP = 1
        PUD_DOWN = 2
    GPIO = _MockGPIO()


@dataclass
class LedStripConfig:
    """Configuration for a single LED strip"""
    gpio_pin: int
    led_count: int
    freq_hz: int = 800000
    dma: int = 10
    invert: bool = False
    brightness: int = 26  # 0-255
    channel: int = 0


@dataclass
class ButtonConfig:
    """Button hardware configuration"""
    pins: List[int]
    pull_mode: int = GPIO.PUD_OFF
    sample_rate_hz: int = 200


@dataclass
class GameConfig:
    """Main game system configuration"""
    
    # Hardware configuration
    button_config: ButtonConfig
    led_strips: List[LedStripConfig]
    
    # Timing configuration  
    frame_duration_ms: float = 33.33  # ~30 FPS (1000ms / 30)
    
    # Sequence configuration
    sequence_timeout_ms: int = 1500
    
    # Computed properties
    @property
    def button_count(self) -> int:
        """Number of buttons based on pin configuration"""
        return len(self.button_config.pins)
    
    @property
    def strip_count(self) -> int:
        """Number of LED strips"""
        return len(self.led_strips)
    
    @property
    def total_led_count(self) -> int:
        """Total number of LEDs across all strips"""
        return sum(strip.led_count for strip in self.led_strips)
    
    @property
    def target_fps(self) -> float:
        """Target FPS derived from frame duration"""
        return 1000.0 / self.frame_duration_ms
    
    def validate(self) -> None:
        """Basic validation of configuration"""
        if not self.button_config.pins:
            raise ValueError("At least one button pin must be configured")
            
        if not self.led_strips:
            raise ValueError("At least one LED strip must be configured")
            
        if self.frame_duration_ms <= 0:
            raise ValueError("Frame duration must be positive")
            
        # Check for duplicate GPIO pins
        button_pins = set(self.button_config.pins)
        led_pins = set(strip.gpio_pin for strip in self.led_strips)
        
        if button_pins & led_pins:
            raise ValueError(f"GPIO pin conflict between buttons and LEDs: {button_pins & led_pins}")
            
        # Basic bounds checking
        for pin in self.button_config.pins:
            if not (2 <= pin <= 27):  # Valid RPi GPIO range
                raise ValueError(f"Button GPIO pin {pin} out of valid range (2-27)")
                
        for strip in self.led_strips:
            if not (2 <= strip.gpio_pin <= 27):
                raise ValueError(f"LED strip GPIO pin {strip.gpio_pin} out of valid range (2-27)")
            if strip.led_count <= 0:
                raise ValueError(f"LED count must be positive, got {strip.led_count}")
            if not (0 <= strip.brightness <= 255):
                raise ValueError(f"LED brightness must be 0-255, got {strip.brightness}")


# Default config moved to game_example.py
