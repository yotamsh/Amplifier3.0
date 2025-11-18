#!/usr/bin/env python3
"""
Pyramid Wipe Animation Test - Color wipe from bottom to top

Creates a smooth wipe animation that fills the pyramid from bottom to top
with colors transitioning one after another.

Usage:
    sudo python src/tests/pyramidWipe_test.py [speed]
    
Examples:
    sudo python src/tests/pyramidWipe_test.py         # Default speed
    sudo python src/tests/pyramidWipe_test.py 0.05    # Faster wipe
    sudo python src/tests/pyramidWipe_test.py 0.02    # Very fast
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from led_system import PixelStripAdapter, Pixel
from game_system.animation_helpers import pyramidHeight, PyramidMapping

# Strip 1 configuration (pyramid)
PYRAMID_CONFIG = {
    "gpio_pin": 18,
    "led_count": 300,
    "dma": 10,
    "brightness": 26,
    "channel": 0
}

# Color sequence for wipe
COLOR_SEQUENCE = [
    (Pixel(255, 0, 0), "Red"),
    (Pixel(255, 128, 0), "Orange"),
    (Pixel(255, 255, 0), "Yellow"),
    (Pixel(0, 255, 0), "Green"),
    (Pixel(0, 128, 255), "Cyan"),
    (Pixel(0, 0, 255), "Blue"),
    (Pixel(128, 0, 255), "Purple"),
    (Pixel(255, 0, 128), "Magenta"),
]

def wipe_bottom_to_top(strip, color: Pixel, delay: float = 0.03):
    """
    Wipe a single color from bottom to top.
    
    Args:
        strip: LED strip adapter
        color: Color to wipe
        delay: Delay between height levels (seconds)
    """
    # Clear strip first
    strip[:] = Pixel(0, 0, 0)
    strip.show()
    
    # Wipe from height 0 to 100
    for height in range(0, 101):
        led_indices = pyramidHeight[0:height]
        
        # Light all LEDs from bottom to current height
        for idx in led_indices:
            strip[idx] = color
        
        strip.show()
        time.sleep(delay)

def wipe_multi_color_sequence(strip, colors: list, delay: float = 0.03):
    """
    Wipe multiple colors from bottom to top in sequence.
    Each color fills a portion of the pyramid height.
    
    Args:
        strip: LED strip adapter
        colors: List of (Pixel, name) tuples
        delay: Delay between height levels (seconds)
    """
    num_colors = len(colors)
    height_per_color = 100 / num_colors  # Divide height equally
    
    strip[:] = Pixel(0, 0, 0)
    strip.show()
    
    print(f"\n🌈 Wiping {num_colors} colors from bottom to top...")
    
    # Wipe from bottom to top
    for height in range(0, 101):
        # Determine which colors to show up to this height
        for color_idx, (color, name) in enumerate(colors):
            color_start = int(color_idx * height_per_color)
            color_end = int((color_idx + 1) * height_per_color)
            
            if height >= color_start:
                # Fill this color's range (up to current height)
                actual_end = min(height, color_end)
                led_indices = pyramidHeight[color_start:actual_end]
                
                for idx in led_indices:
                    strip[idx] = color
        
        strip.show()
        time.sleep(delay)
    
    print("✅ Wipe complete!")

def wipe_rainbow_smooth(strip, delay: float = 0.02):
    """
    Smooth rainbow wipe from bottom to top.
    Color gradually transitions through full spectrum.
    
    Args:
        strip: LED strip adapter
        delay: Delay between height levels (seconds)
    """
    from game_system.animation_helpers import AnimationHelpers
    
    strip[:] = Pixel(0, 0, 0)
    strip.show()
    
    print("\n🌈 Rainbow wipe from bottom to top...")
    
    for height in range(0, 101):
        # Calculate hue based on height (0-360 degrees)
        hue = (height / 100.0) * 360
        color = AnimationHelpers.hsv_to_pixel(hue, 1.0, 1.0)
        
        # Fill from bottom to current height with gradient
        for h in range(0, height + 1):
            h_hue = (h / 100.0) * 360
            h_color = AnimationHelpers.hsv_to_pixel(h_hue, 1.0, 1.0)
            
            for idx in pyramidHeight[h:h]:  # Single height bucket
                strip[idx] = h_color
        
        strip.show()
        time.sleep(delay)
    
    print("✅ Rainbow wipe complete!")

def wipe_fill_and_drain(strip, color: Pixel, fill_delay: float = 0.02, hold_time: float = 0.5):
    """
    Fill from bottom to top, hold, then drain from top to bottom.
    
    Args:
        strip: LED strip adapter
        color: Color to use
        fill_delay: Delay during fill
        hold_time: Time to hold at full
    """
    print(f"\n💧 Fill and drain animation...")
    
    # Fill up
    for height in range(0, 101):
        led_indices = pyramidHeight[0:height]
        
        strip[:] = Pixel(0, 0, 0)
        for idx in led_indices:
            strip[idx] = color
        
        strip.show()
        time.sleep(fill_delay)
    
    # Hold
    time.sleep(hold_time)
    
    # Drain down
    for height in range(100, -1, -1):
        led_indices = pyramidHeight[0:height]
        
        strip[:] = Pixel(0, 0, 0)
        for idx in led_indices:
            strip[idx] = color
        
        strip.show()
        time.sleep(fill_delay)
    
    print("✅ Fill and drain complete!")

def run_demo_sequence(strip, speed: float):
    """Run all wipe animations in sequence"""
    
    demos = [
        ("Single Color Wipe (Red)", lambda: wipe_bottom_to_top(strip, Pixel(255, 0, 0), speed)),
        ("Multi-Color Sequence", lambda: wipe_multi_color_sequence(strip, COLOR_SEQUENCE, speed)),
        ("Rainbow Smooth", lambda: wipe_rainbow_smooth(strip, speed)),
        ("Fill and Drain (Blue)", lambda: wipe_fill_and_drain(strip, Pixel(0, 128, 255), speed, 1.0)),
    ]
    
    for name, demo_func in demos:
        print(f"\n{'='*60}")
        print(f"▶️  {name}")
        print('='*60)
        
        demo_func()
        
        print(f"Waiting 2 seconds...\n")
        time.sleep(2)
    
    print("\n✅ All demos complete!")

def main():
    # Parse speed argument
    speed = 0.03  # Default delay between steps
    
    if len(sys.argv) > 1:
        try:
            speed = float(sys.argv[1])
            if speed < 0:
                print("❌ Speed must be positive")
                sys.exit(1)
        except ValueError:
            print("❌ Speed must be a number (e.g., 0.03)")
            sys.exit(1)
    
    print("🔺 PYRAMID WIPE ANIMATION TEST")
    print(f"⏱️  Speed: {speed}s per step")
    print()
    
    # Initialize pyramid strip
    strip = PixelStripAdapter(
        led_count=PYRAMID_CONFIG["led_count"],
        gpio_pin=PYRAMID_CONFIG["gpio_pin"],
        dma=PYRAMID_CONFIG["dma"],
        brightness=PYRAMID_CONFIG["brightness"],
        channel=PYRAMID_CONFIG["channel"]
    )
    
    try:
        run_demo_sequence(strip, speed)
        
        print("\nPress Ctrl+C to exit")
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n")
    
    finally:
        print("🛑 Clearing pyramid...")
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        print("Done!")

if __name__ == "__main__":
    main()

