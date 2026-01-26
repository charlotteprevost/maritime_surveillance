"""
Tests for API helper functions (request parsing and filter conversion).

Note: GFW API client tests are in test_gfw_client.py
"""
import os
import sys
import pytest
from werkzeug.datastructures import MultiDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils import api_helpers


def test_parse_eez_ids_repeated_and_comma_and_json():
    """Test parsing EEZ IDs from various input formats."""
    # repeated params
    md = MultiDict([('eez_ids', '1'), ('eez_ids', '2')])
    assert api_helpers.parse_eez_ids(md) == ['1', '2']

    # comma-separated
    md2 = MultiDict({'eez_ids': '3,4,5'})
    assert api_helpers.parse_eez_ids(md2) == ['3', '4', '5']

    # json array
    md3 = MultiDict({'eez_ids': '[6,7,8]'})
    assert api_helpers.parse_eez_ids(md3) == ['6', '7', '8']


def test_parse_eez_ids_multiple_formats():
    """Test parsing EEZ IDs from various input formats."""
    class MockArgs:
        def getlist(self, key):
            return []

        def get(self, key):
            return None

    # Case 1: JSON array format
    args = MockArgs()
    args.getlist = lambda key: ['["8493", "5677"]']
    result = api_helpers.parse_eez_ids(args)
    assert "8493" in result
    assert "5677" in result

    # Case 2: Comma-separated format
    args.getlist = lambda key: ["8493,5677,8456"]
    result = api_helpers.parse_eez_ids(args)
    assert "8493" in result
    assert "5677" in result
    assert "8456" in result

    # Case 3: Single value
    args.getlist = lambda key: ["8493"]
    result = api_helpers.parse_eez_ids(args)
    assert result == ["8493"]


def test_parse_filters_from_request():
    """Test parsing filters from request arguments."""
    class MockArgs:
        def getlist(self, key):
            return []
        
        def get(self, key):
            return None
    
    # Test with no filters
    args = MockArgs()
    filters = api_helpers.parse_filters_from_request(args)
    assert filters.flag is None
    # matched defaults to False (dark vessel view) when not provided
    assert filters.matched is False
    
    # Test with matched filter
    args.get = lambda key: "false" if key == "matched" else None
    filters = api_helpers.parse_filters_from_request(args)
    assert filters.matched is False
    
    # Test with flag filter
    args.getlist = lambda key: ["USA", "FRA"] if key == "flag" else []
    args.get = lambda key: None
    filters = api_helpers.parse_filters_from_request(args)
    assert "USA" in filters.flag
    assert "FRA" in filters.flag


def test_sar_filterset_to_gfw_string():
    """Test converting filter set to GFW API string format."""
    from schemas.filters import SarFilterSet
    
    # Test with matched filter
    filters = SarFilterSet(matched=False)
    result = api_helpers.sar_filterset_to_gfw_string(filters)
    assert "matched='false'" in result
    
    # Test with flag filter
    filters = SarFilterSet(flag=["USA", "FRA"])
    result = api_helpers.sar_filterset_to_gfw_string(filters)
    assert "flag in" in result
    assert "'USA'" in result
    assert "'FRA'" in result
    
    # Test with multiple filters
    filters = SarFilterSet(matched=False, flag=["USA"], geartype=["trawlers"])
    result = api_helpers.sar_filterset_to_gfw_string(filters)
    assert "matched='false'" in result
    assert "flag in" in result
    assert "geartype in" in result
    assert " AND " in result
