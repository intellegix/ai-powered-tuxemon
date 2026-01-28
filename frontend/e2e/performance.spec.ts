/**
 * Performance E2E Tests
 * Austin Kidwell | Intellegix | AI-Powered Tuxemon Game
 *
 * Tests focused on performance metrics, load times, and mobile optimization.
 * Validates that the game meets performance targets for mobile devices.
 */

import { test, expect, type Page } from '@playwright/test';

// Performance thresholds
const PERFORMANCE_THRESHOLDS = {
  INITIAL_LOAD_TIME: 3000,     // 3 seconds max for initial load
  INTERACTION_DELAY: 100,      // 100ms max for UI interactions
  FRAME_RATE_MIN: 30,          // Minimum 30 FPS
  MEMORY_USAGE_MAX: 200,       // 200MB max memory usage
  BUNDLE_SIZE_MAX: 1048576,    // 1MB max main bundle
};

// Helper functions
async function measurePageLoadTime(page: Page, url: string): Promise<number> {
  const startTime = Date.now();
  await page.goto(url);
  await page.waitForLoadState('networkidle');
  return Date.now() - startTime;
}

async function measureInteractionTime(page: Page, selector: string): Promise<number> {
  const startTime = Date.now();
  await page.click(selector);
  await page.waitForTimeout(50); // Allow for UI update
  return Date.now() - startTime;
}

async function getMemoryUsage(page: Page): Promise<number> {
  const metrics = await page.evaluate(() => {
    return (performance as any).memory?.usedJSHeapSize || 0;
  });
  return metrics / (1024 * 1024); // Convert to MB
}

test.describe('Performance Tests', () => {
  test('Initial Page Load Performance', async ({ page }) => {
    const loadTime = await measurePageLoadTime(page, '/');

    console.log(`Initial load time: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.INITIAL_LOAD_TIME);

    // Check for performance metrics
    const performanceEntries = await page.evaluate(() => {
      return performance.getEntriesByType('navigation').map(entry => ({
        domContentLoaded: (entry as PerformanceNavigationTiming).domContentLoadedEventEnd - (entry as PerformanceNavigationTiming).domContentLoadedEventStart,
        loadComplete: (entry as PerformanceNavigationTiming).loadEventEnd - (entry as PerformanceNavigationTiming).loadEventStart
      }));
    });

    console.log('Performance entries:', performanceEntries);
  });

  test('Game World Rendering Performance', async ({ page }) => {
    await page.goto('/');

    // Wait for game to load
    await page.waitForSelector('[data-testid="game-world"]', { timeout: 10000 });

    // Measure rendering performance
    const renderingMetrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        let frames = 0;
        let startTime = performance.now();

        const measureFrames = () => {
          frames++;
          if (frames < 60) { // Measure for 60 frames
            requestAnimationFrame(measureFrames);
          } else {
            const endTime = performance.now();
            const fps = (frames * 1000) / (endTime - startTime);
            resolve({ fps, duration: endTime - startTime, frames });
          }
        };

        requestAnimationFrame(measureFrames);
      });
    });

    console.log('Rendering metrics:', renderingMetrics);
    expect((renderingMetrics as any).fps).toBeGreaterThan(PERFORMANCE_THRESHOLDS.FRAME_RATE_MIN);
  });

  test('UI Interaction Responsiveness', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="auth-container"]');

    // Test button click responsiveness
    const buttonSelectors = [
      '[data-testid="register-button"]',
      '[data-testid="login-tab"]'
    ];

    for (const selector of buttonSelectors) {
      const element = page.locator(selector);
      if (await element.isVisible()) {
        const interactionTime = await measureInteractionTime(page, selector);
        console.log(`${selector} interaction time: ${interactionTime}ms`);
        expect(interactionTime).toBeLessThan(PERFORMANCE_THRESHOLDS.INTERACTION_DELAY);
      }
    }
  });

  test('Memory Usage During Gameplay', async ({ page }) => {
    await page.goto('/');

    // Initial memory reading
    const initialMemory = await getMemoryUsage(page);
    console.log(`Initial memory usage: ${initialMemory.toFixed(2)}MB`);

    // Register user and start game
    await page.fill('[data-testid="username-input"]', `perf_test_${Date.now()}`);
    await page.fill('[data-testid="email-input"]', `perf_test_${Date.now()}@example.com`);
    await page.fill('[data-testid="password-input"]', 'TestPassword123!');
    await page.fill('[data-testid="confirm-password-input"]', 'TestPassword123!');
    await page.click('[data-testid="register-button"]');

    await page.waitForSelector('[data-testid="game-world"]', { timeout: 10000 });

    // Memory after game load
    await page.waitForTimeout(2000); // Let game stabilize
    const gameLoadMemory = await getMemoryUsage(page);
    console.log(`Memory after game load: ${gameLoadMemory.toFixed(2)}MB`);

    // Simulate gameplay activity
    const moveButton = page.locator('[data-testid="move-up"]');
    for (let i = 0; i < 10; i++) {
      if (await moveButton.isVisible()) {
        await moveButton.click();
        await page.waitForTimeout(100);
      }
    }

    // Open and close inventory multiple times
    const inventoryButton = page.locator('[data-testid="inventory-button"]');
    for (let i = 0; i < 5; i++) {
      if (await inventoryButton.isVisible()) {
        await inventoryButton.click();
        await page.waitForTimeout(200);

        const closeButton = page.locator('[data-testid="close-inventory"]');
        if (await closeButton.isVisible()) {
          await closeButton.click();
          await page.waitForTimeout(200);
        }
      }
    }

    // Final memory reading
    const finalMemory = await getMemoryUsage(page);
    console.log(`Final memory usage: ${finalMemory.toFixed(2)}MB`);

    // Memory should not exceed threshold
    expect(finalMemory).toBeLessThan(PERFORMANCE_THRESHOLDS.MEMORY_USAGE_MAX);

    // Memory should not grow excessively during gameplay
    const memoryGrowth = finalMemory - gameLoadMemory;
    console.log(`Memory growth during gameplay: ${memoryGrowth.toFixed(2)}MB`);
    expect(memoryGrowth).toBeLessThan(50); // Should not grow more than 50MB during short gameplay
  });

  test('Bundle Size Validation', async ({ page }) => {
    // Navigate to app and check resource loading
    await page.goto('/');

    const resourceSizes = await page.evaluate(() => {
      return performance.getEntriesByType('resource').map(entry => ({
        name: entry.name,
        size: (entry as PerformanceResourceTiming).transferSize || 0,
        type: (entry as PerformanceResourceTiming).initiatorType
      })).filter(resource => resource.type === 'script' || resource.type === 'stylesheet');
    });

    console.log('Resource sizes:', resourceSizes);

    // Find main JavaScript bundle
    const mainBundle = resourceSizes.find(resource =>
      resource.name.includes('index') || resource.name.includes('main')
    );

    if (mainBundle) {
      console.log(`Main bundle size: ${(mainBundle.size / 1024).toFixed(2)}KB`);
      expect(mainBundle.size).toBeLessThan(PERFORMANCE_THRESHOLDS.BUNDLE_SIZE_MAX);
    }

    // Total JavaScript size should be reasonable
    const totalJSSize = resourceSizes
      .filter(r => r.type === 'script')
      .reduce((sum, r) => sum + r.size, 0);

    console.log(`Total JavaScript size: ${(totalJSSize / 1024).toFixed(2)}KB`);
    expect(totalJSSize).toBeLessThan(PERFORMANCE_THRESHOLDS.BUNDLE_SIZE_MAX * 2); // Allow 2MB total
  });

  test('Network Performance Under Load', async ({ page }) => {
    // Start monitoring network
    const networkLogs: any[] = [];
    page.on('response', response => {
      networkLogs.push({
        url: response.url(),
        status: response.status(),
        timing: response.timing(),
        size: response.headers()['content-length'] || 0
      });
    });

    await page.goto('/');

    // Register and play for a bit
    await page.fill('[data-testid="username-input"]', `perf_test_${Date.now()}`);
    await page.fill('[data-testid="email-input"]', `perf_test_${Date.now()}@example.com`);
    await page.fill('[data-testid="password-input"]', 'TestPassword123!');
    await page.fill('[data-testid="confirm-password-input"]', 'TestPassword123!');
    await page.click('[data-testid="register-button"]');

    await page.waitForSelector('[data-testid="game-world"]', { timeout: 10000 });

    // Wait for network activity to complete
    await page.waitForTimeout(3000);

    // Analyze network performance
    const apiCalls = networkLogs.filter(log => log.url.includes('/api/'));

    console.log(`Total network requests: ${networkLogs.length}`);
    console.log(`API calls: ${apiCalls.length}`);

    // Check API response times
    for (const call of apiCalls) {
      if (call.timing && call.timing.responseEnd) {
        const responseTime = call.timing.responseEnd - call.timing.requestStart;
        console.log(`${call.url}: ${responseTime}ms`);

        // API calls should be under 1 second
        expect(responseTime).toBeLessThan(1000);
      }
    }
  });

  test('Performance on Slow Network', async ({ page, context }) => {
    // Simulate slow 3G network
    await context.route('**/*', async route => {
      // Add 200ms delay for all requests
      await new Promise(resolve => setTimeout(resolve, 200));
      route.continue();
    });

    const startTime = Date.now();
    await page.goto('/');
    await page.waitForSelector('[data-testid="auth-container"]');
    const loadTime = Date.now() - startTime;

    console.log(`Load time on slow network: ${loadTime}ms`);

    // Should still load within reasonable time on slow network
    expect(loadTime).toBeLessThan(8000); // 8 seconds max on slow network

    // App should remain usable
    await page.fill('[data-testid="username-input"]', `slow_test_${Date.now()}`);
    await page.fill('[data-testid="email-input"]', `slow_test_${Date.now()}@example.com`);
    await page.fill('[data-testid="password-input"]', 'TestPassword123!');

    const interactionStartTime = Date.now();
    await page.fill('[data-testid="confirm-password-input"]', 'TestPassword123!');
    const interactionTime = Date.now() - interactionStartTime;

    // Local interactions should still be fast
    expect(interactionTime).toBeLessThan(500);
  });

  test('PWA Performance Metrics', async ({ page }) => {
    await page.goto('/');

    // Check for PWA performance indicators
    const pwaMetrics = await page.evaluate(() => {
      const metrics = {
        hasServiceWorker: 'serviceWorker' in navigator,
        hasManifest: !!document.querySelector('link[rel="manifest"]'),
        isStandalone: window.matchMedia('(display-mode: standalone)').matches,
        isInstallable: false
      };

      // Check for beforeinstallprompt
      window.addEventListener('beforeinstallprompt', () => {
        metrics.isInstallable = true;
      });

      return metrics;
    });

    console.log('PWA metrics:', pwaMetrics);

    // PWA features should be present
    expect(pwaMetrics.hasServiceWorker).toBe(true);
    expect(pwaMetrics.hasManifest).toBe(true);
  });

  test('First Contentful Paint Performance', async ({ page }) => {
    await page.goto('/');

    const paintMetrics = await page.evaluate(() => {
      const perfEntries = performance.getEntriesByType('paint');
      const fcp = perfEntries.find(entry => entry.name === 'first-contentful-paint');
      const fp = perfEntries.find(entry => entry.name === 'first-paint');

      return {
        firstPaint: fp ? fp.startTime : 0,
        firstContentfulPaint: fcp ? fcp.startTime : 0
      };
    });

    console.log('Paint metrics:', paintMetrics);

    // First Contentful Paint should be under 2 seconds
    if (paintMetrics.firstContentfulPaint > 0) {
      expect(paintMetrics.firstContentfulPaint).toBeLessThan(2000);
    }
  });

  test('Mobile Performance Validation', async ({ page }) => {
    // Set mobile viewport and user agent
    await page.setViewportSize({ width: 393, height: 851 });
    await page.setExtraHTTPHeaders({
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
    });

    const startTime = Date.now();
    await page.goto('/');
    await page.waitForSelector('[data-testid="auth-container"]');
    const mobileLoadTime = Date.now() - startTime;

    console.log(`Mobile load time: ${mobileLoadTime}ms`);

    // Mobile should load within 3 seconds
    expect(mobileLoadTime).toBeLessThan(3000);

    // Check touch target sizes
    const buttons = await page.locator('button').all();
    for (const button of buttons.slice(0, 5)) { // Check first 5 buttons
      const boundingBox = await button.boundingBox();
      if (boundingBox) {
        expect(boundingBox.width).toBeGreaterThanOrEqual(44); // iOS minimum touch target
        expect(boundingBox.height).toBeGreaterThanOrEqual(44);
      }
    }

    // Test scroll performance on mobile
    const scrollContainer = page.locator('body');
    const scrollStart = Date.now();

    await scrollContainer.evaluate(el => {
      el.scrollTo({ top: 200, behavior: 'smooth' });
    });

    await page.waitForTimeout(500); // Allow scroll to complete
    const scrollTime = Date.now() - scrollStart;

    console.log(`Scroll time: ${scrollTime}ms`);
    expect(scrollTime).toBeLessThan(600); // Smooth scrolling should complete quickly
  });
});