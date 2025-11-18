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
        AnimationHelpers.fade_to_black_hsv(self.strip, fade_amount=60, min_brightness=0.0)
        
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


class AmplifyPyramidAnimation(Animation):
    """
    Pyramid fill animation based on number of pressed buttons.
    
    Fills the pyramid from bottom to top proportionally to the number
    of pressed buttons. Uses PyramidMapping for height-based control.
    """
    
    def __init__(self, strip: 'LedStrip', button_count: int, speed_ms: int = 50):
        """
        Initialize pyramid amplify animation.
        
        Args:
            strip: LED strip to operate on (pyramid strip)
            button_count: Total number of buttons in the system
            speed_ms: Animation update interval in milliseconds
        """
        super().__init__(strip, speed_ms)
        self.button_count: int = button_count
        
        # Track which buttons are currently pressed
        self.pressed_buttons: List[bool] = [False] * button_count
        
        # Fill color - white
        from led_system.pixel import Pixel
        self.fill_color = Pixel(255, 255, 255)
        self.off_color = Pixel(0, 0, 0)
    
    def set_pressed_buttons(self, pressed_buttons: List[bool]) -> None:
        """
        Update which buttons are currently pressed.
        
        Args:
            pressed_buttons: List of boolean values indicating button press state
        """
        self.pressed_buttons = pressed_buttons.copy()
    
    def advance(self) -> None:
        """Update pyramid LEDs based on number of pressed buttons"""
        from game_system.animation_helpers import pyramidHeight
        
        # Count how many buttons are pressed
        buttons_pressed = sum(self.pressed_buttons)
        
        # Calculate fill percentage: (buttons_pressed / total_buttons) * 100
        fill_percent = int((buttons_pressed / self.button_count) * 100)
        
        # Get LEDs to light (from bottom to fill_percent height)
        leds_to_light = pyramidHeight[0:fill_percent]
        
        # Clear entire strip first
        num_pixels = self.strip.num_pixels()
        for i in range(num_pixels):
            self.strip[i] = self.off_color
        
        # Light the bottom portion
        for led_idx in leds_to_light:
            self.strip[led_idx] = self.fill_color


class PartyPyramidAnimation(Animation):
    """
    Party pyramid animation - whole pyramid blinks on/off with vibrant colors.
    
    Alternates between lit (with color) and dark every 400ms.
    Starts with white, then uses vibrant, pleasant colors.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = 50):
        """
        Initialize party pyramid animation.
        
        Args:
            strip: LED strip to operate on (pyramid strip)
            speed_ms: Animation update interval (checks for blink timing)
        """
        super().__init__(strip, speed_ms)
        
        # Blinking state
        from led_system.pixel import Pixel
        self.current_color = Pixel(255, 255, 255)  # Start with white
        self.is_lit = True  # Start lit
        self.is_first_blink = True
        self.blink_interval_ms = 400  # 400ms per on/off toggle
        self.last_blink_time = time.time()
        self.black = Pixel(0, 0, 0)
    
    def _get_random_pastel_color(self) -> 'Pixel':
        """Generate a random vibrant, pleasant color"""
        from led_system.pixel import Pixel
        
        # Vibrant but pleasant color palette
        colors = [
            Pixel(255, 105, 180),  # Hot pink
            Pixel(100, 149, 237),  # Cornflower blue
            Pixel(144, 238, 144),  # Light green
            Pixel(255, 165, 0),    # Orange
            Pixel(186, 85, 211),   # Medium orchid
            Pixel(255, 215, 0),    # Gold
            Pixel(64, 224, 208),   # Turquoise
            Pixel(255, 20, 147),   # Deep pink
            Pixel(30, 144, 255),   # Dodger blue
            Pixel(255, 99, 71),    # Tomato red
            Pixel(147, 112, 219),  # Medium purple
            Pixel(50, 205, 50),    # Lime green
        ]
        return random.choice(colors)
    
    def advance(self) -> None:
        """Toggle pyramid on/off every 400ms, changing color when turning on"""
        current_time = time.time()
        elapsed_ms = (current_time - self.last_blink_time) * 1000
        
        # Check if it's time to toggle
        if elapsed_ms >= self.blink_interval_ms:
            self.is_lit = not self.is_lit
            
            # When turning on, pick a new color
            if self.is_lit:
                if self.is_first_blink:
                    # First time stays white
                    self.is_first_blink = False
                else:
                    # After first blink, use pastel colors
                    self.current_color = self._get_random_pastel_color()
            
            self.last_blink_time = current_time
        
        # Fill pyramid with current state (lit color or black)
        num_pixels = self.strip.num_pixels()
        display_color = self.current_color if self.is_lit else self.black
        
        for i in range(num_pixels):
            self.strip[i] = display_color


class PartyAnimation(Animation):
    """
    Elegant pushing wave party animation.
    
    Creates color bands that appear in the center and push outward symmetrically.
    New colors enter at the center, pushing previous colors toward the edges.
    Like a wave emanating from the center.
    """
    
    def __init__(self, strip: 'LedStrip', speed_ms: int = None, button_count: int = None):
        """
        Initialize party pushing wave animation.
        
        Args:
            strip: LED strip to operate on
            speed_ms: Animation update interval in milliseconds (random if None)
            button_count: Number of buttons for reduction feature (optional)
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
        
        # Color palette (initialized immediately)
        self.colors = [
            AnimationHelpers.RED_WINE,
            AnimationHelpers.GREEN_GRASS,
            AnimationHelpers.PURPLE,
            AnimationHelpers.SOFT_WHITE
        ]
        
        # Wave state: track position with fixed band width for smooth animation
        self.wave_position: int = 0  # How far the wave has traveled from center
        self.band_width: int = 25  # Fixed width for consistent, smooth bands
        self.speed_change_interval: int = self.band_width * len(self.colors)  # Change speed after full color cycle
        
        # Reduction red override state
        self.button_count = button_count
        self.leds_per_button = strip.num_pixels() // button_count if button_count else 0
        self.button_A = None
        self.button_B = None
        self.a_red_pixels = 0  # Additional spread pixels (not including segment)
        self.b_red_pixels = 0  # Additional spread pixels (not including segment)
        self.button_A_held = False
        self.button_B_held = False
    
    def advance(self) -> None:
        """
        Stateless wave effect - calculates each pixel's color independently
        based on distance from center and current wave position.
        This prevents the animation from interfering with red override pixels.
        Uses fixed band_width for smooth, jump-free animation.
        """
        # Advance wave position
        self.wave_position += 1
        
        # Optionally vary speed after full color cycle (smooth transitions)
        if self.wave_position % self.speed_change_interval == 0:
            self.speed_ms = random.randint(10, 20)
        
        # Calculate color for each pixel based on distance from center
        for i in range(self.num_pixels):
            # Calculate distance from center
            if self.is_even:
                # Distance from nearest center
                dist = min(abs(i - self.center1), abs(i - self.center2))
            else:
                dist = abs(i - self.center2)
            
            # Determine which color band this pixel is in
            # Subtract wave_position to create outward movement effect
            band_position = (dist - self.wave_position) // self.band_width
            
            # Use modulo to cycle through colors, handle negative with abs
            color_idx = abs(band_position) % len(self.colors)
            self.strip[i] = self.colors[color_idx]
        
        # Apply red override on top (after generating base animation)
        self._apply_red_override()
    
    def set_red_override(self, button_A: int, button_B: int, 
                         a_red_pixels: int, b_red_pixels: int,
                         button_A_held: bool, button_B_held: bool) -> None:
        """
        Set red override information for reduction feature.
        
        Args:
            button_A: Index of button A (right center)
            button_B: Index of button B (left center)
            a_red_pixels: Number of additional spread pixels from A (not including segment)
            b_red_pixels: Number of additional spread pixels from B (not including segment)
            button_A_held: Whether button A is currently held
            button_B_held: Whether button B is currently held
        """
        self.button_A = button_A
        self.button_B = button_B
        self.a_red_pixels = a_red_pixels
        self.b_red_pixels = b_red_pixels
        self.button_A_held = button_A_held
        self.button_B_held = button_B_held
    
    def _apply_red_override(self) -> None:
        """Apply red color override for reduction feature"""
        if not self.button_A_held and not self.button_B_held:
            return  # No buttons held, no override needed
        
        from led_system.pixel import Pixel
        red = Pixel(255, 0, 0)
        
        # Button A held: segment + spread right
        if self.button_A_held:
            # Segment always red when held
            segment_start = self.button_A * self.leds_per_button
            segment_end = (self.button_A + 1) * self.leds_per_button
            self.strip[segment_start:segment_end] = red
            
            # Additional spread pixels beyond segment
            if self.a_red_pixels > 0:
                spread_start = segment_end
                spread_end = spread_start + self.a_red_pixels
                self.strip[spread_start:spread_end] = red
        
        # Button B held: segment + spread left
        if self.button_B_held:
            # Segment always red when held
            segment_start = self.button_B * self.leds_per_button
            segment_end = (self.button_B + 1) * self.leds_per_button
            self.strip[segment_start:segment_end] = red
            
            # Additional spread pixels before segment
            if self.b_red_pixels > 0:
                spread_end = segment_start
                spread_start = max(0, spread_end - self.b_red_pixels)
                self.strip[spread_start:spread_end] = red


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
