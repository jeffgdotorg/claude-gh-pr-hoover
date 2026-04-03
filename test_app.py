"""Comprehensive test suite for GitHub PR Hoover API."""

import pytest
import json
import yaml
from datetime import datetime, timezone
from unittest.mock import patch, Mock
from requests.exceptions import HTTPError, ConnectionError, Timeout
import app as flask_app


@pytest.fixture
def client():
    """Create test client for Flask app."""
    flask_app.app.config['TESTING'] = True
    with flask_app.app.test_client() as client:
        yield client


@pytest.fixture
def mock_pr_data():
    """Sample PR data from GitHub API."""
    return [
        {
            'number': 123,
            'user': {'login': 'alice'},
            'merged_by': {'login': 'bob'},
            'created_at': '2022-01-01T10:00:00Z',
            'merged_at': '2022-01-02T15:30:00Z'
        },
        {
            'number': 456,
            'user': {'login': 'charlie'},
            'merged_by': {'login': 'diana'},
            'created_at': '2022-01-03T08:00:00Z',
            'merged_at': '2022-01-04T12:00:00Z'
        }
    ]


@pytest.fixture
def mock_reviews_data():
    """Sample review data from GitHub API."""
    return [
        {'user': {'login': 'reviewer1'}},
        {'user': {'login': 'reviewer2'}},
        {'user': {'login': 'reviewer1'}}  # Duplicate to test deduplication
    ]


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200 and correct status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestMergedPRsEndpoint:
    """Tests for /api/v1/merged-prs endpoint."""

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_merged_prs_json(self, mock_get_prs, client):
        """Test getting PRs in JSON format."""
        mock_get_prs.return_value = [
            {'test-org/test-repo#123': {'orgName': 'test-org', 'repoName': 'test-repo', 'prId': 123}}
        ]

        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600')

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert len(data) == 1
        assert 'test-org/test-repo#123' in data[0]

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_merged_prs_yaml(self, mock_get_prs, client):
        """Test getting PRs in YAML format."""
        mock_get_prs.return_value = [
            {'test-org/test-repo#123': {'orgName': 'test-org', 'prId': 123}}
        ]

        response = client.get(
            '/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600',
            headers={'Accept': 'application/x-yaml'}
        )

        assert response.status_code == 200
        assert 'application/x-yaml' in response.content_type
        data = yaml.safe_load(response.data)
        assert len(data) == 1

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_merged_prs_csv(self, mock_get_prs, client):
        """Test getting PRs in CSV format."""
        mock_get_prs.return_value = [
            {'test-org/test-repo#123': {
                'orgName': 'test-org',
                'repoName': 'test-repo',
                'prId': 123,
                'creator': 'alice',
                'mergedBy': 'bob',
                'createdAt': 1640995200,
                'mergedAt': 1643673600
            }}
        ]

        response = client.get(
            '/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600',
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 200
        assert 'text/csv' in response.content_type
        csv_data = response.data.decode('utf-8')
        assert 'prIdentifier' in csv_data
        assert 'test-org/test-repo#123' in csv_data

    def test_missing_required_params(self, client):
        """Test error when required parameters are missing."""
        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Missing required parameters' in data['error']
        assert 'branch' in data['missing']
        assert 'start_time' in data['missing']
        assert 'end_time' in data['missing']

    def test_invalid_timestamp_format(self, client):
        """Test error when timestamps are not valid integers."""
        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=invalid&end_time=1643673600')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid timestamp format' in data['error']

    def test_invalid_time_range(self, client):
        """Test error when start_time >= end_time."""
        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1643673600&end_time=1640995200')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Invalid time range' in data['error']

    @patch('github_service.GitHubService.get_merged_prs')
    def test_github_api_error(self, mock_get_prs, client):
        """Test handling of GitHub API errors."""
        mock_get_prs.side_effect = Exception('GitHub API error')

        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Failed to fetch PRs from GitHub' in data['error']

    @patch('github_service.GitHubService.get_merged_prs')
    def test_empty_result_set(self, mock_get_prs, client):
        """Test handling when no PRs match the criteria."""
        mock_get_prs.return_value = []

        response = client.get('/api/v1/merged-prs?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []


class TestMergedPRsCountEndpoint:
    """Tests for /api/v1/merged-prs/count endpoint."""

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_count_text_plain(self, mock_get_prs, client):
        """Test getting count in text/plain format (default)."""
        mock_get_prs.return_value = [
            {'org/repo#1': {}},
            {'org/repo#2': {}},
            {'org/repo#3': {}}
        ]

        response = client.get('/api/v1/merged-prs/count?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600')

        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        assert response.data.decode('utf-8') == '3'

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_count_json(self, mock_get_prs, client):
        """Test getting count in JSON format."""
        mock_get_prs.return_value = [{'org/repo#1': {}}, {'org/repo#2': {}}]

        response = client.get(
            '/api/v1/merged-prs/count?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600',
            headers={'Accept': 'application/json'}
        )

        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert data['count'] == 2

    @patch('github_service.GitHubService.get_merged_prs')
    def test_get_count_yaml(self, mock_get_prs, client):
        """Test getting count in YAML format."""
        mock_get_prs.return_value = [{'org/repo#1': {}}]

        response = client.get(
            '/api/v1/merged-prs/count?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600',
            headers={'Accept': 'application/x-yaml'}
        )

        assert response.status_code == 200
        assert 'application/x-yaml' in response.content_type
        data = yaml.safe_load(response.data)
        assert data['count'] == 1

    def test_count_csv_not_supported(self, client):
        """Test that CSV format is rejected for count endpoint."""
        response = client.get(
            '/api/v1/merged-prs/count?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600',
            headers={'Accept': 'text/csv'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Unsupported format' in data['error']
        assert 'CSV' in data['detail']

    @patch('github_service.GitHubService.get_merged_prs')
    def test_count_zero_results(self, mock_get_prs, client):
        """Test count endpoint with zero results."""
        mock_get_prs.return_value = []

        response = client.get('/api/v1/merged-prs/count?org=test-org&repo=test-repo&branch=main&start_time=1640995200&end_time=1643673600')

        assert response.status_code == 200
        assert response.data.decode('utf-8') == '0'


class TestReviewersEndpoint:
    """Tests for /api/v1/merged-prs/{org}/{repo}/{prId}/reviewers endpoint."""

    @patch('github_service.GitHubService.get_pr_reviewers')
    def test_get_reviewers_success(self, mock_get_reviewers, client):
        """Test successfully getting reviewers for a PR."""
        mock_get_reviewers.return_value = ['reviewer1', 'reviewer2']

        response = client.get('/api/v1/merged-prs/test-org/test-repo/123/reviewers')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['reviewers'] == ['reviewer1', 'reviewer2']

    @patch('github_service.GitHubService.get_pr_reviewers')
    def test_get_reviewers_empty(self, mock_get_reviewers, client):
        """Test getting reviewers when PR has no reviews."""
        mock_get_reviewers.return_value = []

        response = client.get('/api/v1/merged-prs/test-org/test-repo/123/reviewers')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['reviewers'] == []

    @patch('github_service.GitHubService.get_pr_reviewers')
    def test_get_reviewers_not_found(self, mock_get_reviewers, client):
        """Test error when PR is not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        error = HTTPError()
        error.response = mock_response
        mock_get_reviewers.side_effect = error

        response = client.get('/api/v1/merged-prs/test-org/test-repo/999/reviewers')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['error']

    @patch('github_service.GitHubService.get_pr_reviewers')
    def test_get_reviewers_github_error(self, mock_get_reviewers, client):
        """Test error when GitHub API fails."""
        mock_response = Mock()
        mock_response.status_code = 503
        error = HTTPError()
        error.response = mock_response
        mock_get_reviewers.side_effect = error

        response = client.get('/api/v1/merged-prs/test-org/test-repo/123/reviewers')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'Failed to fetch reviewers from GitHub' in data['error']

    @patch('github_service.GitHubService.get_pr_reviewers')
    def test_get_reviewers_network_error(self, mock_get_reviewers, client):
        """Test handling of network errors."""
        mock_get_reviewers.side_effect = Exception('Network error')

        response = client.get('/api/v1/merged-prs/test-org/test-repo/123/reviewers')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'Failed to fetch reviewers' in data['error']


class TestGitHubService:
    """Tests for GitHubService class."""

    @patch('requests.get')
    def test_get_merged_prs_success(self, mock_get, mock_pr_data):
        """Test successful PR retrieval."""
        from github_service import GitHubService

        mock_response = Mock()
        mock_response.json.return_value = mock_pr_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('github_service.GitHubService.get_pr_reviewers', return_value=[]):
            service = GitHubService(token='test-token')
            result = service.get_merged_prs('test-org', 'test-repo', 'main', 1640995200, 1643673600)

            assert len(result) == 2
            assert 'test-org/test-repo#123' in result[0]

    @patch('requests.get')
    def test_get_pr_reviewers_deduplication(self, mock_get, mock_reviews_data):
        """Test that duplicate reviewers are removed."""
        from github_service import GitHubService

        mock_response = Mock()
        mock_response.json.return_value = mock_reviews_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        service = GitHubService(token='test-token')
        result = service.get_pr_reviewers('test-org', 'test-repo', 123)

        assert len(result) == 2
        assert 'reviewer1' in result
        assert 'reviewer2' in result

    @patch('requests.get')
    def test_github_api_timeout(self, mock_get):
        """Test handling of GitHub API timeout."""
        from github_service import GitHubService

        mock_get.side_effect = Timeout('Request timed out')

        service = GitHubService(token='test-token')

        with pytest.raises(Timeout):
            service.get_pr_reviewers('test-org', 'test-repo', 123)

    @patch('requests.get')
    def test_github_api_connection_error(self, mock_get):
        """Test handling of connection errors."""
        from github_service import GitHubService

        mock_get.side_effect = ConnectionError('Failed to connect')

        service = GitHubService(token='test-token')

        with pytest.raises(ConnectionError):
            service.get_merged_prs('test-org', 'test-repo', 'main', 1640995200, 1643673600)

    def test_missing_github_token(self):
        """Test error when GitHub token is not provided."""
        from github_service import GitHubService

        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match='GitHub token must be provided'):
                GitHubService()


class TestDataFormatters:
    """Tests for DataFormatter class."""

    def test_to_json(self):
        """Test JSON formatting."""
        from formatters import DataFormatter

        data = [{'test-org/test-repo#123': {'prId': 123}}]
        result = DataFormatter.to_json(data)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == data

    def test_to_yaml(self):
        """Test YAML formatting."""
        from formatters import DataFormatter

        data = [{'test-org/test-repo#123': {'prId': 123}}]
        result = DataFormatter.to_yaml(data)

        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_to_csv_empty(self):
        """Test CSV formatting with empty data."""
        from formatters import DataFormatter

        result = DataFormatter.to_csv([])
        assert result == ""

    def test_to_csv_with_data(self):
        """Test CSV formatting with data."""
        from formatters import DataFormatter

        data = [{
            'test-org/test-repo#123': {
                'orgName': 'test-org',
                'repoName': 'test-repo',
                'prId': 123,
                'creator': 'alice',
                'mergedBy': 'bob',
                'createdAt': 1640995200,
                'mergedAt': 1643673600
            }
        }]
        result = DataFormatter.to_csv(data)

        assert 'prIdentifier,orgName,repoName' in result
        assert 'test-org/test-repo#123,test-org,test-repo,123' in result


class TestErrorHandlers:
    """Tests for Flask error handlers."""

    def test_404_not_found(self, client):
        """Test 404 handler."""
        response = client.get('/api/v1/nonexistent')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Endpoint not found' in data['error']


class TestTimezoneHandling:
    """Tests for timezone-aware datetime handling."""

    @patch('requests.get')
    def test_timezone_aware_timestamps(self, mock_get):
        """Test that timestamps are properly timezone-aware."""
        from github_service import GitHubService

        pr_data = [{
            'number': 123,
            'user': {'login': 'alice'},
            'merged_by': {'login': 'bob'},
            'created_at': '2022-01-01T10:00:00Z',
            'merged_at': '2022-01-02T15:30:00+00:00'
        }]

        mock_response = Mock()
        mock_response.json.return_value = pr_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        service = GitHubService(token='test-token')
        result = service.get_merged_prs('test-org', 'test-repo', 'main', 1640995200, 1643673600)

        # Should not raise timezone comparison errors
        assert len(result) == 1
        pr_key = list(result[0].keys())[0]
        assert isinstance(result[0][pr_key]['createdAt'], int)
        assert isinstance(result[0][pr_key]['mergedAt'], int)
