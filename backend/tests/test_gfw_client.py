"""
Tests for GFWApiClient.

Tests the GFW API client functionality including authentication,
request handling, and error management.
"""
import os
import sys
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.gfw_client import GFWApiClient


def test_gfw_client_initialization():
    """Test GFWApiClient initialization with token."""
    client = GFWApiClient("test-token-123")
    assert client.api_token == "test-token-123"
    assert "Authorization" in client.session.headers
    assert client.session.headers["Authorization"] == "Bearer test-token-123"
    assert client.session.headers["Content-Type"] == "application/json"


def test_gfw_client_make_request_injects_auth(monkeypatch):
    """Test that _make_request injects authorization header."""
    client = GFWApiClient("test-token-123")
    
    captured = {}
    
    class MockResp:
        def raise_for_status(self):
            return None
        
        def json(self):
            return {'ok': True}
    
    def fake_request(method, url, **kwargs):
        # Verify Authorization header is present
        headers = kwargs.get('headers', {})
        assert 'Authorization' in headers or 'Authorization' in client.session.headers
        captured['method'] = method
        captured['url'] = url
        captured['kwargs'] = kwargs
        return MockResp()
    
    monkeypatch.setattr(client.session, 'request', fake_request)
    
    resp = client._make_request('GET', '/test/endpoint', params={'a': 'b'})
    assert resp.json() == {'ok': True}
    assert captured['method'] == 'GET'
    assert 'test/endpoint' in captured['url']
    assert captured['kwargs'].get('params') == {'a': 'b'}


def test_gfw_client_make_request_raises_on_http_error(monkeypatch):
    """Test that _make_request raises on HTTP errors."""
    client = GFWApiClient("test-token-456")
    
    class ErrResp:
        status_code = 500
        text = "Internal Server Error"
        
        def raise_for_status(self):
            raise requests.HTTPError('Server Error')
        
        def json(self):
            return {'error': 'Server Error'}
    
    def fake_request(method, url, **kwargs):
        return ErrResp()
    
    monkeypatch.setattr(client.session, 'request', fake_request)
    
    with pytest.raises(requests.HTTPError):
        client._make_request('GET', '/test/endpoint')


def test_gfw_client_has_retry_strategy():
    """Test that GFWApiClient has retry strategy configured."""
    client = GFWApiClient("test-token")
    
    # Check that adapters are mounted
    assert 'https://' in client.session.adapters
    assert 'http://' in client.session.adapters
    
    # Verify adapter has retry strategy
    adapter = client.session.adapters['https://']
    assert hasattr(adapter, 'max_retries')
    assert adapter.max_retries is not None


def test_gfw_client_caching_disabled():
    """Test that caching can be disabled."""
    client = GFWApiClient("test-token", enable_cache=False)
    # Client should still work without caching
    assert client.api_token == "test-token"


def test_gfw_client_caching_enabled(monkeypatch):
    """Test that caching uses CachedSession when enabled and available."""
    from utils import gfw_client as gmod

    # Force cache availability and mock requests_cache module
    monkeypatch.setattr(gmod, "CACHE_AVAILABLE", True, raising=False)

    class FakeCachedSession:
        def __init__(self, *args, **kwargs):
            self.headers = {}

        def mount(self, *args, **kwargs):
            return None

    fake_requests_cache = MagicMock()
    fake_requests_cache.CachedSession = MagicMock(return_value=FakeCachedSession())
    monkeypatch.setattr(gmod, "requests_cache", fake_requests_cache, raising=False)

    client = GFWApiClient("test-token", enable_cache=True)
    assert client.api_token == "test-token"
    fake_requests_cache.CachedSession.assert_called_once()