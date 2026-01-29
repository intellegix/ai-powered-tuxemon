#!/usr/bin/env python3
"""
Generate PWA screenshots for AI-Powered Tuxemon
Creates placeholder screenshots for app store display
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Screenshot dimensions (iPhone 13 Pro size)
SCREENSHOT_SIZE = (390, 844)

# Game colors
COLORS = {
    'background': '#1a202c',
    'primary': '#4299e1',
    'accent': '#38b2ac',
    'text': '#ffffff',
    'card': '#2d3748'
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_mobile_gameplay_screenshot():
    """Generate mobile gameplay screenshot"""
    img = Image.new('RGB', SCREENSHOT_SIZE, hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    width, height = SCREENSHOT_SIZE

    # Header area
    header_height = 80
    draw.rectangle([0, 0, width, header_height], fill=hex_to_rgb(COLORS['primary']))

    # Game title in header
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    text = "AI-Powered Tuxemon"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (width - text_width) // 2
    draw.text((text_x, 25), text, fill=hex_to_rgb(COLORS['text']), font=font)

    # Game world area (main content)
    game_area_y = header_height + 20
    game_area_height = height - header_height - 150

    # Draw simple game world representation
    draw.rectangle([20, game_area_y, width-20, game_area_y + game_area_height],
                  fill=hex_to_rgb(COLORS['card']))

    # Player character representation (circle)
    player_x, player_y = width // 2, game_area_y + game_area_height // 2
    draw.ellipse([player_x-20, player_y-20, player_x+20, player_y+20],
                fill=hex_to_rgb(COLORS['accent']))

    # NPC characters (smaller circles around player)
    npc_positions = [
        (player_x - 80, player_y - 60),
        (player_x + 70, player_y - 40),
        (player_x - 50, player_y + 80)
    ]

    for npc_x, npc_y in npc_positions:
        draw.ellipse([npc_x-15, npc_y-15, npc_x+15, npc_y+15],
                    fill=hex_to_rgb(COLORS['primary']))

    # UI elements at bottom
    ui_y = height - 120

    # Touch controls representation
    control_size = 50
    controls = [
        (30, ui_y + 30),  # Left control
        (width - 80, ui_y + 30),  # Right control
        (width - 80, ui_y - 20),  # Action button
    ]

    for ctrl_x, ctrl_y in controls:
        draw.ellipse([ctrl_x, ctrl_y, ctrl_x + control_size, ctrl_y + control_size],
                    outline=hex_to_rgb(COLORS['text']), width=2)

    # Status info
    status_text = "Level 5 | NPCs: 3 nearby | Touch to interact"
    try:
        small_font = ImageFont.truetype("arial.ttf", 14)
    except:
        small_font = ImageFont.load_default()

    status_bbox = draw.textbbox((0, 0), status_text, font=small_font)
    status_width = status_bbox[2] - status_bbox[0]
    status_x = (width - status_width) // 2
    draw.text((status_x, height - 30), status_text, fill=hex_to_rgb(COLORS['text']), font=small_font)

    return img

def generate_battle_screenshot():
    """Generate battle interface screenshot"""
    img = Image.new('RGB', SCREENSHOT_SIZE, hex_to_rgb(COLORS['background']))
    draw = ImageDraw.Draw(img)

    width, height = SCREENSHOT_SIZE

    # Battle header
    header_height = 60
    draw.rectangle([0, 0, width, header_height], fill=hex_to_rgb(COLORS['primary']))

    try:
        font = ImageFont.truetype("arial.ttf", 18)
        small_font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    battle_text = "Battle Mode"
    text_bbox = draw.textbbox((0, 0), battle_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_x = (width - text_width) // 2
    draw.text((text_x, 20), battle_text, fill=hex_to_rgb(COLORS['text']), font=font)

    # Enemy monster area
    enemy_y = header_height + 40
    enemy_size = 80
    enemy_x = width // 2 - enemy_size // 2
    draw.ellipse([enemy_x, enemy_y, enemy_x + enemy_size, enemy_y + enemy_size],
                fill=hex_to_rgb(COLORS['accent']))

    # Enemy health bar
    health_bar_y = enemy_y + enemy_size + 20
    health_bar_width = 200
    health_bar_x = width // 2 - health_bar_width // 2

    # Health bar background
    draw.rectangle([health_bar_x, health_bar_y, health_bar_x + health_bar_width, health_bar_y + 15],
                  fill=hex_to_rgb('#666666'))
    # Health bar fill (75% health)
    draw.rectangle([health_bar_x, health_bar_y, health_bar_x + health_bar_width * 0.75, health_bar_y + 15],
                  fill=hex_to_rgb('#4a90e2'))

    # Player monster area
    player_monster_y = height // 2 + 50
    draw.ellipse([enemy_x, player_monster_y, enemy_x + enemy_size, player_monster_y + enemy_size],
                fill=hex_to_rgb(COLORS['primary']))

    # Player health bar
    player_health_y = player_monster_y + enemy_size + 20
    draw.rectangle([health_bar_x, player_health_y, health_bar_x + health_bar_width, player_health_y + 15],
                  fill=hex_to_rgb('#666666'))
    draw.rectangle([health_bar_x, player_health_y, health_bar_x + health_bar_width * 0.9, player_health_y + 15],
                  fill=hex_to_rgb('#4a90e2'))

    # Battle controls
    controls_y = height - 150
    button_width = 80
    button_height = 35
    button_spacing = 20

    buttons = ["Attack", "Defend", "Item", "Run"]
    total_buttons_width = len(buttons) * button_width + (len(buttons) - 1) * button_spacing
    start_x = (width - total_buttons_width) // 2

    for i, button_text in enumerate(buttons):
        button_x = start_x + i * (button_width + button_spacing)

        # Button background
        draw.rectangle([button_x, controls_y, button_x + button_width, controls_y + button_height],
                      fill=hex_to_rgb(COLORS['card']), outline=hex_to_rgb(COLORS['text']))

        # Button text
        button_text_bbox = draw.textbbox((0, 0), button_text, font=small_font)
        button_text_width = button_text_bbox[2] - button_text_bbox[0]
        button_text_x = button_x + (button_width - button_text_width) // 2
        draw.text((button_text_x, controls_y + 10), button_text,
                 fill=hex_to_rgb(COLORS['text']), font=small_font)

    # Battle status text
    status_text = "Choose your move wisely!"
    status_bbox = draw.textbbox((0, 0), status_text, font=small_font)
    status_width = status_bbox[2] - status_bbox[0]
    status_x = (width - status_width) // 2
    draw.text((status_x, height - 40), status_text, fill=hex_to_rgb(COLORS['text']), font=small_font)

    return img

def save_screenshot(img, filename):
    """Save screenshot image"""
    screenshots_dir = Path(__file__).parent / 'public' / 'screenshots'
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshots_dir / filename
    img.save(screenshot_path, 'PNG')
    print(f"Generated: {filename}")

def generate_all_screenshots():
    """Generate all PWA screenshots"""
    print("Generating PWA screenshots for AI-Powered Tuxemon...")

    try:
        # Mobile gameplay screenshot
        gameplay_img = generate_mobile_gameplay_screenshot()
        save_screenshot(gameplay_img, 'mobile-gameplay.png')

        # Battle screen screenshot
        battle_img = generate_battle_screenshot()
        save_screenshot(battle_img, 'battle-screen.png')

        print("All PWA screenshots generated successfully!")
        print("\nGenerated screenshots:")
        print("  - mobile-gameplay.png (390x844)")
        print("  - battle-screen.png (390x844)")

        return True

    except Exception as e:
        print(f"Error generating screenshots: {e}")
        return False

if __name__ == "__main__":
    success = generate_all_screenshots()
    if not success:
        exit(1)