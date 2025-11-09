"""
Animation base class and concrete implementations for the game system
"""

import math
import random
import time
from abc import ABC, abstractmethod
from typing import List, Tuple, TYPE_CHECKING

from game_system.animation_helpers import AnimationHelpers

if TYPE_CHECKING:
    from led_system.interfaces import LedStrip
    from led_system.pixel import Pixel


class Animation(ABC):
    """
    Abstract base class for time-based animations.
    
    Provides non-blocking, time-based animation updates with configurable speed.
    Each animation operates on a single LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int):
        """
        Initialize animation with timing control.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Update interval in milliseconds
        """
        self.strip: 'LedStrip' = strip
        self.speed_ms: int = speed_ms
        self.last_update: float = time.time()
    
    def get_name(self) -> str:
        """Get animation name from class name"""
        return self.__class__.__name__
    
    def update_if_needed(self) -> bool:
        """
        Update animation if enough time has passed.
        
        Returns:
            True if animation was updated, False if skipped
        """
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            self.advance()
            self.strip.show()
            self.last_update = now
            return True
        return False
    
    @abstractmethod
    def advance(self) -> None:
        """
        Advance animation by one frame (override in subclasses).
        
        Should update the strip's pixel data but not call show().
        """
        pass


class RainbowAnimation(Animation):
    """
    Continuous rainbow cycle animation.
    
    Creates a flowing rainbow pattern across the entire LED strip
    with configurable speed and hue shifting.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50, hue_shift_per_frame: int = 8):
        """
        Initialize rainbow animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds  
            hue_shift_per_frame: Degrees to shift hue each frame
        """
        super().__init__(strip, speed_ms)
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Update all strip pixels
        num_pixels = self.strip.num_pixels()
        
        for i in range(num_pixels):
            # Calculate hue based on position and offset
            hue = (i * 360 / num_pixels + self.hue_offset) % 360
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
            self.strip[i] = color


class BreathingAnimation(Animation):
    """
    Smooth breathing/pulsing animation with configurable color and brightness range.
    
    Uses sine wave for natural breathing effect across the entire LED strip.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel', speed_ms: int = 100, 
                 brightness_range: Tuple[float, float] = (0.1, 1.0)):
        """
        Initialize breathing animation.
        
        Args:
            strip: LED strip to operate on
            color: Base color to pulse
            speed_ms: Animation update interval
            brightness_range: (min_brightness, max_brightness) tuple
        """
        super().__init__(strip, speed_ms)
        self.base_color: 'Pixel' = color
        self.brightness_range: Tuple[float, float] = brightness_range
        self.phase: float = 0.0
        self.phase_speed: float = 0.1  # Phase increment per frame (adjust for breathing speed)
    
    def advance(self) -> None:
        """Advance breathing phase and update strip pixels"""
        self.phase += self.phase_speed
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        
        # Calculate current brightness using sine wave
        min_brightness, max_brightness = self.brightness_range
        brightness_range = max_brightness - min_brightness
        current_brightness = min_brightness + brightness_range * (0.5 + 0.5 * math.sin(self.phase))
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # Create dimmed color
        dimmed_color = Pixel(
            int(self.base_color.r * current_brightness),
            int(self.base_color.g * current_brightness),
            int(self.base_color.b * current_brightness)
        )
        
        # Update entire strip
        self.strip[:] = dimmed_color


class StaticColorAnimation(Animation):
    """
    Simple static color animation for testing and simple effects.
    """
    
    def __init__(self, strip: 'LedStrip', color: 'Pixel'):
        """
        Initialize static color animation.
        
        Args:
            strip: LED strip to operate on
            color: Color to display
        """
        super().__init__(strip, 1000)  # Slow update since it's static
        self.color: 'Pixel' = color
        self._initialized: bool = False
    
    def advance(self) -> None:
        """Set static color once, then no changes needed"""
        if not self._initialized:
            # Update entire strip once
            self.strip[:] = self.color
            self._initialized = True


class IdleAnimation(Animation):
    """
    Dynamic bouncing rainbow scanner animation for idle state.
    
    Creates a single bright LED that bounces back and forth across the strip,
    cycling through rainbow hues with a fading trail effect behind it.
    Based on the classic "Cylon eye" or "scanner" effect.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50, hue_increment: int = 3, fade_amount: int = 40):
        """
        Initialize idle scanner animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
            hue_increment: Amount to increment hue each frame (higher = faster color change)
            fade_amount: Fade strength (0-255, where 255 = fade to target completely, 0 = no fade)
        """
        super().__init__(strip, speed_ms)
        
        # Strip length
        self.num_pixels: int = strip.num_pixels()
        
        # Scanner position and movement - start from random position
        self.led_index: int = random.randint(0, self.num_pixels - 1)
        self.reverse: bool = random.choice([True, False])  # Random initial direction
        
        # Color cycling - start from random hue
        self.hue_index: int = random.randint(0, 359)
        self.hue_increment: int = hue_increment
        
        # Fading effect
        self.fade_amount: int = fade_amount
    
    def advance(self) -> None:
        """Advance scanner position, update colors, and apply fading effect"""
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # 1. Fade all existing pixels using HSV to preserve color (trail effect)
        AnimationHelpers.fade_to_black_hsv(self.strip, self.fade_amount)
        
        # 2. Set current LED to bright rainbow color
        current_color = AnimationHelpers.hsv_to_pixel(self.hue_index % 360, 1.0, 1.0)
        self.strip[self.led_index] = current_color
        
        # 3. Move LED index (bouncing motion)
        if self.reverse:
            self.led_index -= 1
        else:
            self.led_index += 1
        
        # 4. Reverse direction at strip ends
        if self.led_index >= self.num_pixels - 1 or self.led_index <= 0:
            self.reverse = not self.reverse
            # Ensure we stay within bounds
            self.led_index = max(0, min(self.led_index, self.num_pixels - 1))
        
        # 5. Increment hue for next frame (rainbow cycling)
        self.hue_index += self.hue_increment


class AnimationDelayWrapper(Animation):
    """
    Generic wrapper that adds a delay before starting a target animation.
    
    During the delay period, keeps the LED strip black. After the delay,
    delegates all animation behavior to the wrapped target animation.
    """
    
    def __init__(self, target_animation: 'Animation', delay_ms: int):
        """
        Initialize delay wrapper.
        
        Args:
            target_animation: Animation to run after delay
            delay_ms: Delay duration in milliseconds before starting target animation
        """
        super().__init__(target_animation.strip, target_animation.speed_ms)
        self.target_animation: 'Animation' = target_animation
        self.delay_ms: int = delay_ms
        self.start_time: float = time.time() * 1000  # Current time in milliseconds
        self.delay_finished: bool = False
    
    def advance(self) -> None:
        """Either maintain black strip during delay or delegate to target animation"""
        if not self.delay_finished:
            # Check if delay period is over
            current_time = time.time() * 1000
            if current_time - self.start_time >= self.delay_ms:
                self.delay_finished = True
                # Delay finished, start delegating to target animation
                self.target_animation.advance()
            else:
                # Still in delay - keep strip black
                # Import here to avoid circular imports
                from led_system.pixel import Pixel
                black = Pixel(0, 0, 0)
                self.strip[:] = black
        else:
            # Delay finished - delegate to target animation
            self.target_animation.advance()


class AmplifyAnimation(Animation):
    """
    Rainbow animation that only illuminates LED segments corresponding to pressed buttons.
    
    Each button controls a segment of the LED strip. Only pressed button segments
    show the rainbow pattern, while unpressed segments have a blinking OrangeRed indicator.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50, 
                 hue_shift_per_frame: int = 18):
        """
        Initialize amplify animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons that control segments
            speed_ms: Animation update interval in milliseconds
            hue_shift_per_frame: Degrees to shift hue each frame (higher = faster)
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
        
        # Calculate LEDs per button (constant for this animation instance)
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        
        # Initialize color constants
        AnimationHelpers._init_colors()
    
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """
        Update which buttons are currently pressed.
        
        Args:
            pressed_buttons: List of boolean values indicating button press state
        """
        self.pressed_buttons = pressed_buttons.copy()
    
    def _get_button_center_pixel(self, button_index: int) -> int:
        """
        Get the center pixel index for a button segment.
        
        Formula: totalLeds/buttonsCount*(button_index+0.5)-1
        
        Args:
            button_index: Index of the button (0-based)
            
        Returns:
            Center pixel index for that button's segment
        """
        num_pixels = self.strip.num_pixels()
        center = int(num_pixels / self.button_count * (button_index + 0.5) - 1)
        return max(0, min(center, num_pixels - 1))  # Clamp to valid range
    
    def advance(self) -> None:
        """Advance rainbow hue offset and update strip pixels based button state"""
        self.hue_offset = (self.hue_offset + self.hue_shift_per_frame) % 360
        
        # Import here to avoid circular imports
        from led_system.pixel import Pixel
        
        # 1. First, apply HSV fading to create trails for released button segments
        AnimationHelpers.fade_to_black_hsv(self.strip, fade_amount=30, min_brightness=0.0)
        
        # 2. Update all strip pixels based on current button state
        num_pixels = self.strip.num_pixels()
        
        for led_pos in range(num_pixels):
            # Calculate which button segment this LED belongs to
            button_index = led_pos // self.leds_per_button
            
            # Check if this button is pressed (with bounds checking)
            if button_index < self.button_count and self.pressed_buttons[button_index]:
                # Calculate rainbow hue based on LED position and offset
                hue = (led_pos * 360 / num_pixels + self.hue_offset) % 360
                color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                self.strip[led_pos] = color
            # Note: No explicit "else" - let fading handle unpressed segments
        
        # 3. Add blinking OrangeRed indicators on unpressed button centers
        # Using beat8-style blinking: on when beat > 240 (short blink every ~3 seconds)
        beat_value = AnimationHelpers.beat8(20)  # 20 BPM = blink every 3 seconds
        
        for button_index in range(self.button_count):
            if not self.pressed_buttons[button_index]:
                center_pixel = self._get_button_center_pixel(button_index)
                if beat_value > 240:
                    # Blink on - show OrangeRed
                    self.strip[center_pixel] = AnimationHelpers.ORANGE_RED
                else:
                    # Blink off - force to black (override fade)
                    self.strip[center_pixel] = AnimationHelpers.BLACK


class PartyAnimation(Animation):
    """
    Energetic party animation with multiple simultaneous effects.
    
    Combines:
    - Fast rainbow wave traveling across strip
    - Random sparkles/glitter overlay
    - Brightness pulsing
    - Color zones that shift (creates sections of different colors)
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 20):
        """
        Initialize party animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Rainbow wave parameters
        self.hue_offset: int = 0
        self.wave_speed: int = 15  # Degrees per frame
        
        # Sparkle parameters
        self.sparkle_probability: float = 0.12  # 12% chance per LED per frame
        self.sparkle_positions: set = set()
        
        # Pulse parameters
        self.pulse_phase: float = 0.0
        self.pulse_speed: float = 0.25
        
        # Color zone parameters (creates shifting color sections)
        self.zone_hue: int = 0
        self.zone_shift_speed: int = 5
        self.zone_size: int = 30  # LEDs per zone
    
    def advance(self) -> None:
        """Energetic party effect with multiple layers"""
        # Initialize color constants if needed
        AnimationHelpers._init_colors()
        
        # 1. Base layer: Fast traveling rainbow wave
        self.hue_offset = (self.hue_offset + self.wave_speed) % 360
        
        for i in range(self.num_pixels):
            # Calculate base rainbow hue with wave effect
            position_factor = i / self.num_pixels
            hue = (position_factor * 360 + self.hue_offset) % 360
            
            # 2. Color zones - create alternating color sections that shift
            # This creates visible "bands" of different colors moving along the strip
            zone_index = (i // self.zone_size) % 3  # 3 different zones
            if zone_index == 0:
                hue = (hue + self.zone_hue) % 360
            elif zone_index == 1:
                hue = (hue + self.zone_hue + 120) % 360  # 120° offset = complementary
            else:
                hue = (hue + self.zone_hue + 240) % 360  # 240° offset = triad
            
            # 3. Pulsing brightness (0.6 to 1.0)
            brightness = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(self.pulse_phase + position_factor * 2 * math.pi))
            
            # Convert to pixel
            color = AnimationHelpers.hsv_to_pixel(hue, 1.0, brightness)
            self.strip[i] = color
        
        # 4. Add random sparkles (white flashes)
        # Clear old sparkles
        self.sparkle_positions.clear()
        
        # Create new sparkles
        for i in range(self.num_pixels):
            if random.random() < self.sparkle_probability:
                self.sparkle_positions.add(i)
                self.strip[i] = AnimationHelpers.WHITE  # Bright white
        
        # Update animation parameters for next frame
        self.pulse_phase = (self.pulse_phase + self.pulse_speed) % (2 * math.pi)
        self.zone_hue = (self.zone_hue + self.zone_shift_speed) % 360
