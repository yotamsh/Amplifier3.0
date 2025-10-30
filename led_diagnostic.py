#!/usr/bin/env python3
"""
Comprehensive LED strip diagnostic - test different parameters
"""
import time
from rpi_ws281x import PixelStrip, Color, ws

def test_led_parameters():
    """Test different LED strip configurations"""
    
    print("🔍 LED STRIP DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # First, let's check what LED strips you have
    print("\n📋 LED STRIP INFORMATION NEEDED:")
    print("Look at your LED strips and answer these questions:")
    print()
    
    # Get strip information
    strip_type = input("1. What's printed on your strips? (WS2812B/WS2811/SK6812/other): ").strip()
    voltage = input("2. What voltage? (5V/12V): ").strip()
    arrows = input("3. Do you see direction arrows → on the strips? (y/n): ").strip().lower()
    
    print(f"\n✅ You have: {strip_type} strips, {voltage}, arrows: {arrows}")
    
    # GPIO setup
    gpio_pin = 18  # Use known working GPIO
    print(f"\n🔌 Connect ONE strip to GPIO {gpio_pin} (Physical pin 12)")
    input("Press ENTER when connected...")
    
    # Test different configurations
    configurations = [
        # (frequency, strip_type_constant, description)
        (800000, ws.WS2811_STRIP_RGB, "WS2812B RGB (standard)"),
        (800000, ws.WS2811_STRIP_GRB, "WS2812B GRB (common alternative)"),
        (800000, ws.WS2811_STRIP_BGR, "WS2812B BGR"),
        (800000, ws.WS2811_STRIP_RBG, "WS2812B RBG"),
        (800000, ws.WS2811_STRIP_GBR, "WS2812B GBR"),
        (800000, ws.WS2811_STRIP_BRG, "WS2812B BRG"),
        (400000, ws.WS2811_STRIP_RGB, "WS2811 RGB (400kHz)"),
        (400000, ws.WS2811_STRIP_GRB, "WS2811 GRB (400kHz)"),
    ]
    
    print(f"\n🧪 Testing {len(configurations)} different configurations...")
    
    working_configs = []
    
    for i, (freq, strip_type_const, desc) in enumerate(configurations, 1):
        print(f"\n--- TEST {i}/{len(configurations)}: {desc} ---")
        
        try:
            # Create strip with current configuration
            strip = PixelStrip(
                10,              # 10 LEDs for testing
                gpio_pin,        # GPIO 18
                freq,            # Test frequency
                10,              # DMA
                False,           # Invert
                100,             # Bright for testing
                0,               # Channel
                strip_type_const # Color order
            )
            
            strip.begin()
            
            # Test pattern: Red, Green, Blue
            print("🔴 Setting LED 0 to RED")
            print("🟢 Setting LED 1 to GREEN") 
            print("🔵 Setting LED 2 to BLUE")
            
            strip.setPixelColor(0, Color(255, 0, 0))    # Should be RED
            strip.setPixelColor(1, Color(0, 255, 0))    # Should be GREEN
            strip.setPixelColor(2, Color(0, 0, 255))    # Should be BLUE
            strip.show()
            
            print("\n👀 CHECK: Are the colors CORRECT?")
            print("   LED 0: Should be BRIGHT RED")
            print("   LED 1: Should be BRIGHT GREEN")  
            print("   LED 2: Should be BRIGHT BLUE")
            print("   Other LEDs: Should be OFF")
            
            result = input("Are colors correct? (y/n): ").strip().lower()
            
            if result == 'y':
                working_configs.append((freq, strip_type_const, desc))
                print(f"✅ SUCCESS: {desc}")
            else:
                print(f"❌ FAILED: {desc}")
            
            # Turn off LEDs
            for j in range(10):
                strip.setPixelColor(j, Color(0, 0, 0))
            strip.show()
            
        except Exception as e:
            print(f"❌ ERROR: {desc} - {e}")
    
    # Results
    print("\n" + "=" * 50)
    print("🏆 DIAGNOSTIC RESULTS:")
    
    if working_configs:
        print(f"✅ Found {len(working_configs)} working configuration(s):")
        for freq, strip_const, desc in working_configs:
            print(f"   ✅ {desc}")
        
        # Use the first working config
        best_freq, best_type, best_desc = working_configs[0]
        print(f"\n🎯 USE THIS CONFIG: {best_desc}")
        print(f"   Frequency: {best_freq}")
        print(f"   Strip type: {best_type}")
        
        return best_freq, best_type, best_desc
    else:
        print("❌ NO working configurations found!")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. Check LED strip is WS2812B or WS2811") 
        print("   2. Check 5V power supply connected")
        print("   3. Check data wire connection")
        print("   4. Check LED strip direction (input end)")
        print("   5. Try a different LED strip")
        
        return None, None, None

if __name__ == "__main__":
    test_led_parameters()

