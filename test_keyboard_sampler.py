#!/usr/bin/env python3
"""
Test script for KeyboardSampler - test button system without GPIO hardware
"""

import sys
import time
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from button_system import KeyboardSampler, ButtonReader
from utils.class_logger import ClassLogger


def main():
    """Test the keyboard sampler"""
    
    # Create logger
    logger = ClassLogger("KeyboardTest", console_only=True)
    
    print("=" * 70)
    print("🎮 Keyboard Sampler Test (NO GPIO Required)")
    print("=" * 70)
    print()
    print("This tests the button system using only keyboard input.")
    print("Perfect for development on Mac/Linux without Raspberry Pi!")
    print()
    print("CONTROLS:")
    print("  • Press digit keys 0-9 to toggle virtual buttons ON/OFF")
    print("  • Press SPACE to show current button states")
    print("  • Press 'r' to reset all buttons to OFF")
    print("  • Press 'q' to quit")
    print()
    print("=" * 70)
    print()
    
    try:
        # Create keyboard sampler (10 virtual buttons)
        num_buttons = 10
        sampler = KeyboardSampler(num_buttons=num_buttons, logger=logger)
        
        # Create button reader using the keyboard sampler
        button_reader = ButtonReader(sampler=sampler, logger=logger)
        
        # Setup
        sampler.setup()
        
        print()
        print("🎮 Keyboard sampler ready! Start pressing digit keys...")
        print()
        
        # Main loop - read button states continuously
        loop_count = 0
        last_state_display = time.time()
        
        while True:
            # Read button states
            button_state = button_reader.read_buttons()
            
            # Display pressed buttons
            if button_state.any_pressed:
                pressed_list = [str(i) for i in range(num_buttons) if button_state.currently_pressed[i]]
                print(f"🔵 Pressed: {', '.join(pressed_list)}")
            
            # Display newly pressed (rising edge)
            if button_state.any_rising_edge:
                rising_list = [str(i) for i in range(num_buttons) if button_state.rising_edge[i]]
                print(f"⬆️  Rising edge: {', '.join(rising_list)}")
            
            # Display newly released (falling edge)
            if button_state.any_falling_edge:
                falling_list = [str(i) for i in range(num_buttons) if button_state.falling_edge[i]]
                print(f"⬇️  Falling edge: {', '.join(falling_list)}")
            
            # Periodically show status (every 5 seconds if no activity)
            current_time = time.time()
            if not button_state.any_pressed and current_time - last_state_display > 5:
                print(f"⏳ Running... (loop #{loop_count}, press digit keys to toggle)")
                last_state_display = current_time
            
            loop_count += 1
            
            # Small delay to prevent CPU spinning
            time.sleep(0.05)  # 50ms = 20 Hz sampling rate
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if 'sampler' in locals():
            sampler.cleanup()
        if 'button_reader' in locals():
            button_reader.cleanup()
        
        print("\n✅ Cleanup complete")
        print("=" * 70)


if __name__ == "__main__":
    main()

