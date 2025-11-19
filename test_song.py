#!/usr/bin/env python3
"""
Simple song player for testing audio files with pygame.

Plays a song for 10 seconds then exits automatically.
CTRL+C to exit early.

Usage:
    python test_song.py path/to/song.mp3
"""

import sys
import time
import signal

try:
    import pygame
except ImportError:
    print("❌ Error: pygame not installed")
    print("Install with: pip install pygame")
    sys.exit(1)


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully"""
    print("\n\n⏹️  Stopped by user")
    pygame.mixer.music.stop()
    pygame.quit()
    sys.exit(0)


def play_song(song_path: str, duration_seconds: int = 10):
    """
    Play a song for specified duration.
    
    Args:
        song_path: Path to audio file
        duration_seconds: How long to play (default: 10 seconds)
    """
    # Register CTRL+C handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize pygame mixer
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=4096)
    pygame.mixer.init()
    
    print(f"🎵 Testing: {song_path}")
    print(f"⏱️  Playing for {duration_seconds} seconds...")
    print(f"Press CTRL+C to stop early\n")
    
    try:
        # Load and play song
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.set_volume(0.7)  # 70% volume
        pygame.mixer.music.play()
        
        print("▶️  Playing...")
        
        start_time = time.time()
        elapsed = 0.0  # Initialize elapsed time
        
        # Wait for duration or until song ends
        while True:
            elapsed = time.time() - start_time
            
            # Check if duration reached
            if elapsed >= duration_seconds:
                print(f"\n⏱️  {duration_seconds} seconds elapsed")
                break
            
            # Check if song finished naturally
            if not pygame.mixer.music.get_busy():
                # If song stopped too quickly, it likely failed
                if elapsed < 1.0:
                    print(f"\n❌ Playback failed (stopped after {elapsed:.1f}s - file likely corrupted)")
                    pygame.quit()
                    sys.exit(1)
                else:
                    print(f"\n✅ Song finished (played {elapsed:.1f}s)")
                break
            
            # Update progress every second
            if int(elapsed) != int(elapsed - 0.1):
                progress = "█" * int(elapsed) + "░" * (duration_seconds - int(elapsed))
                print(f"\r[{progress}] {int(elapsed)}/{duration_seconds}s", end="", flush=True)
            
            time.sleep(0.1)
        
        # Stop playback
        pygame.mixer.music.stop()
        pygame.quit()
        
        # Final check - if we didn't play for at least 2 seconds, it's suspicious
        if elapsed < 2.0:
            print(f"\n⚠️  Warning: Song played for only {elapsed:.1f}s - may be corrupted\n")
        else:
            print("\n✅ Test complete\n")
        
    except pygame.error as e:
        print(f"\n❌ Pygame error: {e}")
        pygame.quit()
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n❌ File not found: {song_path}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        pygame.quit()
        sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python test_song.py path/to/song.mp3")
        sys.exit(1)
    
    song_path = sys.argv[1]
    play_song(song_path, duration_seconds=10)


if __name__ == "__main__":
    main()

