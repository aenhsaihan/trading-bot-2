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
        # Use a very small amount that should still fail if balance is near zero
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
            "/USDT",  # Missing base
            "BTC/USDT/ETH",  # Too many parts
            "BTC USDT",  # Space instead of slash
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
        # Test with very large number
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 1e15  # Extremely large
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        # Should fail due to insufficient balance
        self.assertEqual(response.status_code, 400)
    
    def test_very_small_amount(self):
        """Test with extremely small position amounts"""
        # Test with very small number (should still be valid if > 0)
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.00000001  # Very small
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        # Should either succeed or fail with validation error
        # If it succeeds, the position should be valid
        if response.status_code == 201:
            position = response.json()
            self.assertGreater(position['amount'], 0)
            # Clean up
            requests.delete(f"{BASE_URL}/trading/positions/{position['id']}")
        else:
            # Should be a validation error, not a server error
            self.assertIn(response.status_code, [400, 422])
    
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
    
    def test_concurrent_orders_different_symbols(self):
        """Test concurrent orders for different symbols"""
        symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "DOGE/USDT"]
        
        def open_position(symbol):
            data = {
                "symbol": symbol,
                "side": "long",
                "amount": 0.001
            }
            return requests.post(f"{BASE_URL}/trading/positions", json=data)
        
        # Open positions concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(open_position, sym): sym for sym in symbols}
            responses = []
            for future in as_completed(futures):
                responses.append(future.result())
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 201)
        self.assertEqual(success_count, len(symbols), 
                        "All concurrent orders for different symbols should succeed")
        
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
    
    def test_stop_loss_boundary_values(self):
        """Test stop loss with boundary values (0, 100, negative, >100)"""
        # Create a position first
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 201)
        position_id = response.json()['id']
        
        # Test 0% (should remove stop loss)
        update_data = {"stop_loss_percent": 0}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/stop-loss",
            json=update_data
        )
        self.assertEqual(response.status_code, 200)
        
        # Test 100% (edge case - should be valid)
        update_data = {"stop_loss_percent": 100}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/stop-loss",
            json=update_data
        )
        self.assertEqual(response.status_code, 200)
        
        # Test negative (should fail validation)
        update_data = {"stop_loss_percent": -1}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/stop-loss",
            json=update_data
        )
        self.assertIn(response.status_code, [400, 422])
        
        # Test > 100 (should fail validation)
        update_data = {"stop_loss_percent": 101}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/stop-loss",
            json=update_data
        )
        self.assertIn(response.status_code, [400, 422])
        
        # Clean up
        requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
    
    def test_trailing_stop_boundary_values(self):
        """Test trailing stop with boundary values"""
        # Create a position first
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 201)
        position_id = response.json()['id']
        
        # Test 0% (should remove trailing stop)
        update_data = {"trailing_stop_percent": 0}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/trailing-stop",
            json=update_data
        )
        # Should either succeed or fail gracefully
        self.assertIn(response.status_code, [200, 400, 404])
        
        # Test 100% (edge case)
        update_data = {"trailing_stop_percent": 100}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/trailing-stop",
            json=update_data
        )
        if response.status_code == 200:
            # If it accepts 100%, that's fine for paper trading
            pass
        
        # Test negative (should fail validation)
        update_data = {"trailing_stop_percent": -1}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{position_id}/trailing-stop",
            json=update_data
        )
        self.assertIn(response.status_code, [400, 422])
        
        # Clean up
        requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
    
    def test_close_nonexistent_position_variations(self):
        """Test closing positions with various invalid IDs"""
        invalid_ids = [
            "nonexistent",
            "12345",
            "BTC-USDT_invalid",
            "",  # Empty string
            "   ",  # Whitespace
            "special-chars-!@#$%",
        ]
        
        for position_id in invalid_ids:
            response = requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
            self.assertEqual(response.status_code, 404, 
                           f"Position ID '{position_id}' should return 404")
    
    def test_update_nonexistent_position(self):
        """Test updating stop loss/trailing stop on non-existent position"""
        invalid_id = "nonexistent-position-id-12345"
        
        # Test stop loss update
        data = {"stop_loss_percent": 5.0}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{invalid_id}/stop-loss",
            json=data
        )
        self.assertEqual(response.status_code, 404)
        
        # Test trailing stop update
        data = {"trailing_stop_percent": 5.0}
        response = requests.patch(
            f"{BASE_URL}/trading/positions/{invalid_id}/trailing-stop",
            json=data
        )
        self.assertEqual(response.status_code, 404)
    
    def test_rapid_sequential_operations(self):
        """Test rapid sequential operations on the same position"""
        # Create position
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 201)
        position_id = response.json()['id']
        
        # Rapidly update stop loss multiple times
        for i in range(5):
            update_data = {"stop_loss_percent": 2.0 + i}
            response = requests.patch(
                f"{BASE_URL}/trading/positions/{position_id}/stop-loss",
                json=update_data
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(0.1)  # Small delay to avoid overwhelming
        
        # Rapidly update trailing stop multiple times
        for i in range(5):
            update_data = {"trailing_stop_percent": 1.5 + i}
            response = requests.patch(
                f"{BASE_URL}/trading/positions/{position_id}/trailing-stop",
                json=update_data
            )
            self.assertEqual(response.status_code, 200)
            time.sleep(0.1)
        
        # Clean up
        requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
    
    def test_unicode_and_special_characters_in_symbol(self):
        """Test handling of special characters in symbol (if API allows)"""
        # Most APIs won't allow these, but test to ensure graceful handling
        special_symbols = [
            "BTC/USDT",
            "BTC-USDT",  # Hyphen instead of slash
            "BTC_USDT",  # Underscore
        ]
        
        for symbol in special_symbols:
            data = {
                "symbol": symbol,
                "side": "long",
                "amount": 0.001
            }
            response = requests.post(f"{BASE_URL}/trading/positions", json=data)
            # Should either succeed or fail with validation error, not crash
            self.assertIn(response.status_code, [201, 400, 422],
                         f"Symbol '{symbol}' should be handled gracefully")
            
            if response.status_code == 201:
                position_id = response.json()['id']
                requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
    
    def test_position_id_encoding(self):
        """Test that position IDs with special characters are handled correctly"""
        # Create a position (ID will contain symbols like BTC/USDT)
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001
        }
        response = requests.post(f"{BASE_URL}/trading/positions", json=data)
        self.assertEqual(response.status_code, 201)
        position_id = response.json()['id']
        
        # Try to get the position using the ID
        # The ID might contain special characters, so test URL encoding
        response = requests.get(f"{BASE_URL}/trading/positions/{position_id}")
        self.assertEqual(response.status_code, 200)
        
        # Try to close it
        response = requests.delete(f"{BASE_URL}/trading/positions/{position_id}")
        self.assertEqual(response.status_code, 200)
    
    def test_empty_request_body(self):
        """Test handling of empty or malformed request bodies"""
        # Test POST with empty body
        response = requests.post(
            f"{BASE_URL}/trading/positions",
            json={}
        )
        self.assertIn(response.status_code, [400, 422], 
                     "Empty body should be rejected")
        
        # Test PATCH with empty body
        response = requests.patch(
            f"{BASE_URL}/trading/positions/test-id/stop-loss",
            json={}
        )
        self.assertIn(response.status_code, [400, 422, 404],
                     "Empty body should be rejected or position not found")
    
    def test_malformed_json(self):
        """Test handling of malformed JSON"""
        # This would typically be caught by FastAPI before reaching our code
        # But test to ensure server doesn't crash
        response = requests.post(
            f"{BASE_URL}/trading/positions",
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        # Should return 422 (validation error) or 400, not 500
        self.assertIn(response.status_code, [400, 422])


if __name__ == '__main__':
    unittest.main()

