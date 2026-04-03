#!/bin/bash

# Test runner script for GitHub PR Hoover
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}GitHub PR Hoover - Test Suite${NC}"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q -r requirements-dev.txt

# Set test environment variables
export GITHUB_TOKEN=fake-token-for-testing

# Parse command line arguments
case "${1}" in
    --coverage)
        echo -e "${GREEN}Running tests with coverage report...${NC}"
        pytest --cov=. --cov-report=term-missing --cov-report=html
        echo ""
        echo -e "${GREEN}HTML coverage report generated at: htmlcov/index.html${NC}"
        ;;
    --verbose)
        echo -e "${GREEN}Running tests in verbose mode...${NC}"
        pytest -v
        ;;
    --fast)
        echo -e "${GREEN}Running tests (fast mode)...${NC}"
        pytest -q
        ;;
    --watch)
        echo -e "${GREEN}Running tests in watch mode...${NC}"
        pytest-watch
        ;;
    *)
        echo -e "${GREEN}Running all tests...${NC}"
        pytest
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo ""
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
