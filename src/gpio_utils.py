#!/usr/bin/env python3
"""
Simple GPIO utilities for Raspberry Pi 3 Model B
Complete mapping between GPIO numbers and physical pin numbers.

CLI Usage:
    python gpio_utils.py to_physical 25    # Returns: GPIO 25 → Pin 22
    python gpio_utils.py to_gpio 22        # Returns: Pin 22 → GPIO 25
"""

import sys
from typing import Optional

# Complete GPIO to Physical Pin mapping for Raspberry Pi 3 Model B
GPIO_TO_PHYSICAL = {
    0: 27,   1: 28,   2: 3,    3: 5,
    4: 7,    5: 29,   6: 31,   7: 26,
    8: 24,   9: 21,   10: 19,  11: 23,
    12: 32,  13: 33,  14: 8,   15: 10,
    16: 36,  17: 11,  18: 12,  19: 35,
    20: 38,  21: 40,  22: 15,  23: 16,
    24: 18,  25: 22,  26: 37,  27: 13
}

# Physical Pin to GPIO mapping (reverse lookup)
PHYSICAL_TO_GPIO = {v: k for k, v in GPIO_TO_PHYSICAL.items()}

def gpio_to_physical(gpio_num: int) -> int:
    """Convert GPIO number to physical pin number"""
    return GPIO_TO_PHYSICAL.get(gpio_num, "?")

def physical_to_gpio(physical_pin: int) -> Optional[int]:
    """Convert physical pin number to GPIO number"""
    return PHYSICAL_TO_GPIO.get(physical_pin)

def main():
    """Handle CLI commands"""
    if len(sys.argv) < 2:
        # Default: show test mappings
        print("🧪 Testing GPIO Utils")
        print("-" * 30)
        
        # Test your current mappings
        test_gpios = [4, 5, 6, 16, 17, 20, 22, 23, 24, 25]
        print("Your current button GPIOs:")
        for gpio in test_gpios:
            physical = gpio_to_physical(gpio)
            print(f"  GPIO {gpio:2d} → Pin {physical:>2}")
        
        print(f"\nAll available GPIOs: {sorted(GPIO_TO_PHYSICAL.keys())}")
        print(f"Total GPIO pins: {len(GPIO_TO_PHYSICAL)}")
        print("\nCLI Usage:")
        print("  python gpio_utils.py to_physical 25")
        print("  python gpio_utils.py to_gpio 22")
        return
    
    command = sys.argv[1].lower()
    
    if command == "to_physical" and len(sys.argv) == 3:
        try:
            gpio_num = int(sys.argv[2])
            physical = gpio_to_physical(gpio_num)
            if physical == "?":
                print(f"❌ Invalid GPIO: {gpio_num}")
                sys.exit(1)
            else:
                print(f"GPIO {gpio_num} → Pin {physical}")
        except ValueError:
            print(f"❌ Invalid GPIO number: {sys.argv[2]}")
            sys.exit(1)
    
    elif command == "to_gpio" and len(sys.argv) == 3:
        try:
            pin_num = int(sys.argv[2])
            gpio_num = physical_to_gpio(pin_num)
            if gpio_num is None:
                print(f"❌ Pin {pin_num} is not a GPIO pin (power/ground/unused)")
                sys.exit(1)
            else:
                print(f"Pin {pin_num} → GPIO {gpio_num}")
        except ValueError:
            print(f"❌ Invalid pin number: {sys.argv[2]}")
            sys.exit(1)
    
    else:
        print("❌ Usage:")
        print("  python gpio_utils.py to_physical <gpio_number>")
        print("  python gpio_utils.py to_gpio <pin_number>")
        print("  python gpio_utils.py  # Show test mappings")
        sys.exit(1)

if __name__ == "__main__":
    main()
