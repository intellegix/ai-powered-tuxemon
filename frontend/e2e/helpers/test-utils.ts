/**
 * E2E Test Utilities
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Shared utilities and helpers for E2E testing.
 */

import { type Page, type Locator } from '@playwright/test';

export interface TestUser {
  username: string;
  email: string;
  password: string;
}

export interface GameState {
  player: {
    position: { x: number; y: number };
    level: number;
    currentMap: string;
  };
  inventory: {
    items: any[];
    capacity: number;
  };
}

/**
 * Generate a unique test user
 */
export function createTestUser(): TestUser {
  const timestamp = Date.now();
  return {
    username: `e2e_user_${timestamp}`,
    email: `e2e_test_${timestamp}@example.com`,
    password: 'TestPassword123!'
  };
}

/**
 * Register a new test user
 */
export async function registerUser(page: Page, user: TestUser): Promise<void> {
  await page.goto('/auth/register');
  await page.fill('[data-testid="username-input"]', user.username);
  await page.fill('[data-testid="email-input"]', user.email);
  await page.fill('[data-testid="password-input"]', user.password);
  await page.fill('[data-testid="confirm-password-input"]', user.password);
  await page.click('[data-testid="register-button"]');
}

/**
 * Login with existing user credentials
 */
export async function loginUser(page: Page, user: TestUser): Promise<void> {
  await page.goto('/auth/login');
  await page.fill('[data-testid="username-input"]', user.username);
  await page.fill('[data-testid="password-input"]', user.password);
  await page.click('[data-testid="login-button"]');
}

/**
 * Wait for game world to be ready
 */
export async function waitForGameReady(page: Page, timeout = 10000): Promise<void> {
  await page.waitForSelector('[data-testid="game-world"]', { timeout });
  await page.waitForSelector('[data-testid="player-avatar"]', { timeout });

  // Wait for loading states to complete
  await page.waitForFunction(() => {
    const loadingElement = document.querySelector('[data-testid="loading-screen"]');
    return !loadingElement || loadingElement.style.display === 'none';
  }, { timeout });
}

/**
 * Perform mobile swipe gesture
 */
export async function swipe(
  page: Page,
  element: Locator,
  direction: 'up' | 'down' | 'left' | 'right',
  distance = 100
): Promise<void> {
  const box = await element.boundingBox();
  if (!box) throw new Error('Element not found for swipe');

  const startX = box.x + box.width / 2;
  const startY = box.y + box.height / 2;

  let endX = startX;
  let endY = startY;

  switch (direction) {
    case 'up':
      endY = startY - distance;
      break;
    case 'down':
      endY = startY + distance;
      break;
    case 'left':
      endX = startX - distance;
      break;
    case 'right':
      endX = startX + distance;
      break;
  }

  await page.touchscreen.tap(startX, startY);
  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(endX, endY);
  await page.mouse.up();
}

/**
 * Simulate mobile device orientation change
 */
export async function changeOrientation(
  page: Page,
  orientation: 'portrait' | 'landscape'
): Promise<void> {
  const currentViewport = page.viewportSize();
  if (!currentViewport) return;

  if (orientation === 'landscape') {
    await page.setViewportSize({
      width: Math.max(currentViewport.width, currentViewport.height),
      height: Math.min(currentViewport.width, currentViewport.height)
    });
  } else {
    await page.setViewportSize({
      width: Math.min(currentViewport.width, currentViewport.height),
      height: Math.max(currentViewport.width, currentViewport.height)
    });
  }

  // Trigger orientation change event
  await page.evaluate(() => {
    window.dispatchEvent(new Event('orientationchange'));
  });
}

/**
 * Measure performance timing
 */
export async function measurePerformance(page: Page, action: () => Promise<void>): Promise<{
  duration: number;
  memoryUsed: number;
}> {
  const startTime = Date.now();
  const startMemory = await page.evaluate(() => {
    return (performance as any).memory?.usedJSHeapSize || 0;
  });

  await action();

  const endTime = Date.now();
  const endMemory = await page.evaluate(() => {
    return (performance as any).memory?.usedJSHeapSize || 0;
  });

  return {
    duration: endTime - startTime,
    memoryUsed: (endMemory - startMemory) / (1024 * 1024) // Convert to MB
  };
}

/**
 * Check if element is within mobile touch target guidelines (44px minimum)
 */
export async function validateTouchTarget(element: Locator): Promise<boolean> {
  const box = await element.boundingBox();
  if (!box) return false;

  return box.width >= 44 && box.height >= 44;
}

/**
 * Wait for network idle (useful for API-dependent tests)
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Mock network conditions
 */
export async function mockSlowNetwork(page: Page, delay = 200): Promise<void> {
  await page.route('**/*', async (route) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    await route.continue();
  });
}

/**
 * Get game state from local storage or API
 */
export async function getGameState(page: Page): Promise<GameState | null> {
  return await page.evaluate(() => {
    try {
      const gameState = localStorage.getItem('gameState');
      return gameState ? JSON.parse(gameState) : null;
    } catch {
      return null;
    }
  });
}

/**
 * Clear all game data (useful for test cleanup)
 */
export async function clearGameData(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();

    // Clear IndexedDB if used
    if ('indexedDB' in window) {
      indexedDB.databases?.().then(databases => {
        databases.forEach(db => {
          if (db.name?.includes('tuxemon')) {
            indexedDB.deleteDatabase(db.name);
          }
        });
      });
    }
  });
}

/**
 * Take a screenshot with mobile device frame (for debugging)
 */
export async function takeDeviceScreenshot(
  page: Page,
  name: string,
  deviceType = 'mobile'
): Promise<void> {
  await page.screenshot({
    path: `test-results/screenshots/${deviceType}-${name}-${Date.now()}.png`,
    fullPage: true
  });
}

/**
 * Simulate app going to background and returning (for PWA testing)
 */
export async function simulateAppBackgroundCycle(page: Page): Promise<void> {
  // Simulate visibility change
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { value: true, writable: true });
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', writable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });

  await page.waitForTimeout(1000);

  // Return to foreground
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { value: false, writable: true });
    Object.defineProperty(document, 'visibilityState', { value: 'visible', writable: true });
    document.dispatchEvent(new Event('visibilitychange'));
  });
}

/**
 * Check PWA installation readiness
 */
export async function checkPWAFeatures(page: Page): Promise<{
  hasManifest: boolean;
  hasServiceWorker: boolean;
  isInstallable: boolean;
}> {
  return await page.evaluate(() => {
    return {
      hasManifest: !!document.querySelector('link[rel="manifest"]'),
      hasServiceWorker: 'serviceWorker' in navigator,
      isInstallable: !!(window as any).beforeinstallprompt
    };
  });
}

/**
 * Validate accessibility features
 */
export async function checkAccessibilityFeatures(page: Page): Promise<{
  hasAriaLabels: boolean;
  hasTabIndices: boolean;
  hasAltText: boolean;
}> {
  return await page.evaluate(() => {
    const elementsWithAria = document.querySelectorAll('[aria-label], [aria-labelledby]');
    const elementsWithTabIndex = document.querySelectorAll('[tabindex]');
    const imagesWithAlt = document.querySelectorAll('img[alt]');
    const totalImages = document.querySelectorAll('img');

    return {
      hasAriaLabels: elementsWithAria.length > 0,
      hasTabIndices: elementsWithTabIndex.length > 0,
      hasAltText: totalImages.length === 0 || imagesWithAlt.length === totalImages.length
    };
  });
}

/**
 * Generate test data for inventory/items
 */
export function generateTestInventory() {
  return {
    items: [
      {
        id: 'test_potion_1',
        slug: 'health_potion',
        name: 'Health Potion',
        quantity: 5,
        category: 'healing'
      },
      {
        id: 'test_ball_1',
        slug: 'tuxeball',
        name: 'Tuxe Ball',
        quantity: 10,
        category: 'capture'
      }
    ],
    capacity: 50,
    usedSlots: 2
  };
}

/**
 * Generate test NPC data
 */
export function generateTestNPC() {
  return {
    id: 'test_npc_1',
    name: 'Test Trainer Alice',
    position: { x: 10, y: 15 },
    dialogue: [
      'Hello there, trainer!',
      'How are your monsters doing?',
      'Would you like to battle?'
    ]
  };
}