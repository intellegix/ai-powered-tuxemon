#!/usr/bin/env node
/**
 * Generate PWA icons for AI-Powered Tuxemon
 * Creates basic but professional icons for all required sizes
 */

const fs = require('fs');
const path = require('path');
const { createCanvas } = require('canvas');

// Icon sizes required by manifest.json
const ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512];

// Game colors (matching theme)
const COLORS = {
  background: '#1a202c',  // Dark background
  primary: '#4299e1',     // Blue theme color
  accent: '#38b2ac',      // Teal accent
  text: '#ffffff'         // White text
};

/**
 * Generate a game-themed icon using HTML5 Canvas
 */
function generateIcon(size) {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Background circle
  ctx.fillStyle = COLORS.background;
  ctx.fillRect(0, 0, size, size);

  // Outer ring
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.45, 0, 2 * Math.PI);
  ctx.fillStyle = COLORS.primary;
  ctx.fill();

  // Inner circle
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.35, 0, 2 * Math.PI);
  ctx.fillStyle = COLORS.background;
  ctx.fill();

  // Game controller/monster ball design
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.25, 0, 2 * Math.PI);
  ctx.fillStyle = COLORS.accent;
  ctx.fill();

  // Central dot (like a Pokéball)
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size * 0.08, 0, 2 * Math.PI);
  ctx.fillStyle = COLORS.text;
  ctx.fill();

  // Horizontal line through center (Pokéball style)
  ctx.strokeStyle = COLORS.text;
  ctx.lineWidth = size * 0.03;
  ctx.beginPath();
  ctx.moveTo(size * 0.25, size / 2);
  ctx.lineTo(size * 0.75, size / 2);
  ctx.stroke();

  return canvas;
}

/**
 * Generate shortcut icons
 */
function generateShortcutIcon(size, type = 'battle') {
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext('2d');

  // Background
  ctx.fillStyle = type === 'battle' ? '#e53e3e' : '#38b2ac';
  ctx.fillRect(0, 0, size, size);

  // Simple icon shape
  if (type === 'battle') {
    // Battle sword icon
    ctx.fillStyle = COLORS.text;
    const centerX = size / 2;
    const centerY = size / 2;
    const swordLength = size * 0.6;

    ctx.fillRect(centerX - 2, centerY - swordLength / 2, 4, swordLength);
    ctx.fillRect(centerX - 8, centerY - swordLength / 2 + 10, 16, 6);
  } else {
    // Chat bubble icon
    ctx.fillStyle = COLORS.text;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 4, size * 0.3, 0, 2 * Math.PI);
    ctx.fill();

    // Chat tail
    ctx.beginPath();
    ctx.moveTo(size / 2 - 8, size / 2 + 8);
    ctx.lineTo(size / 2, size / 2 + 16);
    ctx.lineTo(size / 2 + 8, size / 2 + 8);
    ctx.fill();
  }

  return canvas;
}

/**
 * Save canvas as PNG file
 */
function saveIcon(canvas, filename) {
  const iconPath = path.join(__dirname, 'public', 'icons', filename);
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(iconPath, buffer);
  console.log(`Generated: ${filename}`);
}

/**
 * Generate all required icons
 */
function generateAllIcons() {
  console.log('🎮 Generating PWA icons for AI-Powered Tuxemon...');

  // Main app icons
  ICON_SIZES.forEach(size => {
    const canvas = generateIcon(size);
    saveIcon(canvas, `icon-${size}x${size}.png`);
  });

  // Shortcut icons
  const battleIcon = generateShortcutIcon(96, 'battle');
  saveIcon(battleIcon, 'battle-shortcut.png');

  const chatIcon = generateShortcutIcon(96, 'chat');
  saveIcon(chatIcon, 'chat-shortcut.png');

  console.log('✅ All PWA icons generated successfully!');
  console.log('\nGenerated icons:');
  ICON_SIZES.forEach(size => {
    console.log(`  - icon-${size}x${size}.png`);
  });
  console.log('  - battle-shortcut.png');
  console.log('  - chat-shortcut.png');
}

/**
 * Check if canvas package is available
 */
function checkDependencies() {
  try {
    require('canvas');
    return true;
  } catch (error) {
    console.log('❌ Canvas package not found. Installing...');
    return false;
  }
}

// Main execution
if (require.main === module) {
  if (!checkDependencies()) {
    console.log('Please install canvas package:');
    console.log('npm install canvas');
    console.log('\nOr run: npm run generate-icons (if canvas is in devDependencies)');
    process.exit(1);
  }

  generateAllIcons();
}

module.exports = { generateAllIcons, generateIcon, generateShortcutIcon };