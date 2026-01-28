# E2E Testing Suite for AI-Powered Tuxemon

This directory contains end-to-end tests for the AI-Powered Tuxemon mobile game, focusing on mobile-first user experiences and performance validation.

## Test Structure

### Core Test Files

- `critical-workflows.spec.ts` - Essential user journeys that must work for the game to be functional
- `performance.spec.ts` - Performance tests validating mobile optimization and load times
- `helpers/test-utils.ts` - Shared utilities and helper functions for E2E testing

### Test Categories

#### Critical Workflows
- New player onboarding and registration
- User authentication flow
- Basic game navigation and movement
- Inventory management
- Mobile PWA functionality
- Offline capabilities
- Performance under poor network conditions
- Touch interface accessibility
- Game state persistence
- Error handling and recovery

#### Performance Tests
- Initial page load performance (<3s target)
- Game world rendering performance (>30 FPS)
- UI interaction responsiveness (<100ms)
- Memory usage during gameplay (<200MB)
- Bundle size validation (<1MB main bundle)
- Network performance under load
- Mobile-specific performance metrics
- PWA performance indicators

## Mobile-First Testing

All tests are designed with mobile-first principles:

### Device Configurations
- **Primary**: Mobile Chrome (Pixel 5) - 393x851 viewport
- **Secondary**: Mobile Safari (iPhone 12) - 390x844 viewport
- **Landscape**: Mobile landscape modes for orientation testing
- **Desktop**: Chrome, Firefox, Safari for cross-platform validation

### Mobile-Specific Features Tested
- Touch target sizes (44px minimum for accessibility)
- Swipe gestures and touch interactions
- Screen orientation changes
- PWA installation and offline functionality
- Mobile performance under various network conditions
- Battery efficiency simulation

## Performance Thresholds

### Load Time Targets
- Initial page load: <3 seconds
- UI interactions: <100ms response time
- API calls: <1 second response time

### Resource Targets
- Memory usage: <200MB during gameplay
- Main bundle size: <1MB
- Frame rate: >30 FPS sustained
- Total JavaScript: <2MB

### Network Conditions Tested
- Fast WiFi (baseline)
- 4G mobile network
- Slow 3G network (300ms latency)
- Offline mode with service worker

## Running Tests

### Prerequisites
```bash
cd frontend
npm install
npm install --save-dev @playwright/test
npx playwright install
```

### Run All E2E Tests
```bash
# Run all tests
npm run test:e2e

# Run specific test file
npx playwright test critical-workflows.spec.ts

# Run performance tests only
npx playwright test performance.spec.ts

# Run tests with UI (for debugging)
npx playwright test --ui

# Run tests in headed mode
npx playwright test --headed
```

### Run on Specific Devices
```bash
# Run on mobile Chrome only
npx playwright test --project="Mobile Chrome"

# Run on mobile Safari only
npx playwright test --project="Mobile Safari"

# Run performance tests
npx playwright test --project="Performance Testing"
```

### Generate Test Report
```bash
# Run tests and generate HTML report
npx playwright test --reporter=html

# View report
npx playwright show-report
```

## Test Environment Setup

### Local Testing
1. Start backend API server on port 8000
2. Start frontend dev server on port 5173
3. Ensure database and Redis are running for full functionality

### CI/CD Testing
Tests are automatically run in GitHub Actions with:
- Docker containers for backend services
- Simulated mobile devices
- Network condition simulation
- Performance benchmarking

### Docker Testing
```bash
# Start full test environment
docker-compose -f docker-compose.test.yml up -d

# Run E2E tests against Docker environment
PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run test:e2e
```

## Test Data Management

### Test Users
- Auto-generated unique usernames for each test run
- Isolated test data to prevent conflicts
- Automatic cleanup after tests complete

### Mock Data
- Predefined inventory items for testing
- Mock NPC interactions
- Simulated game state data

## Debugging Tests

### Screenshots and Videos
- Automatic screenshots on test failure
- Video recordings for debugging
- Device-specific screenshots for mobile testing

### Network Debugging
- Request/response logging
- Performance timing analysis
- Network condition simulation

### Mobile-Specific Debugging
- Touch interaction visualization
- Viewport size validation
- Device orientation testing

## Performance Monitoring

### Metrics Tracked
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Time to Interactive (TTI)
- Memory usage patterns
- Network request performance

### Mobile Performance
- Touch target accessibility
- Battery usage simulation
- Frame rate monitoring
- Bundle size optimization

## Integration with CI/CD

E2E tests are integrated into the GitHub Actions workflow:

1. **Pre-deployment Validation**: Run critical workflows before deployment
2. **Performance Regression Testing**: Ensure performance doesn't degrade
3. **Mobile Compatibility**: Validate across different mobile devices
4. **PWA Functionality**: Test offline capabilities and installation

## Best Practices

### Writing Tests
- Use mobile-first selectors (data-testid attributes)
- Test touch interactions, not just clicks
- Validate accessibility features
- Test performance, not just functionality

### Maintenance
- Update test data generators as features evolve
- Review performance thresholds regularly
- Keep device configurations current
- Monitor test execution times

### Debugging
- Use headed mode for visual debugging
- Check network logs for API issues
- Validate mobile viewport settings
- Review console logs for JavaScript errors

## Future Enhancements

### Planned Test Additions
- AI NPC interaction testing
- Real-time multiplayer scenarios
- Advanced mobile gesture recognition
- Voice interface testing (when implemented)
- AR/VR compatibility testing (future features)

### Performance Improvements
- Parallel test execution optimization
- Visual regression testing
- Automated accessibility scanning
- Real device testing integration