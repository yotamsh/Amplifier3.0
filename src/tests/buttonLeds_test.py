#!/usr/bin/env python3
"""
Button + LED Combined Test - Button Reading with LED Keyboard Control

Combines real-time button edge detection with immediate LED keyboard control:
- Button system: 5ms sampling, full logging, edge detection
- LED control: Non-blocking keyboard input ('1'=ON, '0'=OFF, 'q'=quit)
- Terminal: Full cbreak mode for immediate response
- Hardware: GPIO22 (button) + GPIO26 (LED) - no conflicts

Features:
- 200Hz button sampling with press/release detection
- Immediate LED control via keyboard
- Comprehensive logging for both button and LED actions
- Robust terminal cleanup on any exit condition
"""
import sys
import time
import select
import termios
import tty
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from button_system import ButtonReader
    from hybridLogger import HybridLogger
    import RPi.GPIO as GPIO
    import logging
    from rpi_ws281x import PixelStrip, Color
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with rpi_ws281x installed")
    sys.exit(1)

# Configuration
BUTTON_PINS = [
    22,  # Single button for this test - avoiding all conflicts
]

# LED Configuration 
LED_GPIO = 26  # GPIO26 (Physical pin 37) - no conflicts with button or other systems

# LED Strip Configuration
LED_COUNT = 300         # Number of LEDs per strip
LED_BRIGHTNESS = 26     # 0-255 (10% brightness for testing)
LED_FREQ_HZ = 800000    # 800kHz signal frequency

# Strip 1: Rainbow cycle - GPIO18 (PWM channel 0)
LED_STRIP1_GPIO = 18
LED_STRIP1_DMA = 10  
LED_STRIP1_CHANNEL = 0

# Strip 2: Color wipe - GPIO21 (channel 0) - GPIO21 doesn't use PWM
LED_STRIP2_GPIO = 21
LED_STRIP2_DMA = 5
LED_STRIP2_CHANNEL = 0

class Animation:
    """Base non-blocking animation with time-based updates"""
    
    def __init__(self, strip, speed_ms, logger, name="Animation"):
        self.strip = strip
        self.speed_ms = speed_ms  # How often to advance (milliseconds)
        self.last_update = time.time()
        self.logger = logger
        self.name = name
        
    def update(self):
        """Called every loop - advances only when enough time has passed"""
        now = time.time()
        elapsed_ms = (now - self.last_update) * 1000
        
        if elapsed_ms >= self.speed_ms:
            # Check for significant lag
            if elapsed_ms > self.speed_ms * 2:
                self.logger.warning(f"{self.name} lagging: {elapsed_ms:.1f}ms vs {self.speed_ms}ms target")
            
            self.advance()  # Subclass implements this
            self.strip.show()  # ~10ms blocking call per strip
            self.last_update = now
            return True
        return False
    
    def advance(self):
        """Override in subclasses - change strip colors"""
        pass
    
    def hsv_to_color(self, h, s, v):
        """Convert HSV to rpi_ws281x Color"""
        h = h % 360  # Wrap hue
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:  # 300 <= h < 360
            r, g, b = c, 0, x
        
        r = int((r + m) * 255)
        g = int((g + m) * 255)
        b = int((b + m) * 255)
        
        return Color(r, g, b)

class RainbowCycleAnimation(Animation):
    """Continuously cycling rainbow animation"""
    
    def __init__(self, strip, speed_ms=50, logger=None):
        super().__init__(strip, speed_ms, logger, "RainbowCycle")
        self.hue_offset = 0
    
    def jump(self):
        """Jump the rainbow hue by 255 degrees for dramatic color shift"""
        self.hue_offset = (self.hue_offset + 255) % 360
        # No logging here - button handler will log the action
        
    def advance(self):
        """Update rainbow pattern with offset"""
        for i in range(self.strip.numPixels()):
            # Calculate hue based on position and offset
            hue = (i * 360 / self.strip.numPixels() + self.hue_offset) % 360
            color = self.hsv_to_color(hue, 1.0, 1.0)  # Full saturation and brightness
            self.strip.setPixelColor(i, color)
        
        # Advance the rainbow offset with bigger steps for more dynamic motion
        self.hue_offset = (self.hue_offset + 8) % 360  # 8 degrees per frame for faster color cycling

class ColorWipeAnimation(Animation):
    """Green wipe → Red wipe → repeat animation"""
    
    def __init__(self, strip, speed_ms=20, logger=None):
        super().__init__(strip, speed_ms, logger, "ColorWipe")
        self.position = 0
        self.color_sets = [
            [Color(0, 255, 0), Color(255, 0, 0)],      # Green, Red (default)
            [Color(255, 128, 0), Color(0, 255, 255)]   # Orange, Cyan (jumped)
        ]
        self.current_color_set = 0  # Index into color_sets
        self.colors = self.color_sets[self.current_color_set]
        self.color_index = 0
    
    def jump(self):
        """Jump to alternate color set: Green/Red ↔ Orange/Cyan"""
        self.current_color_set = (self.current_color_set + 1) % len(self.color_sets)
        self.colors = self.color_sets[self.current_color_set]
        
        # Keep current animation state (position and color_index) - just change colors
        # No reset - animation continues seamlessly with new color set
        
        color_names = ["Green/Red", "Orange/Cyan"]
        current_name = color_names[self.current_color_set]
        
        # No logging here - button handler will log the action
        
    def advance(self):
        """Update wipe pattern - simple color-to-color wipe, no black clearing"""
        current_color = self.colors[self.color_index]
        
        # Set current position to current color
        self.strip.setPixelColor(self.position, current_color)
        
        self.position += 1
        
        if self.position >= self.strip.numPixels():
            # Wipe complete - switch to next color and restart from position 0
            self.color_index = (self.color_index + 1) % len(self.colors)
            self.position = 0

class ButtonLedsTestRunner:
    """Combined button reading, LED control, and LED strip animation test runner"""
    
    def __init__(self):
        self.running = True
        self.button_reader = None
        self.loop_count = 0
        self.button_click_counts = [0] * len(BUTTON_PINS)
        # Periodic status removed as requested
        self.last_loop_time = time.time()    # Track time for loop rate limiting
        
        # LED control state
        self.led_state = False  # False = OFF, True = ON
        
        # LED strips
        self.strip1 = None  # Rainbow animation
        self.strip2 = None  # Color wipe animation
        
        # Terminal management
        self.old_terminal_settings = None
        
        print(f"🔲 Setting up combined test: {len(BUTTON_PINS)} button(s) + LED control + 2 LED strips...")
        
    def setup_terminal(self, logger=None):
        """Set terminal to cbreak mode for immediate keyboard input"""
        try:
            self.old_terminal_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            # Only log, don't print + log
        except Exception as e:
            if logger:
                logger.error(f"Terminal setup failed: {e}", exception=e)
    
    def restore_terminal(self):
        """Restore original terminal settings"""
        try:
            if self.old_terminal_settings:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_terminal_settings)
        except Exception:
            pass  # Silent fail during cleanup
    
    def setup_led_control(self, logger):
        """Initialize LED GPIO for output control"""
        try:
            GPIO.setup(LED_GPIO, GPIO.OUT, initial=GPIO.LOW)  # Start with LED OFF
            logger.info(f"LED initialized on GPIO{LED_GPIO} (OFF)")
            return True
        except Exception as e:
            logger.error(f"LED setup failed on GPIO{LED_GPIO}: {e}", exception=e)
            return False
    
    def setup_led_strips(self, logger):
        """Initialize both LED strips"""
        try:
            # Strip 1: Rainbow animation (GPIO18, PWM channel 0)
            self.strip1 = PixelStrip(
                LED_COUNT, LED_STRIP1_GPIO, LED_FREQ_HZ, LED_STRIP1_DMA,
                False, LED_BRIGHTNESS, LED_STRIP1_CHANNEL
            )
            self.strip1.begin()
            logger.info(f"Strip 1 initialized: GPIO{LED_STRIP1_GPIO}, PWM channel {LED_STRIP1_CHANNEL}")
            
            # Strip 2: Color wipe animation (GPIO21, channel 0) - GPIO21 doesn't use PWM
            self.strip2 = PixelStrip(
                LED_COUNT, LED_STRIP2_GPIO, LED_FREQ_HZ, LED_STRIP2_DMA,
                False, LED_BRIGHTNESS, LED_STRIP2_CHANNEL
            )
            self.strip2.begin()
            logger.info(f"Strip 2 initialized: GPIO{LED_STRIP2_GPIO}, PWM channel {LED_STRIP2_CHANNEL}")
            
            # Clear both strips initially
            for i in range(LED_COUNT):
                self.strip1.setPixelColor(i, Color(0, 0, 0))
                self.strip2.setPixelColor(i, Color(0, 0, 0))
            self.strip1.show()
            self.strip2.show()
            
            logger.info(f"LED strips ready: {LED_COUNT} LEDs each, GPIO{LED_STRIP1_GPIO}+GPIO{LED_STRIP2_GPIO}")
            return True
            
        except Exception as e:
            logger.error(f"LED strip setup failed: {e}", exception=e)
            return False
    
    def setup_button_reader(self, logger):
        """Initialize button reader with selected GPIO"""
        try:
            self.button_reader = ButtonReader(
                button_pins=BUTTON_PINS,
                logger=logger,
                pull_mode=GPIO.PUD_OFF  # External circuits
            )
            
            logger.info("Button reader initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Button reader setup failed: {e}", exception=e)
            return False
    
    def check_keyboard_input(self):
        """Non-blocking keyboard input check - returns key or None"""
        try:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1).lower()
        except Exception:
            pass
        return None
    
    def set_led(self, state, logger):
        """Control LED state with logging"""
        try:
            if state:
                GPIO.output(LED_GPIO, GPIO.HIGH)  # 3.3V - LED ON
                self.led_state = True
                print("🟢 LED ON  (3.3V)")
                logger.info(f"LED turned ON (GPIO{LED_GPIO}) - keyboard command '1'")
            else:
                GPIO.output(LED_GPIO, GPIO.LOW)   # GND - LED OFF
                self.led_state = False
                print("🔴 LED OFF (GND)")
                logger.info(f"LED turned OFF (GPIO{LED_GPIO}) - keyboard command '0'")
        except Exception as e:
            logger.error(f"LED control failed: {e}", exception=e)
    
    def process_keyboard_input(self, key, logger):
        """Process keyboard commands with full logging"""
        if key == '1':
            if not self.led_state:
                self.set_led(True, logger)
            else:
                print("💡 LED is already ON")
                logger.info("LED already ON - ignored keyboard command '1'")
                
        elif key == '0':
            if self.led_state:
                self.set_led(False, logger)
            else:
                print("💡 LED is already OFF")
                logger.info("LED already OFF - ignored keyboard command '0'")
                
        elif key == 'q':
            print("👋 Quit requested via keyboard...")
            logger.info("Test termination requested - keyboard command 'q'")
            self.running = False
            
        elif key == '\x03':  # Ctrl+C character
            logger.info("Test interrupted - Ctrl+C detected")
            raise KeyboardInterrupt
            
        else:
            # Log unknown keys for debugging but don't spam console
            if ord(key) >= 32 and ord(key) <= 126:  # Printable characters only
                logger.debug(f"Unknown keyboard command: '{key}'")
    
    def print_hardware_setup(self):
        """Display hardware connection requirements"""
        print("📍 Hardware Mapping:")
        for idx, pin in enumerate(BUTTON_PINS):
            print(f"   Button {idx}      → GPIO {pin:2d}")
        print(f"   LED control   → GPIO {LED_GPIO:2d}")
        print(f"   LED Strip 1   → GPIO {LED_STRIP1_GPIO:2d} (Rainbow cycle)")
        print(f"   LED Strip 2   → GPIO {LED_STRIP2_GPIO:2d} (Color wipe)")
        print()
    
    def run_combined_loop(self, logger):
        """Main combined loop: button reading + LED keyboard control + LED strip animations"""
        print("🎮 COMBINED BUTTON + LED + STRIP ANIMATION TEST")
        print("=" * 60)
        print("Hardware Setup:")
        print("• Button: SPDT with RC circuit → GPIO22")
        print("• LED control: GPIO26 → LED positive + Ground")
        print("• LED Strip 1: GPIO18 → Rainbow cycle animation (300 LEDs)")
        print("• LED Strip 2: GPIO21 → Green/Red wipe animation (300 LEDs)")
        print()
        
        self.print_hardware_setup()
        
        print("📊 Controls & Features:")
        print("  • Buttons: Real-time press/release detection (200Hz max, CPU efficient)")
        print("  • Button 0 PRESS: Rainbow strip jumps (hue +255°)")
        print("  • Button 0 RELEASE: Wipe strip jumps (Green/Red ↔ Orange/Cyan)")
        print("  • LED: Keyboard control - '1'=ON, '0'=OFF, 'q'=quit")
        print("  • Strip 1: Dynamic rainbow cycle (20 FPS, faster color flow)")
        print("  • Strip 2: Direct color wipe cycle (50 FPS, no black phase)")
        print("  • Logging: All button events and LED actions")
        print("  • Terminal: Immediate input (no Enter key needed)")
        print()
        print("⏱️  Starting combined test...")
        print("⌨️  Ready for keyboard input: 1, 0, q")
        print()
        print("Event Log:")
        print("-" * 30)
        
        # Create animations
        rainbow_anim = RainbowCycleAnimation(self.strip1, speed_ms=50, logger=logger)  # 20 FPS
        wipe_anim = ColorWipeAnimation(self.strip2, speed_ms=20, logger=logger)        # 50 FPS
        
        try:
            # Setup terminal for immediate input
            self.setup_terminal(logger)
            
            while self.running:
                # Button reading (existing logic)
                state = self.button_reader.read_buttons()
                
                # Log button changes immediately and handle animation jumps
                if state.any_changed:
                    self.log_button_changes(state, logger, rainbow_anim, wipe_anim)
                
                # Check for keyboard input (non-blocking)
                key = self.check_keyboard_input()
                if key:
                    self.process_keyboard_input(key, logger)
                
                # Update LED strip animations (non-blocking, time-based)
                rainbow_updated = rainbow_anim.update()  # Updates only if 50ms+ elapsed
                wipe_updated = wipe_anim.update()        # Updates only if 20ms+ elapsed
                
                # Periodic status deleted as requested
                
                self.loop_count += 1
                
                # Ensure loop doesn't run faster than 200Hz (5ms minimum interval)
                current_time = time.time()
                elapsed_ms = (current_time - self.last_loop_time) * 1000
                min_interval_ms = 5.0  # 5ms = 200Hz maximum
                
                if elapsed_ms < min_interval_ms:
                    sleep_time = (min_interval_ms - elapsed_ms) / 1000.0
                    time.sleep(sleep_time)
                
                self.last_loop_time = time.time()
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Test stopped by user (Ctrl+C)")
            logger.info(f"Test completed after {self.loop_count} loops")
        except Exception as e:
            logger.error(f"Test error: {e}", exception=e)
        finally:
            # Clear LED strips before exit
            try:
                for i in range(LED_COUNT):
                    self.strip1.setPixelColor(i, Color(0, 0, 0))
                    self.strip2.setPixelColor(i, Color(0, 0, 0))
                self.strip1.show()
                self.strip2.show()
                logger.info("LED strips cleared")
            except Exception:
                pass
            
            # Critical cleanup
            self.restore_terminal()
            logger.info("Combined test completed - GPIO, strips, and terminal will be cleaned up automatically")
    
    def log_button_changes(self, state, logger, rainbow_anim=None, wipe_anim=None):
        """Log individual button press/release events and handle animation jumps"""
        for button_idx in range(state.get_button_count()):
            if state.was_changed[button_idx]:
                gpio_pin = BUTTON_PINS[button_idx]
                current_state = state.for_button[button_idx]
                
                if current_state:
                    action = "PRESSED"
                    self.button_click_counts[button_idx] += 1
                    click_count = self.button_click_counts[button_idx]
                    logger.info(f"Button {button_idx} {action.lower()} (GPIO {gpio_pin}) - Click #{click_count}")
                    
                    # Button 0 press: jump rainbow animation (strip 1)
                    if button_idx == 0 and rainbow_anim:
                        rainbow_anim.jump()
                        logger.info("Button 0 PRESSED - Rainbow animation jumped!")
                        
                else:
                    action = "RELEASED"
                    click_count = self.button_click_counts[button_idx]
                    logger.info(f"Button {button_idx} {action.lower()} (GPIO {gpio_pin}) - Total clicks: {click_count}")
                    
                    # Button 0 release: jump wipe animation (strip 2)
                    if button_idx == 0 and wipe_anim:
                        wipe_anim.jump()
                        logger.info("Button 0 RELEASED - Color wipe animation jumped!")
    
    # Periodic status logging removed as requested
    
    def cleanup(self):
        """Optional manual cleanup for advanced users"""
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Internal cleanup - LED + LED strips + GPIO + terminal"""
        try:
            # Turn off LED
            GPIO.output(LED_GPIO, GPIO.LOW)
            
            # Clear LED strips
            if self.strip1:
                for i in range(LED_COUNT):
                    self.strip1.setPixelColor(i, Color(0, 0, 0))
                    self.strip2.setPixelColor(i, Color(0, 0, 0))
                self.strip1.show()
                self.strip2.show()
            
            # Restore terminal
            self.restore_terminal()
            
            # Don't call GPIO.cleanup() here - automatic cleanup in ButtonReader handles it
            
            # Don't print, only log cleanup completion
        except Exception:
            pass  # Silent fail during destruction
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self._cleanup_resources()

def main():
    """Main function with comprehensive setup"""
    print("🎮 COMBINED BUTTON + LED + STRIP ANIMATION SYSTEM TEST")
    print("=" * 70)
    print("Hardware Requirements:")
    print("• 1 SPDT button with RC circuit (100nF + 330Ω)")
    print("• 1 LED with appropriate current limiting")
    print("• 2 WS2812B LED strips (300 LEDs each)")
    print("• External 5V power supply (6A+ recommended)")
    print()
    print("Connection Guide:")
    print(f"  Button      → GPIO{BUTTON_PINS[0]:2d} (Physical pin 15)")  
    print(f"  LED control → GPIO{LED_GPIO:2d} (Physical pin 37)")
    print(f"  LED Strip 1 → GPIO{LED_STRIP1_GPIO:2d} (Physical pin 12) - Rainbow animation")
    print(f"  LED Strip 2 → GPIO{LED_STRIP2_GPIO:2d} (Physical pin 40) - Color wipe animation")
    print("  LED - & Strips GND → Pi Ground + External PSU Ground")
    print("  Button → Common to GPIO, NC to GND, NO to 3.3V")
    print()
    print("Power & Safety:")
    print("  • LED strips: Connect to external 5V supply (NOT Pi 5V)")
    print("  • Ground: Connect Pi GND to external PSU GND")
    print("  • Data: Pi GPIO → LED strip data input (3.3V signal)")
    print()
    print("Performance:")
    print("  • Button sampling: ~50Hz (excellent responsiveness)")
    print("  • Rainbow animation: 20 FPS (smooth color cycling)")
    print("  • Wipe animation: 50 FPS (smooth pixel progression)")
    print()
    
    # User confirmation - immediate input mode
    print("📍 Hardware setup complete? Press ANY KEY to start...")
    print("   (No Enter key needed - immediate response mode)")
    
    # Wait for any key to start
    try:
        old_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        sys.stdin.read(1)  # Any key starts
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
    except Exception:
        input()  # Fallback to regular input
    
    print()
    
    # Initialize logging system
    main_logger = HybridLogger("ButtonLedsTest")
    
    # Class-specific loggers with appropriate levels
    test_logger = main_logger.get_class_logger("ButtonLedsTestRunner", logging.DEBUG)
    gpio_logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
    
    test_logger.info("Combined button + LED + strip animation test starting")
    test_logger.info(f"Configuration: {len(BUTTON_PINS)} button(s), 1 LED, 2 strips (300 LEDs each), ~50Hz sampling")
    
    # Run the test
    test_runner = ButtonLedsTestRunner()
    
    # Setup all systems
    button_setup = test_runner.setup_button_reader(gpio_logger)
    led_setup = test_runner.setup_led_control(test_logger)
    strip_setup = test_runner.setup_led_strips(test_logger)
    
    if button_setup and led_setup and strip_setup:
        test_runner.run_combined_loop(test_logger)
    else:
        print("❌ Failed to initialize one or more systems")
        test_logger.error("Test aborted due to setup failure")
    
    # Cleanup
    main_logger.cleanup()

# Import shared utilities
from gpio_utils import gpio_to_physical

if __name__ == "__main__":
    main()
