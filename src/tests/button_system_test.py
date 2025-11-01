#!/usr/bin/env python3
"""
Button System Test - Multiple Button Edge Detection

Tests the button system with 10 GPIO inputs, showing real-time
button press/release detection with 5ms sampling rate.

GPIO Selection: Uses pins that don't conflict with PWM or LED strips
"""
import sys
import time
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
     4, 
    # 5,  
    # 6, 
    # 16,
    # 17,
    # 20,
    # 22,
    # 23,
    # 24,
    #25 
]

# Avoided GPIOs (conflicts):
# GPIO 18, 19, 21 - LED strips
# GPIO 12, 13 - PWM channels
# GPIO 14, 15 - UART
# GPIO 2, 3 - I2C (reserved for expansion)

SAMPLE_INTERVAL = 0.005  # 5ms = 200Hz sampling rate

class ButtonTestRunner:
    """High-frequency button test with edge detection"""
    
    def __init__(self):
        self.running = True
        self.button_reader = None
        self.loop_count = 0
        self.button_click_counts = [0] * len(BUTTON_PINS)  # Click counter per button
        
        print(f"🔲 Setting up button test with {len(BUTTON_PINS)} buttons...")
        
    def setup_button_reader(self, logger):
        """Initialize button reader with selected GPIOs"""
        try:
            self.button_reader = ButtonReader(
                button_pins=BUTTON_PINS,
                logger=logger,
                pull_mode=GPIO.PUD_OFF  # No internal pulls (external circuits)
            )
            
            logger.info("Button reader initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Button reader setup failed: {e}")
            return False
    
    def print_button_mapping(self):
        """Display button-to-GPIO mapping"""
        print("📍 Button Mapping:")
        for idx, pin in enumerate(BUTTON_PINS):
            print(f"   Button {idx:2d} → GPIO {pin:2d}")
        print()
    
    def run_test_loop(self, logger):
        """Main test loop with 5ms sampling"""
        print("🎮 BUTTON SYSTEM TEST - EDGE DETECTION")
        print("=" * 50)
        print("Hardware Setup (10 buttons with external pull circuits):")
        
        self.print_button_mapping()
        
        print("📊 Instructions:")
        print("  • Press/release buttons to see edge detection")
        print("  • Each button press/release will be logged immediately")
        print("  • Status summary every 10 seconds")
        print("  • Press Ctrl+C to stop")
        print()
        print("⏱️  Starting detection (5ms sampling)...")
        print()
        print("Event Log:")
        print("-" * 30)
        
        try:
            while self.running:
                state = self.button_reader.read_buttons()
                
                # Log any button changes immediately
                if state.any_changed:
                    self.log_button_changes(state, logger)
                
                # Periodic status (every 2000 loops = 10 seconds at 5ms)
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
            self.cleanup()
    
    def log_button_changes(self, state, logger):
        """Log individual button press/release events"""
        for button_idx in range(state.get_button_count()):
            if state.was_changed[button_idx]:
                gpio_pin = BUTTON_PINS[button_idx]
                current_state = state.for_button[button_idx]
                
                # Determine action and update click counter
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
        """Log periodic status summary"""
        pressed_buttons = []
        for idx, pressed in enumerate(state.for_button):
            if pressed:
                pressed_buttons.append(f"{idx}(GPIO{BUTTON_PINS[idx]})")
        
        # Build click summary
        click_summary = []
        for idx, count in enumerate(self.button_click_counts):
            if count > 0:
                click_summary.append(f"B{idx}:{count}")
        
        if pressed_buttons:
            status_msg = f"Status: {len(pressed_buttons)} pressed: {', '.join(pressed_buttons)}"
        else:
            status_msg = "Status: No buttons currently pressed"
        
        if click_summary:
            status_msg += f" | Clicks: {', '.join(click_summary)}"
        
        logger.info(f"Periodic status: {status_msg}")
    
    def cleanup(self):
        """Clean up resources"""
        print("🔄 Cleaning up...")
        self.running = False
        
        if self.button_reader:
            self.button_reader.cleanup()
        
        print("✅ Test completed and resources cleaned up")

def main():
    """Main function"""
    print("🎮 BUTTON SYSTEM TEST - 10 BUTTON EDGE DETECTION")
    print("=" * 55)
    print("Hardware Requirements:")
    print("  • 10 SPDT buttons with external pull circuits")
    print("  • Button Common → GPIO pin, NC → GND, NO → 3.3V")
    print("  • 330Ω resistor + 100nF capacitor per button for filtering")
    print()
    print("Selected GPIOs (avoiding PWM/LED conflicts):")
    for idx, pin in enumerate(BUTTON_PINS):
        print(f"  Button {idx:2d} → GPIO {pin:2d} (Physical pin {gpio_to_physical(pin)})")
    print()
    print("Avoided GPIOs:")
    print("  • GPIO 18, 19, 21 (LED strips)")
    print("  • GPIO 12, 13 (PWM channels)")  
    print("  • GPIO 14, 15 (UART)")
    print("  • GPIO 2, 3 (I2C reserved)")
    print()
    
    # Verify user is ready
    input("📍 Press ENTER when buttons are connected...")
    print()
    
    # Start test with enhanced logging
    main_logger = HybridLogger("ButtonSystemTest")
    
    # Get class-specific loggers with different levels
    test_logger = main_logger.get_class_logger("ButtonTestRunner", logging.DEBUG)
    gpio_logger = main_logger.get_class_logger("ButtonReader", logging.INFO)
    
    test_logger.info("Button system test starting")
    test_logger.info(f"Testing {len(BUTTON_PINS)} buttons at {1/SAMPLE_INTERVAL:.0f}Hz")
    
    test_runner = ButtonTestRunner()
    
    if test_runner.setup_button_reader(gpio_logger):
        test_runner.run_test_loop(test_logger)
    else:
        print("❌ Failed to initialize button reader")
        test_logger.error("Test aborted due to setup failure")
    
    # Cleanup
    main_logger.cleanup()

def gpio_to_physical(gpio_num):
    """Convert GPIO number to physical pin number for user reference"""
    gpio_to_pin_map = {
        4: 7, 5: 29, 6: 31, 16: 36, 17: 11,
        20: 38, 22: 15, 23: 16, 24: 18, 25: 22
    }
    return gpio_to_pin_map.get(gpio_num, "?")

if __name__ == "__main__":
    main()
