import time
from rpi_ws281x import PixelStrip, Color

# Configuration for dual LED strips
LED_COUNT = 300       # Number of LEDs per strip
LED_FREQ_HZ = 800000  # Signal frequency (800kHz)
LED_BRIGHTNESS = 26   # 0-255 (10% brightness)
LED_INVERT = False    # Signal inversion

# Strip 1 Configuration
LED_PIN_1 = 21
LED_DMA_1 = 10     
LED_1_PWM = 0   

# Strip 2 Configuration
LED_PIN_2 = 19
LED_DMA_2 = 5     
LED_2_PWM = 1

# Strip 3 Configuration
LED_PIN_3 = 18
LED_DMA_3 = 6     
LED_3_PWM = 0

# Initialize all three strips
strip1 = PixelStrip(LED_COUNT, LED_PIN_1, LED_FREQ_HZ, LED_DMA_1, 
                    LED_INVERT, LED_BRIGHTNESS, LED_1_PWM)
strip2 = PixelStrip(LED_COUNT, LED_PIN_2, LED_FREQ_HZ, LED_DMA_2, 
                    LED_INVERT, LED_BRIGHTNESS, LED_2_PWM)
strip3 = PixelStrip(LED_COUNT, LED_PIN_3, LED_FREQ_HZ, LED_DMA_3, 
                    LED_INVERT, LED_BRIGHTNESS, LED_3_PWM)

strip1.begin()
strip2.begin()
strip3.begin()

print(f"✅ Triple LED strips initialized:")
print(f"   Strip 1: GPIO{LED_PIN_1} (PWM{LED_1_PWM}) - {LED_COUNT} LEDs")
print(f"   Strip 2: GPIO{LED_PIN_2} (PWM{LED_2_PWM}) - {LED_COUNT} LEDs")
print(f"   Strip 3: GPIO{LED_PIN_3} (PWM{LED_3_PWM}) - {LED_COUNT} LEDs")

def color_wipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def fill_all(strip, color):
    """Fill all LEDs with the same color at once."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

# Triple strip functions
def color_wipe_all(color1, color2, color3, wait_ms=20):
    print("color wipe all three", color1, color2, color3, wait_ms)
    """Wipe color across all three strips simultaneously."""
    max_pixels = max(strip1.numPixels(), strip2.numPixels(), strip3.numPixels())
    for i in range(max_pixels):
        if i < strip1.numPixels():
            strip1.setPixelColor(i, color1)
        strip1.show()
        if i < strip2.numPixels():
            strip2.setPixelColor(i, color2)
        strip2.show()
        if i < strip3.numPixels():
            strip3.setPixelColor(i, color3)
        strip3.show()
        time.sleep(wait_ms / 1000.0)

def color_wipe_both(color1, color2, wait_ms=20):
    print("color wipe both", color1, color2, wait_ms)
    """Wipe color across both strips simultaneously."""
    max_pixels = max(strip1.numPixels(), strip2.numPixels())
    for i in range(max_pixels):
        if i < strip1.numPixels():
            strip1.setPixelColor(i, color1)
        if i < strip2.numPixels():
            strip2.setPixelColor(i, color2)
        strip1.show()
        strip2.show()
        time.sleep(wait_ms / 1000.0)

def fill_all_three(color):
    """Fill all three strips with the same color at once."""
    fill_all(strip1, color)
    fill_all(strip2, color)
    fill_all(strip3, color)

def fill_all_both(color):
    """Fill both strips with the same color at once."""
    fill_all(strip1, color)
    fill_all(strip2, color)

def fill_strips_different(color1, color2, color3):
    """Fill strip1 with color1, strip2 with color2, and strip3 with color3."""
    fill_all(strip1, color1)
    fill_all(strip2, color2)
    fill_all(strip3, color3)

def get_color_components(color):
    """Extract RGB components from a color integer."""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return r, g, b

def interpolate_color(color1, color2, ratio):
    """Interpolate between two colors based on ratio (0.0 to 1.0)."""
    r1, g1, b1 = get_color_components(color1)
    r2, g2, b2 = get_color_components(color2)
    
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    
    return Color(r, g, b)

def fade_to_color(strip, target_color, duration_ms, steps=50):
    """Fade from current LED state to target color over specified duration."""
    # Get current colors of all LEDs
    current_colors = []
    for i in range(strip.numPixels()):
        current_colors.append(strip.getPixelColor(i))
    
    # Calculate delay between steps
    step_delay = duration_ms / steps / 1000.0
    
    # Perform fade
    for step in range(steps + 1):
        ratio = step / steps
        
        # Set each LED to interpolated color
        for i in range(strip.numPixels()):
            interpolated = interpolate_color(current_colors[i], target_color, ratio)
            strip.setPixelColor(i, interpolated)
        
        strip.show()
        time.sleep(step_delay)

def hsv_to_rgb(h, s, v):
    """Convert HSV to RGB values.
    h: hue (0-360)
    s: saturation (0.0-1.0)
    v: value/brightness (0.0-1.0)
    Returns: (r, g, b) tuple with values 0-255
    """
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
    
    return r, g, b

def ColorHSV(h, s=1.0, v=1.0):
    """Create a Color from HSV values (like FastLED).
    h: hue (0-360)
    s: saturation (0.0-1.0)
    v: value/brightness (0.0-1.0)
    """
    r, g, b = hsv_to_rgb(h, s, v)
    return Color(r, g, b)

def rainbow_fill(strip, start_hue=0, hue_delta=None):
    """Fill strip with rainbow colors (like FastLED).
    start_hue: starting hue (0-360)
    hue_delta: hue change per LED (if None, auto-calculate for full spectrum)
    """
    if hue_delta is None:
        hue_delta = 360.0 / strip.numPixels()  # Full rainbow across strip
    
    for i in range(strip.numPixels()):
        hue = (start_hue + i * hue_delta) % 360
        color = ColorHSV(hue, 1.0, 1.0)  # Full saturation and brightness
        strip.setPixelColor(i, color)
    
    strip.show()

def rainbow_cycle(strip, duration_ms=5000, steps=20):
    """Animated rainbow cycle (like FastLED).
    duration_ms: how long for one full cycle
    steps: animation smoothness
    """
    step_delay = duration_ms / steps / 1000.0
    hue_step = 360.0 / steps
    
    for step in range(steps):
        start_hue = step * hue_step
        rainbow_fill(strip, start_hue)
        time.sleep(step_delay)

# Multi-strip rainbow functions
def rainbow_fill_all(start_hue=0, hue_delta=None):
    """Fill all three strips with rainbow colors."""
    rainbow_fill(strip1, start_hue, hue_delta)
    rainbow_fill(strip2, start_hue, hue_delta)
    rainbow_fill(strip3, start_hue, hue_delta)

def rainbow_fill_both(start_hue=0, hue_delta=None):
    """Fill both strips with rainbow colors."""
    rainbow_fill(strip1, start_hue, hue_delta)
    rainbow_fill(strip2, start_hue, hue_delta)

def rainbow_cycle_all(duration_ms=5000, steps=10):
    """Animated rainbow cycle on all three strips simultaneously."""
    step_delay = duration_ms / steps / 1000.0
    hue_step = 360.0 / steps
    
    for step in range(steps):
        start_hue = step * hue_step
        rainbow_fill(strip1, start_hue)
        time.sleep(0.01)
        rainbow_fill(strip2, start_hue)
        time.sleep(0.01)
        rainbow_fill(strip3, start_hue)
        time.sleep(step_delay)

def rainbow_cycle_both(duration_ms=5000, steps=10):
    """Animated rainbow cycle on both strips simultaneously."""
    step_delay = duration_ms / steps / 1000.0
    hue_step = 360.0 / steps
    
    for step in range(steps):
        start_hue = step * hue_step
        rainbow_fill(strip1, start_hue)
        time.sleep(0.01)
        rainbow_fill(strip2, start_hue)
        time.sleep(step_delay)

def fade_to_color_all(target_color, duration_ms, steps=50):
    """Fade all three strips from current state to target color."""
    fade_to_color(strip1, target_color, duration_ms, steps)
    fade_to_color(strip2, target_color, duration_ms, steps)
    fade_to_color(strip3, target_color, duration_ms, steps)

def fade_to_color_both(target_color, duration_ms, steps=50):
    """Fade both strips from current state to target color."""
    fade_to_color(strip1, target_color, duration_ms, steps)
    fade_to_color(strip2, target_color, duration_ms, steps)

def test():
    try:
        print("\n🎪 Starting DUAL LED Strip Test Show!")
        print("=" * 50)
        
        while True:
            print("\n🟢 Phase 1: Synchronized Effects")
            # Both strips - Green color wipe simultaneously 
            print("   → Synchronized green wipe")
            color_wipe_both(Color(0, 255, 0), Color(0, 255, 0), 10)  # Green, fast wipe (10ms)
            
            # Both strips - Fill red at once and wait 2 seconds
            print("   → Both strips RED")
            fill_all_both(Color(255, 0, 0))  # Red
            time.sleep(2.0)
            
            # Both strips - Fade from red to blue during 1 second
            print("   → Synchronized fade to BLUE")
            fade_to_color_both(Color(0, 0, 255), 1000)  # Blue, 1000ms fade
            time.sleep(2.0)
            
            print("\n🌈 Phase 2: Rainbow Effects")
            # Both strips - Static rainbow
            print("   → Synchronized rainbow pattern")
            rainbow_fill_both()
            time.sleep(3.0)
            
            # Both strips - Animated rainbow cycle
            print("   → Synchronized rainbow cycle")
            rainbow_cycle_both(duration_ms=3000, steps=60)  # 3 second cycle
            
            print("\n🎭 Phase 3: Different Colors Per Strip")
            # Different colors on each strip
            colors = [
                (Color(255, 0, 0), Color(0, 255, 0)),    # Red vs Green
                (Color(0, 0, 255), Color(255, 255, 0)),  # Blue vs Yellow
                (Color(255, 0, 255), Color(0, 255, 255)), # Magenta vs Cyan
                (Color(255, 128, 0), Color(128, 0, 255)), # Orange vs Purple
            ]
            
            for i, (color1, color2) in enumerate(colors):
                print(f"   → Strip contrast #{i+1}")
                fill_strips_different(color1, color2)
                time.sleep(1.5)
            
            print("\n🎨 Phase 4: HSV Color Cycling")
            # HSV color examples - cycle through hues on both strips
            for hue in range(0, 360, 30):  # Every 30 degrees
                print(f"   → Hue: {hue}°")
                fill_all_both(ColorHSV(hue, 1.0, 1.0))  # Pure hue
                time.sleep(0.5)
            
            print("\n🔄 Restarting show...\n")
            
    except KeyboardInterrupt:
        # Turn off all LEDs on exit
        print("\n\n⏹️  Stopping show...")
        fill_all_both(Color(0, 0, 0))
        print("✅ All LEDs turned off. Goodbye!")

if __name__ == "__main__":
    print("🎮 LED Control Ready!")

    # print("Rainbow cycle 1")
    # rainbow_cycle(strip1)

    # print("Rainbow cycle 2")
    # rainbow_cycle(strip2)

    # print("Rainbow cycle both")
    # rainbow_cycle_both()

    print("color wipe 1")
    start_time = time.time()
    color_wipe(strip1, Color(255, 0, 0), 1)
    end_time = time.time()
    total_time = end_time - start_time
    print(f"color_wipe strip1 completed in {total_time:.3f} seconds")

    print("color wipe 2")
    start_time = time.time()
    color_wipe(strip2, Color(0, 255, 0), 1)
    end_time = time.time()
    total_time = end_time - start_time
    print(f"color_wipe strip2 completed in {total_time:.3f} seconds")

    print("color wipe 3")
    start_time = time.time()
    color_wipe(strip3, Color(0, 0, 255), 1)
    end_time = time.time()
    total_time = end_time - start_time
    print(f"color_wipe strip3 completed in {total_time:.3f} seconds")

    print("color wipe both")
    start_time = time.time()
    color_wipe_both(Color(255, 255, 0), Color(0, 255, 255), 1)
    end_time = time.time()
    total_time = end_time - start_time
    print(f"color_wipe_both completed in {total_time:.3f} seconds")

    print("color wipe all three")
    start_time = time.time()
    color_wipe_all(Color(255, 128, 0), Color(128, 255, 0), Color(255, 0, 128), 1)
    end_time = time.time()
    total_time = end_time - start_time
    print(f"color_wipe_all completed in {total_time:.3f} seconds")

    print("End of tests")