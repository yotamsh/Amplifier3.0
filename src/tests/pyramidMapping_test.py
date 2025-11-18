#!/usr/bin/env python3
"""
Pyramid Mapping Test - Verify height-based LED mapping

Tests the PyramidMapping class by lighting different height ranges
on the A-shaped pyramid (Strip 1).

Usage:
    sudo python src/tests/pyramidMapping_test.py <start_height> <end_height>
    
Examples:
    sudo python src/tests/pyramidMapping_test.py 0 20      # Bottom 20%
    sudo python src/tests/pyramidMapping_test.py 100 100   # Top line only
    sudo python src/tests/pyramidMapping_test.py 40 60     # Middle band
    sudo python src/tests/pyramidMapping_test.py           # Interactive mode
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

def test_height_range(strip, start: int, end: int, color: Pixel):
    """Test a specific height range"""
    # Clear strip
    strip[:] = Pixel(0, 0, 0)
    
    # Get LEDs in range
    led_indices = pyramidHeight[start:end]
    
    # Light them up
    for idx in led_indices:
        strip[idx] = color
    
    strip.show()
    
    print(f"✅ Height [{start}:{end}] → {len(led_indices)} LEDs lit")
    return led_indices

def run_demo_sequence(strip):
    """Run a predefined demo sequence"""
    print("\n🎬 Running demo sequence...\n")
    
    demos = [
        (1, 20, Pixel(255, 0, 0), "Bottom 20%"),
        (20, 40, Pixel(255, 128, 0), "20-40%"),
        (40, 60, Pixel(255, 255, 0), "40-60% (includes middle bar ~43%)"),
        (60, 80, Pixel(0, 255, 0), "60-80%"),
        (80, 99, Pixel(0, 128, 255), "80-99%"),
        (100, 100, Pixel(255, 0, 255), "Top line only (100%)"),
        (0, 100, Pixel(255, 255, 255), "Full pyramid"),
    ]
    
    for start, end, color, description in demos:
        print(f"📍 {description}")
        led_indices = test_height_range(strip, start, end, color)
        print(f"   LEDs: {sorted(led_indices)[:5]}... (showing first 5)")
        print()
        
        time.sleep(3)
    
    print("✅ Demo complete!")

def run_interactive_mode(strip):
    """Interactive mode - enter height ranges"""
    print("\n🎮 Interactive mode")
    print("Enter height ranges to test (or 'demo' for sequence, 'q' to quit)")
    print("Format: <start> <end>")
    print("Examples: '0 50', '100 100', '43 43'\n")
    
    while True:
        try:
            user_input = input("Height range> ").strip()
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                break
            
            if user_input.lower() == 'demo':
                run_demo_sequence(strip)
                continue
            
            parts = user_input.split()
            if len(parts) != 2:
                print("❌ Enter two numbers: <start> <end>")
                continue
            
            start = int(parts[0])
            end = int(parts[1])
            
            if not (0 <= start <= 100 and 0 <= end <= 100):
                print("❌ Heights must be 0-100")
                continue
            
            # Use green for visibility
            test_height_range(strip, start, end, Pixel(0, 255, 0))
            
        except ValueError:
            print("❌ Invalid input. Enter two numbers.")
        except KeyboardInterrupt:
            print("\n")
            break

def print_mapping_info():
    """Print pyramid mapping information"""
    print("=" * 60)
    print("🔺 PYRAMID MAPPING INFO")
    print("=" * 60)
    print(f"Left side:   {PyramidMapping.LEFT_SIDE_COUNT} LEDs (indices {PyramidMapping.LEFT_START}-{PyramidMapping.LEFT_END-1})")
    print(f"Top line:    {PyramidMapping.TOP_LINE_COUNT} LEDs (indices {PyramidMapping.TOP_START}-{PyramidMapping.TOP_END-1})")
    print(f"Right side:  {PyramidMapping.RIGHT_SIDE_COUNT} LEDs (indices {PyramidMapping.RIGHT_START}-{PyramidMapping.RIGHT_END-1})")
    print(f"Middle bar:  {PyramidMapping.MIDDLE_LINE_COUNT} LEDs (indices {PyramidMapping.MIDDLE_START}-{PyramidMapping.MIDDLE_END-1})")
    print(f"Middle bar height: ~{PyramidMapping.MIDDLE_BAR_HEIGHT}%")
    print(f"Total LEDs:  {PyramidMapping.MIDDLE_END}")
    print("=" * 60)
    print()

def main():
    print_mapping_info()
    
    # Initialize pyramid strip
    strip = PixelStripAdapter(
        led_count=PYRAMID_CONFIG["led_count"],
        gpio_pin=PYRAMID_CONFIG["gpio_pin"],
        dma=PYRAMID_CONFIG["dma"],
        brightness=PYRAMID_CONFIG["brightness"],
        channel=PYRAMID_CONFIG["channel"]
    )
    
    try:
        if len(sys.argv) == 3:
            # Command line mode
            start = int(sys.argv[1])
            end = int(sys.argv[2])
            
            if not (0 <= start <= 100 and 0 <= end <= 100):
                print("❌ Heights must be 0-100")
                sys.exit(1)
            
            print(f"Testing height range [{start}:{end}]...")
            test_height_range(strip, start, end, Pixel(0, 255, 0))
            
            print("\nPress Ctrl+C to exit")
            while True:
                time.sleep(1)
        
        elif len(sys.argv) == 1:
            # Interactive mode
            run_interactive_mode(strip)
        
        else:
            print("Usage: python pyramidMapping_test.py [<start_height> <end_height>]")
            print("   Or: python pyramidMapping_test.py (for interactive mode)")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n")
    
    finally:
        print("🛑 Clearing pyramid...")
        strip[:] = Pixel(0, 0, 0)
        strip.show()
        print("Done!")

if __name__ == "__main__":
    main()

