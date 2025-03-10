# Tests for the SAP Test Harness

This directory contains tests for the SAP Test Harness components.

## Test Types

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test how components work together
3. **Visual Tests**: Manual verification of UI elements

## Running the Tests

To run the tests, use pytest:

```bash
# From the project root directory
python -m pytest tests/
```

## Test Files

- `test_url_service.py`: Tests for the URL Service
- `test_template_service.py`: Tests for the Template Service
- `test_dashboard_controller.py`: Tests for the Dashboard Controller
- `test_integration.py`: Integration tests for the application

## Manual Testing Checklist

After implementing the URL Service, verify the following manually:

1. **Basic Functionality**:
   - [ ] Visit the root URL `/` and verify it redirects to `/dashboard`
   - [ ] Check that the dashboard shows "Current page URL: /dashboard"

2. **Edge Cases**:
   - [ ] Try adding a route with parameters to `meta_routes.py` temporarily and test URL generation
   - [ ] Use the browser developer tools to see if any JavaScript errors occur

3. **Visual Verification**:
   - [ ] Check the dashboard renders correctly with no layout issues
   - [ ] Verify all content is visible and properly formatted
