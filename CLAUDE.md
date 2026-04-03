# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask microservice that retrieves merged GitHub pull requests and returns them in JSON, YAML, or CSV format. Designed for OpenShift 4 deployment with no access control (use caution when deploying).

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add GITHUB_TOKEN

# Run development server (Flask built-in)
python app.py

# Test the API
./example_request.sh          # JSON (default)
./example_request.sh yaml     # YAML
./example_request.sh csv      # CSV
```

### Docker
```bash
# Build
docker build -t github-pr-hoover:latest .

# Run locally
docker run -p 8080:8080 -e GITHUB_TOKEN=your_token github-pr-hoover:latest
```

### OpenShift Deployment
```bash
# Deploy all resources
oc apply -k openshift/

# Start build
oc start-build github-pr-hoover

# Get route
oc get route github-pr-hoover -o jsonpath='{.spec.host}'
```

## Architecture

### Core Components

**Three-layer architecture:**

1. **app.py** - Flask application layer
   - Endpoint routing and HTTP handling
   - Request validation and parameter parsing
   - Content negotiation via Accept header (application/json, application/x-yaml, text/csv)
   - Error handling and response formatting

2. **github_service.py** - GitHub API integration layer
   - Wraps GitHub REST API v3
   - Handles authentication with personal access tokens
   - Implements pagination for PR queries
   - Fetches PR metadata and review information

3. **formatters.py** - Data transformation layer
   - Converts PR data to JSON, YAML, or CSV
   - Manages output format specifics

4. **config.py** - Configuration (currently defined but not used by app.py)

### API Design Patterns

**Content Type Negotiation:**
- ALWAYS use HTTP Accept header for format selection
- NEVER use query parameters like `?format=json`
- Supported: `application/json` (default), `application/x-yaml`, `text/csv`

**Response Format:**
- PR identifier keys: `orgName/repoName#prId`
- Values contain: orgName, repoName, prId, creator, mergedBy, createdAt, mergedAt, reviewers

### Critical Implementation Details

**Timezone Handling:**
- GitHub API returns UTC timestamps with timezone info
- ALWAYS use timezone-aware datetime objects: `datetime.fromtimestamp(ts, tz=timezone.utc)`
- NEVER use naive datetime objects (causes comparison errors)
- See github_service.py:45, 61, 111 for reference implementations

**GitHub API:**
- Base URL: https://api.github.com
- Authentication: Bearer token in Authorization header
- Pagination: 100 items per page, iterate until empty response
- Reviews endpoint separate from PR endpoint

## Environment Variables

Required:
- `GITHUB_TOKEN` or `GITHUB_PERSONAL_ACCESS_TOKEN` - Personal access token with `repo` scope

Optional:
- `PORT` - Server port (default: 8080)
- `HOST` - Server host (default: 0.0.0.0)
- `DEBUG` - Enable debug mode (default: False)

## Production Deployment

Uses Gunicorn with 4 workers and 120s timeout (see Dockerfile:26).
OpenShift resources include health probes checking `/health` endpoint.

## Security Warning

The service has NO access control. Any request effectively masquerades as the GitHub user whose token is configured. Deploy with caution.
