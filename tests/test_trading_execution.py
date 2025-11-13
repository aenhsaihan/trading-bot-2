"""Integration tests for trading execution endpoints

Tests the trading API endpoints to ensure orders can be placed,
positions managed, and everything works end-to-end.
"""

import requests
import json
import time
from typing import Dict, Optional

BASE_URL = "http://localhost:8000"
TRADING_BASE = f"{BASE_URL}/trading"


class TradingExecutionTests:
    """Test suite for trading execution"""
    
    def __init__(self):
        self.created_positions = []  # Track positions for cleanup
        self.initial_balance = None
    
    def setup(self):
        """Setup: Get initial balance"""
        print("\n" + "=" * 60)
        print("SETUP: Getting initial balance...")
        response = requests.get(f"{TRADING_BASE}/balance")
        if response.status_code == 200:
            data = response.json()
            self.initial_balance = data['balance']
            print(f"✅ Initial balance: {self.initial_balance} {data['currency']}")
        else:
            print(f"❌ Failed to get balance: {response.status_code}")
            print(response.text)
    
    def test_get_balance(self) -> bool:
        """Test: GET /trading/balance"""
        print("\n" + "-" * 60)
        print("TEST: GET /trading/balance")
        response = requests.get(f"{TRADING_BASE}/balance")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Balance: {data['balance']} {data['currency']}")
            print(f"   Total Value: {data['total_value']}")
            print(f"   Total P&L: {data['total_pnl']} ({data['total_pnl_percent']:.2f}%)")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_get_positions(self) -> bool:
        """Test: GET /trading/positions"""
        print("\n" + "-" * 60)
        print("TEST: GET /trading/positions")
        response = requests.get(f"{TRADING_BASE}/positions")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} positions")
            print(f"   Total P&L: {data['total_pnl']} ({data['total_pnl_percent']:.2f}%)")
            if data['positions']:
                for pos in data['positions']:
                    print(f"   - {pos['symbol']} {pos['side']}: {pos['amount']} @ {pos['entry_price']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_open_long_position(self) -> Optional[Dict]:
        """Test: POST /trading/positions (long)"""
        print("\n" + "-" * 60)
        print("TEST: POST /trading/positions (long)")
        
        data = {
            "symbol": "BTC/USDT",
            "side": "long",
            "amount": 0.001,
            "stop_loss_percent": 3.0,
            "trailing_stop_percent": 2.5
        }
        
        response = requests.post(f"{TRADING_BASE}/positions", json=data)
        
        if response.status_code == 201:
            position = response.json()
            self.created_positions.append(position['id'])
            print(f"✅ Opened long position: {position['id']}")
            print(f"   Symbol: {position['symbol']}")
            print(f"   Amount: {position['amount']}")
            print(f"   Entry Price: {position['entry_price']}")
            print(f"   Stop Loss: {position['stop_loss_percent']}%")
            print(f"   Trailing Stop: {position['trailing_stop']}%")
            return position
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return None
    
    def test_open_short_position(self) -> Optional[Dict]:
        """Test: POST /trading/positions (short)"""
        print("\n" + "-" * 60)
        print("TEST: POST /trading/positions (short)")
        
        data = {
            "symbol": "ETH/USDT",
            "side": "short",
            "amount": 0.01,
            "stop_loss_percent": 5.0
        }
        
        response = requests.post(f"{TRADING_BASE}/positions", json=data)
        
        if response.status_code == 201:
            position = response.json()
            self.created_positions.append(position['id'])
            print(f"✅ Opened short position: {position['id']}")
            print(f"   Symbol: {position['symbol']}")
            print(f"   Amount: {position['amount']}")
            print(f"   Entry Price: {position['entry_price']}")
            return position
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return None
    
    def test_get_position_by_id(self, position_id: str) -> bool:
        """Test: GET /trading/positions/{id}"""
        print("\n" + "-" * 60)
        print(f"TEST: GET /trading/positions/{position_id}")
        
        # URL encode the position ID
        encoded_id = requests.utils.quote(position_id, safe='')
        response = requests.get(f"{TRADING_BASE}/positions/{encoded_id}")
        
        if response.status_code == 200:
            position = response.json()
            print(f"✅ Retrieved position: {position['symbol']} {position['side']}")
            print(f"   P&L: {position['pnl']} ({position['pnl_percent']:.2f}%)")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_set_stop_loss(self, position_id: str) -> bool:
        """Test: PATCH /trading/positions/{id}/stop-loss"""
        print("\n" + "-" * 60)
        print(f"TEST: PATCH /trading/positions/{position_id}/stop-loss")
        
        data = {"stop_loss_percent": 4.0}
        encoded_id = requests.utils.quote(position_id, safe='')
        response = requests.patch(
            f"{TRADING_BASE}/positions/{encoded_id}/stop-loss",
            json=data
        )
        
        if response.status_code == 200:
            position = response.json()
            print(f"✅ Set stop loss: {position['stop_loss_percent']}%")
            print(f"   Stop Loss Price: {position['stop_loss']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_set_trailing_stop(self, position_id: str) -> bool:
        """Test: PATCH /trading/positions/{id}/trailing-stop"""
        print("\n" + "-" * 60)
        print(f"TEST: PATCH /trading/positions/{position_id}/trailing-stop")
        
        data = {"trailing_stop_percent": 3.0}
        encoded_id = requests.utils.quote(position_id, safe='')
        response = requests.patch(
            f"{TRADING_BASE}/positions/{encoded_id}/trailing-stop",
            json=data
        )
        
        if response.status_code == 200:
            position = response.json()
            print(f"✅ Set trailing stop: {position['trailing_stop']}%")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_close_position(self, position_id: str) -> bool:
        """Test: DELETE /trading/positions/{id}"""
        print("\n" + "-" * 60)
        print(f"TEST: DELETE /trading/positions/{position_id}")
        
        encoded_id = requests.utils.quote(position_id, safe='')
        response = requests.delete(f"{TRADING_BASE}/positions/{encoded_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Closed position: {result['message']}")
            if 'result' in result and 'profit' in result['result']:
                print(f"   Profit: {result['result']['profit']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(response.text)
            return False
    
    def test_error_cases(self) -> bool:
        """Test error cases: insufficient balance, invalid symbol, etc."""
        print("\n" + "-" * 60)
        print("TEST: Error Cases")
        all_passed = True
        
        # Test 1: Invalid symbol
        print("\n  Test 1: Invalid symbol")
        data = {"symbol": "INVALID/PAIR", "side": "long", "amount": 0.001}
        response = requests.post(f"{TRADING_BASE}/positions", json=data)
        if response.status_code in [400, 404, 500]:
            print(f"  ✅ Correctly rejected invalid symbol: {response.status_code}")
        else:
            print(f"  ⚠️  Unexpected response: {response.status_code}")
            all_passed = False
        
        # Test 2: Negative amount
        print("\n  Test 2: Negative amount")
        data = {"symbol": "BTC/USDT", "side": "long", "amount": -0.001}
        response = requests.post(f"{TRADING_BASE}/positions", json=data)
        if response.status_code == 422:  # Validation error
            print(f"  ✅ Correctly rejected negative amount: {response.status_code}")
        else:
            print(f"  ⚠️  Unexpected response: {response.status_code}")
            all_passed = False
        
        # Test 3: Invalid side
        print("\n  Test 3: Invalid side")
        data = {"symbol": "BTC/USDT", "side": "invalid", "amount": 0.001}
        response = requests.post(f"{TRADING_BASE}/positions", json=data)
        if response.status_code == 422:  # Validation error
            print(f"  ✅ Correctly rejected invalid side: {response.status_code}")
        else:
            print(f"  ⚠️  Unexpected response: {response.status_code}")
            all_passed = False
        
        # Test 4: Non-existent position
        print("\n  Test 4: Non-existent position")
        fake_id = "NONEXISTENT_12345"
        encoded_id = requests.utils.quote(fake_id, safe='')
        response = requests.get(f"{TRADING_BASE}/positions/{encoded_id}")
        if response.status_code == 404:
            print(f"  ✅ Correctly returned 404 for non-existent position")
        else:
            print(f"  ⚠️  Unexpected response: {response.status_code}")
            all_passed = False
        
        return all_passed
    
    def cleanup(self):
        """Cleanup: Close all created positions"""
        print("\n" + "=" * 60)
        print("CLEANUP: Closing created positions...")
        for position_id in self.created_positions:
            try:
                encoded_id = requests.utils.quote(position_id, safe='')
                response = requests.delete(f"{TRADING_BASE}/positions/{encoded_id}")
                if response.status_code == 200:
                    print(f"✅ Closed position: {position_id}")
                else:
                    print(f"⚠️  Failed to close position {position_id}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error closing position {position_id}: {e}")
        self.created_positions = []
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("TRADING EXECUTION INTEGRATION TESTS")
        print("=" * 60)
        
        results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        
        try:
            # Setup
            self.setup()
            
            # Test 1: Get balance
            if self.test_get_balance():
                results["passed"] += 1
                results["tests"].append(("Get Balance", "PASS"))
            else:
                results["failed"] += 1
                results["tests"].append(("Get Balance", "FAIL"))
            
            # Test 2: Get positions
            if self.test_get_positions():
                results["passed"] += 1
                results["tests"].append(("Get Positions", "PASS"))
            else:
                results["failed"] += 1
                results["tests"].append(("Get Positions", "FAIL"))
            
            # Test 3: Open long position
            long_position = self.test_open_long_position()
            if long_position:
                results["passed"] += 1
                results["tests"].append(("Open Long Position", "PASS"))
                
                # Test 4: Get position by ID
                if self.test_get_position_by_id(long_position['id']):
                    results["passed"] += 1
                    results["tests"].append(("Get Position by ID", "PASS"))
                else:
                    results["failed"] += 1
                    results["tests"].append(("Get Position by ID", "FAIL"))
                
                # Test 5: Set stop loss
                if self.test_set_stop_loss(long_position['id']):
                    results["passed"] += 1
                    results["tests"].append(("Set Stop Loss", "PASS"))
                else:
                    results["failed"] += 1
                    results["tests"].append(("Set Stop Loss", "FAIL"))
                
                # Test 6: Set trailing stop
                if self.test_set_trailing_stop(long_position['id']):
                    results["passed"] += 1
                    results["tests"].append(("Set Trailing Stop", "PASS"))
                else:
                    results["failed"] += 1
                    results["tests"].append(("Set Trailing Stop", "FAIL"))
            else:
                results["failed"] += 1
                results["tests"].append(("Open Long Position", "FAIL"))
            
            # Test 7: Open short position
            short_position = self.test_open_short_position()
            if short_position:
                results["passed"] += 1
                results["tests"].append(("Open Short Position", "PASS"))
            else:
                results["failed"] += 1
                results["tests"].append(("Open Short Position", "FAIL"))
            
            # Test 8: Error cases
            if self.test_error_cases():
                results["passed"] += 1
                results["tests"].append(("Error Cases", "PASS"))
            else:
                results["failed"] += 1
                results["tests"].append(("Error Cases", "FAIL"))
            
            # Test 9: Close positions (if we have any)
            if self.created_positions:
                for pos_id in self.created_positions[:]:  # Copy list to avoid modification during iteration
                    if self.test_close_position(pos_id):
                        results["passed"] += 1
                        results["tests"].append((f"Close Position {pos_id[:20]}...", "PASS"))
                    else:
                        results["failed"] += 1
                        results["tests"].append((f"Close Position {pos_id[:20]}...", "FAIL"))
            
        except Exception as e:
            print(f"\n❌ Test suite error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            self.cleanup()
            
            # Summary
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"Passed: {results['passed']}")
            print(f"Failed: {results['failed']}")
            print(f"Total: {results['passed'] + results['failed']}")
            print("\nTest Details:")
            for test_name, status in results["tests"]:
                status_icon = "✅" if status == "PASS" else "❌"
                print(f"  {status_icon} {test_name}: {status}")
            print("=" * 60)


if __name__ == "__main__":
    tester = TradingExecutionTests()
    tester.run_all_tests()

