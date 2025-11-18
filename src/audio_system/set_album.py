#!/usr/bin/env python3
"""Set MP3 album tag"""
import sys
import os
import eyed3

# Suppress eyed3 verbose logging
eyed3.log.setLevel("ERROR")

if len(sys.argv) != 3:
    print("Usage: python set_album.py <song.mp3> <album_name>")
    sys.exit(1)

song_file = sys.argv[1]
album_name = sys.argv[2]

# Load MP3
audio = eyed3.load(song_file)

if audio is None:
    print(f"❌ Error: Couldn't load {song_file}")
    sys.exit(1)

# Initialize tags if they don't exist
if audio.tag is None:
    audio.initTag()
    print(f"ℹ️  Initialized ID3 tags for {song_file}")

# Set album
audio.tag.album = album_name
audio.tag.save()

# Update modification time to ensure rsync detects the change
os.utime(song_file, None)

print(f"✅ Set album to '{album_name}' for {song_file}")