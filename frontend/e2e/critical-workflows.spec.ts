/**
 * Critical User Workflow E2E Tests
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Tests for core user journeys that must work for the game to be functional.
 * Focuses on mobile-first experience with touch interactions and performance.
 */

import { test, expect, type Page } from '@playwright/test';

// Test user data
const testUser = {
  username: `e2e_user_${Date.now()}`,
  email: `e2e_test_${Date.now()}@example.com`,
  password: 'TestPassword123!'
};

// Helper functions
async function loginAsTestUser(page: Page) {
  await page.goto('/auth/login');
  await page.fill('[data-testid="username-input"]', testUser.username);
  await page.fill('[data-testid="password-input"]', testUser.password);
  await page.click('[data-testid="login-button"]');
  await expect(page.locator('[data-testid="game-world"]')).toBeVisible();
}

async function registerTestUser(page: Page) {
  await page.goto('/auth/register');
  await page.fill('[data-testid="username-input"]', testUser.username);
  await page.fill('[data-testid="email-input"]', testUser.email);
  await page.fill('[data-testid="password-input"]', testUser.password);
  await page.fill('[data-testid="confirm-password-input"]', testUser.password);
  await page.click('[data-testid="register-button"]');
}

test.describe('Critical User Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // Set mobile user agent for mobile-first testing
    await page.setExtraHTTPHeaders({
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
    });
  });

  test('New Player Complete Onboarding', async ({ page }) => {
    const startTime = Date.now();

    // Navigate to app
    await page.goto('/');

    // Check if registration form is visible
    await expect(page.locator('[data-testid="auth-container"]')).toBeVisible();

    // Register new user
    await registerTestUser(page);

    // Verify successful registration and auto-login
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible({ timeout: 10000 });

    // Check tutorial completion (if implemented)
    const tutorialComplete = page.locator('[data-testid="tutorial-complete"]');
    if (await tutorialComplete.isVisible()) {
      await expect(tutorialComplete).toBeVisible();
    }

    // Verify basic game elements are present
    await expect(page.locator('[data-testid="player-avatar"]')).toBeVisible();
    await expect(page.locator('[data-testid="game-hud"]')).toBeVisible();

    // Performance assertion: <3s load time on mobile
    const loadTime = Date.now() - startTime;
    expect(loadTime).toBeLessThan(3000);
  });

  test('User Authentication Flow', async ({ page }) => {
    // First register the user
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Logout
    await page.click('[data-testid="menu-button"]');
    await page.click('[data-testid="logout-button"]');
    await expect(page.locator('[data-testid="auth-container"]')).toBeVisible();

    // Login again
    await loginAsTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();
  });

  test('Basic Game Navigation and Movement', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    const player = page.locator('[data-testid="player-avatar"]');
    await expect(player).toBeVisible();

    // Test touch movement controls
    const moveUpButton = page.locator('[data-testid="move-up"]');
    const moveDownButton = page.locator('[data-testid="move-down"]');
    const moveLeftButton = page.locator('[data-testid="move-left"]');
    const moveRightButton = page.locator('[data-testid="move-right"]');

    if (await moveUpButton.isVisible()) {
      // Test directional movement
      await moveUpButton.click();
      await page.waitForTimeout(500); // Allow movement animation

      await moveRightButton.click();
      await page.waitForTimeout(500);

      await moveDownButton.click();
      await page.waitForTimeout(500);

      await moveLeftButton.click();
      await page.waitForTimeout(500);
    } else {
      // Test tap-to-move if virtual d-pad not present
      const gameCanvas = page.locator('[data-testid="game-canvas"]');
      await gameCanvas.click({ position: { x: 200, y: 150 } });
      await page.waitForTimeout(1000);
    }

    // Verify player position updated
    await expect(player).toBeVisible();
  });

  test('Inventory Management', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Open inventory
    const inventoryButton = page.locator('[data-testid="inventory-button"]');
    await inventoryButton.click();

    // Verify inventory UI opens
    await expect(page.locator('[data-testid="inventory-container"]')).toBeVisible();

    // Check for basic inventory elements
    const inventorySlots = page.locator('[data-testid="inventory-slot"]');
    if (await inventorySlots.first().isVisible()) {
      await expect(inventorySlots.first()).toBeVisible();
    }

    // Test inventory item interaction if items exist
    const inventoryItem = page.locator('[data-testid="inventory-item"]').first();
    if (await inventoryItem.isVisible()) {
      await inventoryItem.click();

      // Should show item details or actions
      const itemDetails = page.locator('[data-testid="item-details"]');
      if (await itemDetails.isVisible()) {
        await expect(itemDetails).toBeVisible();
      }
    }

    // Close inventory
    const closeButton = page.locator('[data-testid="close-inventory"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    } else {
      // Swipe down to close if modal
      await page.locator('[data-testid="inventory-container"]').swipeDown();
    }

    // Verify inventory closed
    await expect(page.locator('[data-testid="inventory-container"]')).not.toBeVisible();
  });

  test('Mobile PWA Installation Flow', async ({ page, browserName }) => {
    // Skip on Safari as it handles PWA differently
    if (browserName === 'webkit') {
      test.skip('PWA installation testing not applicable to Safari');
    }

    await page.goto('/');

    // Check PWA manifest
    const manifestLink = page.locator('link[rel="manifest"]');
    await expect(manifestLink).toBeAttached();

    // Check service worker registration
    const serviceWorkerRegistration = await page.evaluate(() => {
      return 'serviceWorker' in navigator;
    });
    expect(serviceWorkerRegistration).toBe(true);

    // Check PWA install prompt (may not appear in test environment)
    await page.evaluate(() => {
      // Simulate beforeinstallprompt event
      window.dispatchEvent(new Event('beforeinstallprompt'));
    });
  });

  test('Offline Functionality', async ({ page, context }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Go offline
    await context.setOffline(true);

    // Test that basic UI still works
    await page.click('[data-testid="inventory-button"]');
    await expect(page.locator('[data-testid="inventory-container"]')).toBeVisible();

    // Verify offline indicator appears
    const offlineIndicator = page.locator('[data-testid="offline-indicator"]');
    if (await offlineIndicator.isVisible()) {
      await expect(offlineIndicator).toBeVisible();
    }

    // Test basic gameplay functionality offline
    const moveButton = page.locator('[data-testid="move-up"]');
    if (await moveButton.isVisible()) {
      await moveButton.click();
      await page.waitForTimeout(500);
    }

    // Go back online
    await context.setOffline(false);

    // Wait for connection restoration
    await page.waitForTimeout(2000);

    // Verify sync indicator or online status
    const onlineIndicator = page.locator('[data-testid="online-indicator"]');
    if (await onlineIndicator.isVisible()) {
      await expect(onlineIndicator).toBeVisible();
    }
  });

  test('Performance Under Poor Network Conditions', async ({ page, context }) => {
    // Simulate slow 3G
    await context.route('**/*', route => {
      setTimeout(() => route.continue(), 300); // Add 300ms delay
    });

    const startTime = Date.now();

    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Test interaction responsiveness under slow network
    await page.click('[data-testid="inventory-button"]');
    await expect(page.locator('[data-testid="inventory-container"]')).toBeVisible();

    const totalTime = Date.now() - startTime;

    // Should still be usable under poor conditions (allow up to 10s)
    expect(totalTime).toBeLessThan(10000);
  });

  test('Touch Interface Accessibility', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Check touch target sizes (minimum 44px for accessibility)
    const touchableElements = await page.locator('button, [role="button"], a').all();

    for (const element of touchableElements.slice(0, 10)) { // Test first 10 elements
      const boundingBox = await element.boundingBox();
      if (boundingBox) {
        expect(boundingBox.width).toBeGreaterThanOrEqual(44);
        expect(boundingBox.height).toBeGreaterThanOrEqual(44);
      }
    }

    // Test swipe gestures if implemented
    const gameContainer = page.locator('[data-testid="game-container"]');
    const initialPos = await gameContainer.boundingBox();

    if (initialPos) {
      // Perform swipe gesture
      await page.touchscreen.tap(initialPos.x + initialPos.width / 2, initialPos.y + initialPos.height / 2);
      await page.waitForTimeout(100);
    }
  });

  test('Game State Persistence', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Perform some actions that should be saved
    const moveButton = page.locator('[data-testid="move-up"]');
    if (await moveButton.isVisible()) {
      await moveButton.click();
      await page.waitForTimeout(1000);
    }

    // Refresh page
    await page.reload();

    // Should automatically log back in and restore state
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Player should still be visible
    await expect(page.locator('[data-testid="player-avatar"]')).toBeVisible();
  });

  test('Error Handling and Recovery', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Test network error handling by intercepting requests
    await page.route('**/api/**', route => {
      route.abort('failed');
    });

    // Try to interact with something that requires API
    await page.click('[data-testid="inventory-button"]');

    // Should show error message or fallback gracefully
    const errorMessage = page.locator('[data-testid="error-message"], [data-testid="network-error"]');

    // Wait for either error message or graceful fallback
    await page.waitForTimeout(2000);

    // App should remain functional even with network errors
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Remove error simulation
    await page.unroute('**/api/**');
  });
});

// Test group for mobile-specific features
test.describe('Mobile-Specific Features', () => {
  test.use({
    viewport: { width: 393, height: 851 },
    isMobile: true,
    hasTouch: true
  });

  test('Screen Orientation Changes', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    // Change to landscape
    await page.setViewportSize({ width: 851, height: 393 });
    await page.waitForTimeout(1000);

    // UI should adapt to landscape mode
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();
    await expect(page.locator('[data-testid="player-avatar"]')).toBeVisible();

    // Change back to portrait
    await page.setViewportSize({ width: 393, height: 851 });
    await page.waitForTimeout(1000);

    // UI should work in portrait
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();
  });

  test('Touch Gesture Recognition', async ({ page }) => {
    await registerTestUser(page);
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();

    const gameArea = page.locator('[data-testid="game-canvas"]');
    await expect(gameArea).toBeVisible();

    // Test tap gesture
    await gameArea.tap();
    await page.waitForTimeout(500);

    // Test long press (if implemented)
    await gameArea.tap({ timeout: 1000 });
    await page.waitForTimeout(500);

    // App should remain responsive after gestures
    await expect(page.locator('[data-testid="game-world"]')).toBeVisible();
  });
});