#!/usr/bin/env python3
"""
Generate PWA icons for AI-Powered Tuxemon
Creates basic but professional icons for all required sizes using PIL
"""

import os
from PIL import Image, ImageDraw
from pathlib import Path

# Icon sizes required by manifest.json
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Game colors (matching theme)
COLORS = {
    'background': '#1a202c',  # Dark background
    'primary': '#4299e1',     # Blue theme color
    'accent': '#38b2ac',      # Teal accent
    'text': '#ffffff'         # White text
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_icon(size):
    """Generate a game-themed icon using PIL"""
    # Create new image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size // 2

    # Background circle
    draw.ellipse([0, 0, size, size], fill=hex_to_rgb(COLORS['background']))

    # Outer ring
    margin = size * 0.05
    draw.ellipse([margin, margin, size - margin, size - margin],
                fill=hex_to_rgb(COLORS['primary']))

    # Inner circle
    inner_margin = size * 0.15
    draw.ellipse([inner_margin, inner_margin, size - inner_margin, size - inner_margin],
                fill=hex_to_rgb(COLORS['background']))

    # Game controller/monster ball design
    ball_margin = size * 0.25
    draw.ellipse([ball_margin, ball_margin, size - ball_margin, size - ball_margin],
                fill=hex_to_rgb(COLORS['accent']))

    # Central dot (like a Pokéball)
    dot_size = size * 0.08
    dot_margin = center - dot_size
    draw.ellipse([dot_margin, dot_margin, center + dot_size, center + dot_size],
                fill=hex_to_rgb(COLORS['text']))

    # Horizontal line through center (Pokéball style)
    line_width = max(2, size // 32)
    line_start = size * 0.25
    line_end = size * 0.75
    draw.rectangle([line_start, center - line_width//2, line_end, center + line_width//2],
                  fill=hex_to_rgb(COLORS['text']))

    return img

def generate_shortcut_icon(size, icon_type='battle'):
    """Generate shortcut icons"""
    # Create new image
    color = '#e53e3e' if icon_type == 'battle' else '#38b2ac'
    img = Image.new('RGBA', (size, size), hex_to_rgb(color))
    draw = ImageDraw.Draw(img)

    center = size // 2

    if icon_type == 'battle':
        # Battle sword icon - simple rectangle for sword
        sword_width = max(4, size // 24)
        sword_height = size * 0.6
        sword_x = center - sword_width // 2
        sword_y = center - sword_height // 2
        draw.rectangle([sword_x, sword_y, sword_x + sword_width, sword_y + sword_height],
                      fill=hex_to_rgb(COLORS['text']))

        # Crossguard
        guard_width = size // 6
        guard_height = max(4, size // 16)
        guard_x = center - guard_width // 2
        guard_y = sword_y + sword_height // 6
        draw.rectangle([guard_x, guard_y, guard_x + guard_width, guard_y + guard_height],
                      fill=hex_to_rgb(COLORS['text']))
    else:
        # Chat bubble icon - simple circle
        bubble_size = size * 0.3
        bubble_margin = center - bubble_size
        draw.ellipse([bubble_margin, bubble_margin - 4, center + bubble_size, center + bubble_size - 4],
                    fill=hex_to_rgb(COLORS['text']))

        # Chat tail - simple triangle
        tail_points = [
            (center - 8, center + 8),
            (center, center + 16),
            (center + 8, center + 8)
        ]
        draw.polygon(tail_points, fill=hex_to_rgb(COLORS['text']))

    return img

def save_icon(img, filename):
    """Save image as PNG file"""
    icons_dir = Path(__file__).parent / 'public' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)

    icon_path = icons_dir / filename
    img.save(icon_path, 'PNG')
    print(f"Generated: {filename}")

def generate_all_icons():
    """Generate all required icons"""
    print("Generating PWA icons for AI-Powered Tuxemon...")

    try:
        # Main app icons
        for size in ICON_SIZES:
            img = generate_icon(size)
            save_icon(img, f'icon-{size}x{size}.png')

        # Shortcut icons
        battle_icon = generate_shortcut_icon(96, 'battle')
        save_icon(battle_icon, 'battle-shortcut.png')

        chat_icon = generate_shortcut_icon(96, 'chat')
        save_icon(chat_icon, 'chat-shortcut.png')

        print("All PWA icons generated successfully!")
        print("\nGenerated icons:")
        for size in ICON_SIZES:
            print(f"  - icon-{size}x{size}.png")
        print("  - battle-shortcut.png")
        print("  - chat-shortcut.png")

        return True

    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("Please install Pillow: pip install Pillow")
        return False
    except Exception as e:
        print(f"Error generating icons: {e}")
        return False

if __name__ == "__main__":
    success = generate_all_icons()
    if not success:
        exit(1)