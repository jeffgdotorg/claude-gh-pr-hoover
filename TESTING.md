# Testing Guide

## Overview

This project includes a comprehensive test suite with coverage for all API endpoints, error handling, and edge cases.

## Test Structure

- **test_app.py** - Main test file containing all test cases
- **pytest.ini** - Pytest configuration
- **.coveragerc** - Coverage configuration
- **requirements-dev.txt** - Testing dependencies

## Test Coverage

### Endpoints Tested

1. **Health Check** (`/health`)
   - Basic health check functionality

2. **List Merged PRs** (`/api/v1/merged-prs`)
   - JSON, YAML, and CSV output formats
   - Missing parameters
   - Invalid timestamps
   - Invalid time ranges
   - GitHub API errors
   - Empty result sets

3. **Get PR Count** (`/api/v1/merged-prs/count`)
   - Text/plain output (default)
   - JSON output
   - YAML output
   - CSV rejection (not supported)
   - Zero results

4. **Get PR Reviewers** (`/api/v1/merged-prs/{org}/{repo}/{prId}/reviewers`)
   - Success cases
   - Empty reviewer lists
   - PR not found (404)
   - GitHub API errors
   - Network errors

### Service Layer Tests

- **GitHubService**
  - PR retrieval with pagination
  - Reviewer deduplication
  - Timeout handling
  - Connection errors
  - Missing authentication token

### Data Formatting Tests

- **DataFormatter**
  - JSON formatting
  - YAML formatting
  - CSV formatting with empty/populated data

### Error Handling Tests

- 404 errors
- 500 errors
- GitHub API unavailability
- Network failures
- Invalid input validation

## Running Tests Locally

### Basic Test Run
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with verbose output
pytest -v
```

### Coverage Reports
```bash
# Terminal coverage report
pytest --cov=. --cov-report=term-missing

# HTML coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# XML coverage report (for CI)
pytest --cov=. --cov-report=xml
```

### Running Specific Tests
```bash
# Run specific test file
pytest test_app.py

# Run specific test class
pytest test_app.py::TestMergedPRsEndpoint

# Run specific test method
pytest test_app.py::TestMergedPRsEndpoint::test_get_merged_prs_json

# Run tests matching a pattern
pytest -k "test_github"
```

### Debug Mode
```bash
# Show print statements and full output
pytest -s

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l
```

## GitHub Actions Integration

Tests run automatically on:
- Push to `main` or `master` branch
- Pull requests to `main` or `master` branch

### Workflow Configuration

File: `.github/workflows/test.yml`

**Features:**
- Runs on Python 3.11 and 3.12
- Caches pip dependencies for faster runs
- Generates coverage reports
- Uploads to Codecov (optional)
- Enforces 80% coverage threshold

### Viewing Test Results

1. Navigate to the **Actions** tab in your GitHub repository
2. Select the workflow run
3. View test results and coverage report

### Adding Codecov (Optional)

1. Sign up at [codecov.io](https://codecov.io)
2. Add your repository
3. Add `CODECOV_TOKEN` to repository secrets
4. Coverage badges will be available in Codecov dashboard

## Writing New Tests

### Test File Organization

```python
class TestNewFeature:
    """Tests for new feature."""

    def test_success_case(self, client):
        """Test successful operation."""
        response = client.get('/api/v1/new-endpoint')
        assert response.status_code == 200

    def test_error_case(self, client):
        """Test error handling."""
        response = client.get('/api/v1/new-endpoint?invalid=param')
        assert response.status_code == 400
```

### Mocking GitHub API

```python
@patch('github_service.GitHubService.get_merged_prs')
def test_with_mock(self, mock_get_prs, client):
    """Test with mocked GitHub API."""
    mock_get_prs.return_value = [{'data': 'test'}]

    response = client.get('/api/v1/merged-prs?...')
    assert response.status_code == 200
```

### Testing Error Conditions

```python
@patch('github_service.GitHubService.get_merged_prs')
def test_github_unavailable(self, mock_get_prs, client):
    """Test when GitHub API is down."""
    mock_get_prs.side_effect = ConnectionError('API unavailable')

    response = client.get('/api/v1/merged-prs?...')
    assert response.status_code == 500
```

## Coverage Goals

- **Target:** 80% minimum coverage
- **Current areas:** All endpoints, error handlers, formatters
- **Excluded:** Configuration files, venv, deployment files

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

1. **Fast execution** - Most tests complete in < 1 second
2. **No external dependencies** - All GitHub API calls are mocked
3. **Deterministic** - Tests produce consistent results
4. **Informative failures** - Clear error messages and stack traces

## Troubleshooting

### Tests Fail Locally But Pass in CI
- Check Python version matches CI (3.11 or 3.12)
- Ensure clean environment: `pip install -r requirements-dev.txt --force-reinstall`
- Clear pytest cache: `pytest --cache-clear`

### Coverage Lower Than Expected
- Check .coveragerc exclusions
- Ensure all code paths are tested
- Use `pytest --cov-report=html` to see uncovered lines

### Import Errors
- Ensure GITHUB_TOKEN is set: `export GITHUB_TOKEN=fake-token-for-testing`
- Verify all dependencies installed: `pip list`
