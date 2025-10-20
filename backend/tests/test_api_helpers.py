import os
import sys
import time
import base64
import json
import requests
import pytest
from werkzeug.datastructures import MultiDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import api_helpers


def test_parse_eez_ids_repeated_and_comma_and_json():
    # repeated params
    md = MultiDict([('eez_ids', '1'), ('eez_ids', '2')])
    assert api_helpers.parse_eez_ids(md) == ['1', '2']

    # comma-separated
    md2 = MultiDict({'eez_ids': '3,4,5'})
    assert api_helpers.parse_eez_ids(md2) == ['3', '4', '5']

    # json array
    md3 = MultiDict({'eez_ids': '[6,7,8]'})
    assert api_helpers.parse_eez_ids(md3) == ['6', '7', '8']


def test_gfw_request_injects_auth(monkeypatch):
    os.environ['GFW_API_TOKEN'] = 'test-token-123'

    captured = {}

    class MockResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {'ok': True}

    def fake_request(method, url, params=None, json=None, headers=None, timeout=None):
        # assert Authorization header present
        assert headers is not None
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test-token-123'
        captured['method'] = method
        captured['url'] = url
        captured['params'] = params
        captured['json'] = json
        captured['headers'] = headers
        return MockResp()

    monkeypatch.setattr(api_helpers._session, 'request', fake_request)

    resp = api_helpers.gfw_request('GET', 'https://example.org/test', params={'a': 'b'})
    assert resp.json() == {'ok': True}
    assert captured['method'] == 'GET'
    assert captured['url'] == 'https://example.org/test'
    assert captured['params'] == {'a': 'b'}


def test_gfw_request_raises_on_http_error(monkeypatch):
    os.environ['GFW_API_TOKEN'] = 'test-token-456'

    class ErrResp:
        def raise_for_status(self):
            raise requests.HTTPError('boom')

    def fake_request(method, url, params=None, json=None, headers=None, timeout=None):
        return ErrResp()

    monkeypatch.setattr(api_helpers._session, 'request', fake_request)

    with pytest.raises(requests.HTTPError):
        api_helpers.gfw_request('GET', 'https://example.org/fail')


def test_get_gfw_token_cached_parses_jwt(monkeypatch):
    # Build a minimal unsigned JWT: header.payload.
    payload = {'exp': int(time.time()) + 3600}
    header_b64 = base64.urlsafe_b64encode(json.dumps({'alg': 'none'}).encode()).rstrip(b'=').decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b'=').decode()
    token = f"{header_b64}.{payload_b64}."

    monkeypatch.setenv('GFW_API_TOKEN', token)

    t = api_helpers.get_gfw_token_cached()
    assert t == token
    # Ensure expiry was parsed
    assert api_helpers._GFW_TOKEN_EXP == payload['exp']


def test_parse_eez_ids_prioritize_parents():
    class MockArgs:
        def getlist(self, key):
            return []

        def get(self, key):
            return None

    # Case 1: Parent and child EEZs present
    args = MockArgs()
    args.getlist = lambda key: ["Dominican Republic", "Dominican Republic - All Territories"]
    result = api_helpers.parse_eez_ids(args, prioritize_parents=True)
    assert "Dominican Republic" in result
    assert "Dominican Republic - All Territories" not in result

    # Case 2: Only child EEZs present
    args.getlist = lambda key: ["Dominican Republic - All Territories"]
    result = api_helpers.parse_eez_ids(args, prioritize_parents=True)
    assert "Dominican Republic - All Territories" in result

    # Case 3: No prioritization
    args.getlist = lambda key: ["Dominican Republic", "Dominican Republic - All Territories"]
    result = api_helpers.parse_eez_ids(args, prioritize_parents=False)
    assert "Dominican Republic" in result
    assert "Dominican Republic - All Territories" in result


def test_parse_eez_ids_hierarchical_selection():
    class MockArgs:
        def getlist(self, key):
            return []

        def get(self, key):
            return None

    # Case 1: Select "Dominican Republic" and "France - All Territories"
    args = MockArgs()
    args.getlist = lambda key: ["Dominican Republic", "France - All Territories"]
    result = api_helpers.parse_eez_ids(args, prioritize_parents=True)
    assert "Dominican Republic" in result
    assert "France" in result
    assert "French Guiana" in result
    assert "Guadeloupe" in result
    assert "Martinique" in result

    # Case 2: Select "France - All Territories" and deselect "France"
    args.getlist = lambda key: ["France - All Territories", "French Guiana", "Guadeloupe", "Martinique"]
    result = api_helpers.parse_eez_ids(args, prioritize_parents=True)
    assert "France" not in result
    assert "French Guiana" in result
    assert "Guadeloupe" in result
    assert "Martinique" in result
