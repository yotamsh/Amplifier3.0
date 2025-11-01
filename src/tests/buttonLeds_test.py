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
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi")
    sys.exit(1)

# Configuration
BUTTON_PINS = [
    22,  # Single button for this test - avoiding all conflicts
]

# LED Configuration 
LED_GPIO = 26  # GPIO26 (Physical pin 37) - no conflicts with button or other systems

# Timing
SAMPLE_INTERVAL = 0.005  # 5ms = 200Hz sampling rate

class ButtonLedsTestRunner:
    """Combined button reading and LED control test runner"""
    
    def __init__(self):
        self.running = True
        self.button_reader = None
        self.loop_count = 0
        self.button_click_counts = [0] * len(BUTTON_PINS)
        
        # LED control state
        self.led_state = False  # False = OFF, True = ON
        
        # Terminal management
        self.old_terminal_settings = None
        
        print(f"🔲 Setting up combined test: {len(BUTTON_PINS)} button(s) + LED control...")
        
    def setup_terminal(self):
        """Set terminal to cbreak mode for immediate keyboard input"""
        try:
            self.old_terminal_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            print("✅ Terminal set to cbreak mode (immediate input)")
        except Exception as e:
            print(f"⚠️  Terminal setup warning: {e}")
    
    def restore_terminal(self):
        """Restore original terminal settings"""
        try:
            if self.old_terminal_settings:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.old_terminal_settings)
                print("✅ Terminal settings restored")
        except Exception:
            pass  # Silent fail during cleanup
    
    def setup_led_control(self, logger):
        """Initialize LED GPIO for output control"""
        try:
            GPIO.setup(LED_GPIO, GPIO.OUT, initial=GPIO.LOW)  # Start with LED OFF
            logger.info(f"LED initialized on GPIO{LED_GPIO} (OFF)")
            print(f"✅ LED configured on GPIO{LED_GPIO} (output mode)")
            return True
        except Exception as e:
            logger.error(f"LED setup failed on GPIO{LED_GPIO}: {e}")
            print(f"❌ LED setup failed: {e}")
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
            logger.error(f"Button reader setup failed: {e}")
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
            logger.error(f"LED control failed: {e}")
    
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
            print(f"   Button {idx} → GPIO {pin:2d}")
        print(f"   LED       → GPIO {LED_GPIO:2d}")
        print()
    
    def run_combined_loop(self, logger):
        """Main combined loop: button reading + LED keyboard control"""
        print("🎮 COMBINED BUTTON + LED TEST")
        print("=" * 50)
        print("Hardware Setup:")
        print("• Button: SPDT with RC circuit → GPIO22")
        print("• LED: GPIO26 → LED positive + Ground")
        print()
        
        self.print_hardware_setup()
        
        print("📊 Controls & Features:")
        print("  • Buttons: Real-time press/release detection (5ms sampling)")
        print("  • LED: Keyboard control - '1'=ON, '0'=OFF, 'q'=quit")
        print("  • Logging: All button events and LED actions")
        print("  • Terminal: Immediate input (no Enter key needed)")
        print()
        print("⏱️  Starting combined test...")
        print("⌨️  Ready for keyboard input: 1, 0, q")
        print()
        print("Event Log:")
        print("-" * 30)
        
        try:
            # Setup terminal for immediate input
            self.setup_terminal()
            
            while self.running:
                # Button reading (existing logic)
                state = self.button_reader.read_buttons()
                
                # Log button changes immediately
                if state.any_changed:
                    self.log_button_changes(state, logger)
                
                # Check for keyboard input (non-blocking)
                key = self.check_keyboard_input()
                if key:
                    self.process_keyboard_input(key, logger)
                
                # Periodic status summary (every 2000 loops = 10 seconds)
                if self.loop_count % 2000 == 0 and self.loop_count > 0:
                    self.log_status_summary(state, logger)
                
                self.loop_count += 1
                time.sleep(SAMPLE_INTERVAL)
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️  Test stopped by user (Ctrl+C)")
            logger.info(f"Test completed after {self.loop_count} loops")
        except Exception as e:
            logger.error(f"Test error: {e}")
        finally:
            # Critical cleanup
            self.restore_terminal()
            logger.info("Combined test completed - GPIO and terminal will be cleaned up automatically")
    
    def log_button_changes(self, state, logger):
        """Log individual button press/release events (existing logic)"""
        for button_idx in range(state.get_button_count()):
            if state.was_changed[button_idx]:
                gpio_pin = BUTTON_PINS[button_idx]
                current_state = state.for_button[button_idx]
                
                if current_state:
                    action = "PRESSED"
                    self.button_click_counts[button_idx] += 1
                    click_count = self.button_click_counts[button_idx]
                    logger.info(f"Button {button_idx} {action.lower()} (GPIO {gpio_pin}) - Click #{click_count}")
                else:
                    action = "RELEASED"
                    click_count = self.button_click_counts[button_idx]
                    logger.info(f"Button {button_idx} {action.lower()} (GPIO {gpio_pin}) - Total clicks: {click_count}")
    
    def log_status_summary(self, state, logger):
        """Log periodic status including LED state (enhanced logic)"""
        pressed_buttons = []
        for idx, pressed in enumerate(state.for_button):
            if pressed:
                pressed_buttons.append(f"{idx}(GPIO{BUTTON_PINS[idx]})")
        
        # Build click summary
        click_summary = []
        for idx, count in enumerate(self.button_click_counts):
            if count > 0:
                click_summary.append(f"B{idx}:{count}")
        
        # Build status message with LED state
        led_status = "ON" if self.led_state else "OFF"
        if pressed_buttons:
            status_msg = f"Buttons: {len(pressed_buttons)} pressed: {', '.join(pressed_buttons)}"
        else:
            status_msg = "Buttons: None pressed"
        
        if click_summary:
            status_msg += f" | Clicks: {', '.join(click_summary)}"
            
        status_msg += f" | LED: {led_status}"
        
        logger.info(f"Periodic status: {status_msg}")
    
    def cleanup(self):
        """Optional manual cleanup for advanced users"""
        self._cleanup_resources()
    
    def _cleanup_resources(self):
        """Internal cleanup - LED + GPIO + terminal"""
        try:
            # Turn off LED
            GPIO.output(LED_GPIO, GPIO.LOW)
            
            # Restore terminal
            self.restore_terminal()
            
            # GPIO cleanup
            GPIO.cleanup()
            
            print("✅ LED turned off, terminal restored, GPIO cleaned up")
        except Exception:
            pass  # Silent fail during destruction
    
    def __del__(self):
        """Automatic cleanup when object is destroyed"""
        self._cleanup_resources()

def main():
    """Main function with comprehensive setup"""
    print("🎮 COMBINED BUTTON + LED SYSTEM TEST")
    print("=" * 60)
    print("Hardware Requirements:")
    print("• 1 SPDT button with RC circuit (100nF + 330Ω)")
    print("• 1 LED with appropriate current limiting")
    print()
    print("Connection Guide:")
    print(f"  Button → GPIO{BUTTON_PINS[0]:2d} (Physical pin 15)")  
    print(f"  LED +  → GPIO{LED_GPIO:2d} (Physical pin 37)")
    print("  LED -  → Pi Ground (Physical pin 39)")
    print("  Button → Common to GPIO, NC to GND, NO to 3.3V")
    print()
    print("Avoided GPIO conflicts:")
    print("  • GPIO 18, 19, 21 (LED strips)")
    print("  • GPIO 12, 13 (PWM channels)")
    print("  • GPIO 14, 15 (UART)")
    print("  • GPIO 2, 3 (I2C reserved)")
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
    
    test_logger.info("Combined button + LED test starting")
    test_logger.info(f"Configuration: {len(BUTTON_PINS)} button(s), 1 LED, {1/SAMPLE_INTERVAL:.0f}Hz sampling")
    
    # Run the test
    test_runner = ButtonLedsTestRunner()
    
    # Setup both systems
    button_setup = test_runner.setup_button_reader(gpio_logger)
    led_setup = test_runner.setup_led_control(test_logger)
    
    if button_setup and led_setup:
        test_runner.run_combined_loop(test_logger)
    else:
        print("❌ Failed to initialize systems")
        test_logger.error("Test aborted due to setup failure")
    
    # Cleanup
    main_logger.cleanup()

# Import shared utilities
from gpio_utils import gpio_to_physical

if __name__ == "__main__":
    main()
