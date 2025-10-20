#!/usr/bin/env python3
"""
Simple test script to verify the maritime surveillance API endpoints
Run this after starting the Flask backend to test the endpoints
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000"
TEST_EEZ_ID = "5675"  # Estonia EEZ for testing

def test_endpoint(endpoint, method="GET", data=None, params=None):
    """Test an API endpoint and return the response"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, json=data, params=params)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
            
        print(f"🔍 Testing {method} {endpoint}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"   ✅ Success - Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                return result
            except json.JSONDecodeError:
                print(f"   ⚠️  Success but not JSON: {response.text[:100]}...")
                return response.text
        else:
            print(f"   ❌ Failed: {response.text[:200]}...")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection failed - Is the Flask backend running?")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    """Run all API tests"""
    print("🚢 Maritime Surveillance API Test Suite")
    print("=" * 50)
    
    # Test basic endpoints
    print("\n📋 Testing Basic Endpoints:")
    test_endpoint("/api/configs")
    test_endpoint("/api/eez-data")
    
    # Test detection endpoints
    print("\n🔍 Testing Detection Endpoints:")
    
    # Set up test parameters
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    date_range = f"{start_date.strftime('%Y-%m-%d')},{end_date.strftime('%Y-%m-%d')}"
    
    # Test detections endpoint
    params = {
        "eez_ids": TEST_EEZ_ID,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "matched": "false"
    }
    test_endpoint("/api/detections", params=params)
    
    # Test summary endpoint
    test_endpoint("/api/summary", params=params)
    
    # Test bins endpoint
    test_endpoint("/api/bins/5", params={
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    })
    
    # Test events endpoint
    test_endpoint("/api/events", params={
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "event_types": "fishing"
    })
    
    # Test vessel endpoint (with a dummy ID)
    test_endpoint("/api/vessels/test-vessel-123")
    
    # Test insights endpoint
    test_endpoint("/api/insights", method="POST", data={
        "vessel_ids": ["test-vessel-123"],
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "includes": ["FISHING", "GAP"]
    })
    
    # Test style generation
    test_endpoint("/api/generate-style", method="POST", data={
        "interval": "DAY",
        "datasets": ["public-global-sar-presence:latest"],
        "date_range": date_range,
        "color": "viridis"
    })
    
    print("\n" + "=" * 50)
    print("🏁 Test suite completed!")
    print("\n💡 Tips:")
    print("   - If you see 'Connection failed', make sure the Flask backend is running")
    print("   - If you see 'GFW_API_TOKEN not set', set the environment variable")
    print("   - Check the Flask logs for detailed error information")

if __name__ == "__main__":
    main()
