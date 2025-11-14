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
        Initialize idle scanner animation with random starting position and hue.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds
            hue_increment: Amount to increment hue each frame (higher = faster color change)
            fade_amount: Fade strength (0-255, where 255 = fade to target completely, 0 = no fade)
        """
        super().__init__(strip, speed_ms)
        
        # Strip length
        self.num_pixels: int = strip.num_pixels()
        
        # Scanner position and movement - ALWAYS start from random position
        self.led_index: int = random.randint(0, self.num_pixels - 1)
        self.reverse: bool = random.choice([True, False])  # Random initial direction
        
        # Color cycling - ALWAYS start from random hue
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
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 100, 
                 hue_shift_per_frame: int = 10):
        """
        Initialize amplify animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons that control segments
            speed_ms: Animation update interval in milliseconds (higher = slower)
            hue_shift_per_frame: Degrees to shift hue each frame (higher = faster)
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.hue_shift_per_frame: int = hue_shift_per_frame
        self.hue_offset: int = 0
        self.hue_spread: float = 6.7  # Higher value = more color variation between pixels (1/3 more dense)
        
        # Calculate LEDs per button (constant for this animation instance)
        self.leds_per_button: int = strip.num_pixels() // button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        
    
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
                # Calculate rainbow hue with higher spread between pixels
                hue = (led_pos * self.hue_spread + self.hue_offset) % 360
                color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
                self.strip[led_pos] = color
            # Note: No explicit "else" - let fading handle unpressed segments
        
        # 3. Add blinking OrangeRed indicators on unpressed button centers
        # Using beat8-style blinking: on when beat > 240 (short blink every ~1.5 seconds)
        beat_value = AnimationHelpers.beat8(40)  # 40 BPM = blink every 1.5 seconds (double speed)
        
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
    Elegant pushing wave party animation.
    
    Creates color bands that appear in the center and push outward symmetrically.
    New colors enter at the center, pushing previous colors toward the edges.
    Like a wave emanating from the center.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = None):
        """
        Initialize party pushing wave animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds (random if None)
        """
        # Pick random speed if not provided (faster range)
        if speed_ms is None:
            speed_ms = random.randint(10, 20)
        
        super().__init__(strip, speed_ms)
        self.num_pixels: int = strip.num_pixels()
        
        # Determine center position(s)
        # For even pixel count, we have two centers
        self.center1: int = self.num_pixels // 2 - 1
        self.center2: int = self.num_pixels // 2
        self.is_even: bool = (self.num_pixels % 2 == 0)
        
        # Color palette
        self.color_palette = []  # Will be initialized in advance()
        self.color_index: int = 0  # Track current color in sequence
        
        # Current band state
        self.current_color = None
        self.current_band_length: int = 0
        self.current_band_speed: int = speed_ms  # Track current speed
        self.leds_in_current_band: int = 0
    
    def advance(self) -> None:
        """Pushing wave effect - new colors push from center outward"""
        # Initialize color palette (only once)
        if not self.color_palette:
            self.color_palette = [
                AnimationHelpers.RED_WINE,
                AnimationHelpers.GREEN_GRASS,
                AnimationHelpers.PURPLE,
                AnimationHelpers.SOFT_WHITE
            ]
            # Pick first color in sequence, random length and speed
            self.current_color = self.color_palette[self.color_index]
            self.current_band_length = random.randint(15, 35)
            self.current_band_speed = random.randint(10, 20)  # Faster: 10-20ms
            self.speed_ms = self.current_band_speed
            self.leds_in_current_band = 0
        
        # Shift all pixels outward from center using efficient slice notation
        if self.is_even:
            # Even pixel count: two centers at center1 and center2
            # Left side: shift left (positions 0 to center1-1)
            if self.center1 > 0:
                self.strip[:self.center1] = self.strip[1:self.center1+1]
            
            # Right side: shift right (positions center2+1 to end)
            if self.center2 < self.num_pixels - 1:
                self.strip[self.center2+1:] = self.strip[self.center2:-1]
            
            # Add current color at both center positions
            self.strip[self.center1] = self.current_color
            self.strip[self.center2] = self.current_color
            
        else:
            # Odd pixel count: single center at center2
            # Left side: shift left (positions 0 to center2-1)
            if self.center2 > 0:
                self.strip[:self.center2] = self.strip[1:self.center2+1]
            
            # Right side: shift right (positions center2+1 to end)
            if self.center2 < self.num_pixels - 1:
                self.strip[self.center2+1:] = self.strip[self.center2:-1]
            
            # Add current color at center
            self.strip[self.center2] = self.current_color
        
        # Count LEDs added for this color
        self.leds_in_current_band += 1
        
        # Check if we've added enough LEDs for this color band
        if self.leds_in_current_band >= self.current_band_length:
            # Move to next color in sequence
            self.color_index = (self.color_index + 1) % len(self.color_palette)
            self.current_color = self.color_palette[self.color_index]
            
            # Pick random length and speed for next band
            self.current_band_length = random.randint(15, 35)
            self.current_band_speed = random.randint(10, 20)  # Faster: 10-20ms
            self.speed_ms = self.current_band_speed  # Update animation speed
            self.leds_in_current_band = 0


class CodeModeAnimation(Animation):
    """
    Animation for code input mode - shows pure green light on button segments 
    whose digits appear in the current sequence.
    
    All other segments are black.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50):
        """
        Initialize code mode animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons (for segment calculation)
            speed_ms: Animation update interval
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        self.leds_per_button: int = strip.num_pixels() // button_count
        self.active_digits: set = set()  # Button indices currently in sequence
    
    def set_active_digits(self, sequence: str) -> None:
        """
        Update which button digits should be lit based on sequence.
        
        Args:
            sequence: Current sequence string (e.g., "314")
        """
        # Convert sequence chars to digit set
        self.active_digits = set()
        for char in sequence:
            if char.isdigit():
                self.active_digits.add(int(char))
    
    def advance(self) -> None:
        """Update strip - pure green for active digits, black for others"""
        from led_system.pixel import Pixel
        
        green = Pixel(0, 255, 0)  # Pure green
        black = Pixel(0, 0, 0)
        
        num_pixels = self.strip.num_pixels()
        
        for led_pos in range(num_pixels):
            # Calculate which button segment this LED belongs to
            button_index = led_pos // self.leds_per_button
            
            # Light up if this button's digit is in the sequence
            if button_index < self.button_count and button_index in self.active_digits:
                self.strip[led_pos] = green
            else:
                self.strip[led_pos] = black


class CodeRevealAnimation(Animation):
    """
    Animation for code reveal - progressively lights up code digits, then blinks them.
    
    Phases:
    1. Fill phase: Light up each digit segment one by one (fill_speed_ms interval)
    2. Blink phase: Blink all revealed digits (blink_speed_ms interval)
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, code_sequence: str,
                 fill_speed_ms: int = 200, blink_speed_ms: int = 400):
        """
        Initialize code reveal animation.
        
        Args:
            strip: LED strip to operate on
            button_count: Number of buttons (for segment calculation)
            code_sequence: The code to reveal (e.g., "314")
            fill_speed_ms: Milliseconds between revealing each digit
            blink_speed_ms: Milliseconds for blink cycle
        """
        super().__init__(strip, fill_speed_ms)
        
        # Pre-calculate constants
        self.button_count: int = button_count
        self.num_pixels: int = strip.num_pixels()
        self.leds_per_button: int = self.num_pixels // button_count
        self.fill_speed_ms: int = fill_speed_ms
        self.blink_speed_ms: int = blink_speed_ms
        
        # Parse code sequence into list of digit integers
        self.code_digits: List[int] = [int(char) for char in code_sequence]
        
        # Animation state
        self.revealed_count: int = 0  # How many digits have been revealed
        self.is_filling: bool = True  # True during fill phase, False during blink
        self.blink_state: bool = True  # True = on, False = off
        
        # Clear strip once on init
        self.strip[:] = AnimationHelpers.BLACK
    
    def start_blinking(self) -> None:
        """Transition from fill phase to blink phase"""
        self.is_filling = False
        self.speed_ms = self.blink_speed_ms
        self.last_update = time.time()  # Reset timing for blink
    
    def is_fill_complete(self) -> bool:
        """Check if all digits have been revealed"""
        return self.revealed_count >= len(self.code_digits)
    
    def advance(self) -> None:
        """Update animation - fill or blink based on current phase"""
        if self.is_filling:
            # Fill phase: reveal one more digit
            if not self.is_fill_complete():
                digit = self.code_digits[self.revealed_count]
                start_idx = digit * self.leds_per_button
                end_idx = (digit + 1) * self.leds_per_button
                self.strip[start_idx:end_idx] = AnimationHelpers.GREEN
                self.revealed_count += 1
        else:
            # Blink phase: toggle all code digit segments
            self.blink_state = not self.blink_state
            color = AnimationHelpers.GREEN if self.blink_state else AnimationHelpers.BLACK
            
            # Update all code digit segments using slices
            for digit in self.code_digits:
                start_idx = digit * self.leds_per_button
                end_idx = (digit + 1) * self.leds_per_button
                self.strip[start_idx:end_idx] = color
