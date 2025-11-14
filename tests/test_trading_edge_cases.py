"""Edge case tests for trading execution

Tests edge cases and error scenarios that might not be covered
in normal integration tests.
"""

import unittest
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict


BASE_URL = "http://localhost:8000"


class TradingEdgeCaseTests(unittest.TestCase):
    """Test suite for trading edge cases and error scenarios"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - check if backend is running"""
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code != 200:
                raise Exception("Backend not healthy")
        except Exception as e:
            raise unittest.SkipTest(f"Backend not available: {e}")
    
    def setUp(self):
        """Set up for each test - clean up any existing positions"""
        # Get all positions and close them
        response = requests.get(f"{BASE_URL}/trading/positions")
        if response.status_code == 200:
            positions = response.json().get('positions', [])
            for pos in positions:
                requests.delete(f"{BASE_URL}/trading/positions/{pos['id']}")
    
    def test_zero_balance_scenario(self):
        """Test behavior when balance is effectively zero"""
        # Get current balance
        response = requests.get(f"{BASE_URL}/trading/balance")
        balance = response.json()['balance']
        
        # Try to open a position with amount that would exceed balance
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": balance * 2  # Way more than available
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('balance', response.json()['detail'].lower())
    
    def test_invalid_symbol_format(self):
        """Test with various invalid symbol formats"""
        invalid_symbols = [
            "BTC",  # Missing quote
            "BTCUSDT",  # Missing separator
            "",  # Empty
            "BTC/",  # Missing quote part
        ]
        
        for symbol in invalid_symbols:
            data = {
                "symbol": symbol,
                "side": "long",
                "amount": 0.001
            }
            response = requests.post(f"{BASE_URL}/trading/positions", json=data)
            # Should either reject with 422 (validation) or 400 (business logic)
            self.assertIn(response.status_code, [400, 422], 
                         f"Symbol '{symbol}' should be rejected")
    
    def test_very_large_amount(self):
        """Test with extremely large position amounts"""
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 1e15  # Extremely large
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        # Should fail due to insufficient balance
        self.assertEqual(response.status_code, 400)
    
    def test_concurrent_orders_same_symbol(self):
        """Test concurrent orders for the same symbol"""
        def open_position():
            data = {
                "symbol": "BTC/USDT",
                "side": "long",
                "amount": 0.001
            }
            return requests.post(f"{BASE_URL}/trading/positions", json=data)
        
        # Open 5 positions concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(open_position) for _ in range(5)]
            responses = [f.result() for f in as_completed(futures)]
        
        # All should succeed (paper trading allows multiple positions)
        success_count = sum(1 for r in responses if r.status_code == 201)
        self.assertGreater(success_count, 0, "At least some concurrent orders should succeed")
        
        # Clean up
        for response in responses:
            if response.status_code == 201:
                position_id = response.json()['id']
                requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
    
    def test_concurrent_close_operations(self):
        """Test concurrent close operations on the same position"""
        # First create a position
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 201)
        position_id = response.json()['id']
        
        def close_position():
            return requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
        
        # Try to close the same position concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(close_position) for _ in range(3)]
            responses = [f.result() for f in as_completed(futures)]
        
        # Only one should succeed (others should get 404)
        success_count = sum(1 for r in responses if r.status_code == 200)
        not_found_count = sum(1 for r in responses if r.status_code == 404)
        
        self.assertEqual(success_count, 1, "Only one close should succeed")
        self.assertEqual(not_found_count, 2, "Others should get 404")
    
    def test_close_nonexistent_position(self):
        """Test closing positions with various invalid IDs"""
        invalid_ids = [
            "nonexistent",
            "12345",
            "BTC-USDT_invalid",
        ]
        
        for position_id in invalid_ids:
            response = requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
            self.assertEqual(response.status_code, 404, 
                           f"Position ID '{position_id}' should return 404")


if __name__ == '__main__':
    unittest.main()

