"""Quick test script for the FastAPI backend"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_notification():
    """Test creating a notification"""
    url = f"{BASE_URL}/notifications"
    data = {
        "type": "combined_signal",
        "priority": "critical",
        "title": "Test Notification",
        "message": "This is a test notification from the API",
        "source": "system",
        "symbol": "BTC/USDT",
        "confidence_score": 85.0,
        "urgency_score": 90.0,
        "promise_score": 88.0,
        "actions": ["approve", "reject", "custom"]
    }
    
    response = requests.post(url, json=data)
    print(f"Create notification: {response.status_code}")
    if response.status_code == 201:
        print(json.dumps(response.json(), indent=2))
    return response.json() if response.status_code == 201 else None

def test_get_notifications():
    """Test getting all notifications"""
    url = f"{BASE_URL}/notifications"
    response = requests.get(url)
    print(f"\nGet notifications: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total: {data['total']}, Unread: {data['unread_count']}")
        print(f"Notifications: {len(data['notifications'])}")
        if data['notifications']:
            print(json.dumps(data['notifications'][0], indent=2))
    return response.json() if response.status_code == 200 else None

def test_get_stats():
    """Test getting statistics"""
    url = f"{BASE_URL}/notifications/stats/summary"
    response = requests.get(url)
    print(f"\nGet stats: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    return response.json() if response.status_code == 200 else None

if __name__ == "__main__":
    print("Testing FastAPI Notification Backend")
    print("=" * 50)
    
    # Test creating a notification
    notification = test_create_notification()
    
    # Test getting notifications
    notifications = test_get_notifications()
    
    # Test getting stats
    stats = test_get_stats()
    
    print("\n" + "=" * 50)
    print("Tests complete!")

