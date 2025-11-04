#!/usr/bin/env python3
"""
Dual Strip Rainbow - Control two 300-LED strips as one logical 600-LED rainbow

Instead of chaining, this uses:
- Strip 1A: GPIO18, LEDs 0-299 (first half of rainbow)  
- Strip 1B: GPIO21, LEDs 300-599 (second half of rainbow)

This avoids chaining issues while achieving the same visual effect.
"""
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from led_system import PixelStripAdapter, Pixel
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on a Raspberry Pi with required libraries installed")
    sys.exit(1)

class DualRainbowStrip:
    """Treats two 300-LED strips as one logical 600-LED rainbow strip"""
    
    def __init__(self):
        # Strip 1A: First half (LEDs 0-299)
        self.strip1 = PixelStripAdapter(
            led_count=300,
            gpio_pin=18,  # GPIO18
            freq_hz=800000,
            dma=10,
            invert=False,
            brightness=26,
            channel=0
        )
        
        # Strip 1B: Second half (LEDs 300-599) 
        self.strip2 = PixelStripAdapter(
            led_count=300,
            gpio_pin=21,  # GPIO21  
            freq_hz=800000,
            dma=5,
            invert=False,
            brightness=26,
            channel=0
        )
        
        print(f"✅ Dual strip initialized: 2x300 = 600 total LEDs")
        print(f"   Strip 1A: GPIO18 (LEDs 0-299)")
        print(f"   Strip 1B: GPIO21 (LEDs 300-599)")
    
    def set_pixel(self, index: int, color: Pixel):
        """Set a pixel in the logical 600-LED strip"""
        if index < 300:
            self.strip1[index] = color
        elif index < 600:
            self.strip2[index - 300] = color
        else:
            raise IndexError(f"Pixel {index} out of range (0-599)")
    
    def clear_all(self):
        """Clear both strips"""
        self.strip1[:] = Pixel(0, 0, 0)
        self.strip2[:] = Pixel(0, 0, 0)
    
    def show(self):
        """Update both strips simultaneously"""
        self.strip1.show()
        self.strip2.show()
    
    def num_pixels(self) -> int:
        """Total logical pixel count"""
        return 600

def hsv_to_color(h: float, s: float, v: float) -> Pixel:
    """Convert HSV to RGB Pixel"""
    h = h % 360
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
    else:
        r, g, b = c, 0, x
    
    return Pixel(int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

def rainbow_cycle_demo(strip: DualRainbowStrip):
    """Demo rainbow cycling across both strips"""
    print(f"\n🌈 Starting rainbow cycle demo across 600 LEDs...")
    print("   Press Ctrl+C to stop")
    
    hue_offset = 0
    
    try:
        while True:
            # Generate rainbow across all 600 LEDs
            for i in range(600):
                hue = (i * 360 / 600 + hue_offset) % 360
                color = hsv_to_color(hue, 1.0, 1.0)
                strip.set_pixel(i, color)
            
            strip.show()
            hue_offset = (hue_offset + 2) % 360  # Cycle colors
            time.sleep(0.05)  # 20 FPS
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Rainbow demo stopped")
        strip.clear_all()
        strip.show()

def test_strip_sections(strip: DualRainbowStrip):
    """Test each section of the dual strip"""
    print(f"\n🧪 Testing strip sections...")
    
    tests = [
        ("First strip (0-299) RED", 0, 300, Pixel(255, 0, 0)),
        ("Second strip (300-599) BLUE", 300, 600, Pixel(0, 0, 255)),
        ("First 50 GREEN", 0, 50, Pixel(0, 255, 0)),
        ("Last 50 YELLOW", 550, 600, Pixel(255, 255, 0)),
        ("Middle junction (280-320) WHITE", 280, 320, Pixel(100, 100, 100)),
    ]
    
    for test_name, start, end, color in tests:
        print(f"   🔍 {test_name}")
        
        strip.clear_all()
        for i in range(start, end):
            strip.set_pixel(i, color)
        strip.show()
        
        response = input(f"      👀 Can you see {test_name}? (y/n): ").lower()
        if response.startswith('n'):
            print(f"      ❌ Issue with LEDs {start}-{end}")
        else:
            print(f"      ✅ Section working")
        
        time.sleep(0.5)
    
    strip.clear_all()
    strip.show()

def main():
    print("🌈 DUAL STRIP RAINBOW TEST")
    print("=" * 40)
    print("This treats two 300-LED strips as one 600-LED rainbow")
    print("by using separate GPIO pins instead of chaining.")
    print("")
    print("Hardware connections:")
    print("  Strip 1A → GPIO18 (LEDs 0-299)")
    print("  Strip 1B → GPIO21 (LEDs 300-599)")
    print("  Both strips → 5V power + GND")
    print("")
    
    try:
        # Initialize dual strip
        dual_strip = DualRainbowStrip()
        
        # Test sections first
        test_strip_sections(dual_strip)
        
        input("\nPress Enter to start rainbow demo...")
        
        # Run rainbow demo
        rainbow_cycle_demo(dual_strip)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("🏁 Test complete!")

if __name__ == "__main__":
    main()
