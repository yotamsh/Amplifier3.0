#!/usr/bin/env python3
"""
Simple LED Strip Range Test
Usage: python rangeLedStripTest.py <strip_index> <start_led> <end_led>
Example: python rangeLedStripTest.py 0 50 100
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from led_system import PixelStripAdapter, Pixel

# Strip configurations matching amplifier.py
STRIP_CONFIGS = [
    {  # Strip 0
        "gpio_pin": 21,
        "led_count": 300,
        "dma": 5,
        "brightness": 26,
        "channel": 0
    },
    {  # Strip 1
        "gpio_pin": 18,
        "led_count": 300,
        "dma": 10,
        "brightness": 26,
        "channel": 0
    }
]

def main():
    if len(sys.argv) != 4:
        print("Usage: python rangeLedStripTest.py <strip_index> <start_led> <end_led>")
        print("Example: python rangeLedStripTest.py 0 50 100")
        sys.exit(1)
    
    # Parse arguments
    i = int(sys.argv[1])  # Strip index (0 or 1)
    n = int(sys.argv[2])  # Start LED
    m = int(sys.argv[3])  # End LED
    
    # Validate inputs
    if i not in [0, 1]:
        print(f"Error: Strip index must be 0 or 1, got {i}")
        sys.exit(1)
    
    if not (0 <= n <= m < 300):
        print(f"Error: LED range must be 0 <= n <= m < 300, got n={n}, m={m}")
        sys.exit(1)
    
    # Initialize the specified strip
    config = STRIP_CONFIGS[i]
    strip = PixelStripAdapter(
        led_count=config["led_count"],
        gpio_pin=config["gpio_pin"],
        dma=config["dma"],
        brightness=config["brightness"],
        channel=config["channel"]
    )
    
    # Define colors
    red = Pixel(255, 0, 0)
    green = Pixel(0, 255, 0)
    
    # Set LEDs: green for all first
    for led_idx in range(300):
        strip[led_idx] = green
    
    # Set LEDs n to m (inclusive) as red
    for led_idx in range(n, m + 1):
        strip[led_idx] = red
    
    # Show the strip
    strip.show()
    
    print(f"✅ Strip {i}: LEDs {n}-{m} = RED, rest = GREEN")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n🛑 Clearing strip...")
        black = Pixel(0, 0, 0)
        strip[:] = black
        strip.show()
        print("Done")

if __name__ == "__main__":
    main()

