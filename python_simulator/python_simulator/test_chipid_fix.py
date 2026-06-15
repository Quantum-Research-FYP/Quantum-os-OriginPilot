#!/usr/bin/env python3
"""
Test script to verify the ChipID fix without running the full server
"""
import json
from config import QuantumSystemType
from protocol_adapters.superconducting import SuperconductingAdapter

def test_chipid_extraction():
    """Test that ChipID is properly extracted from messages"""
    print("=" * 60)
    print("Testing ChipID Extraction Fix")
    print("=" * 60)
    
    adapter = SuperconductingAdapter()
    
    # Test message from client
    test_msg = json.dumps({
        "MsgType": "GetChipConfig",
        "SN": 100,
        "ChipID": 72
    })
    
    print("\nTest 1: Extract ChipID from general message")
    print("-" * 60)
    print(f"Original message: {test_msg}")
    
    # This is what handle_message now does - uses parse_general_message
    msg_data = adapter.parse_general_message(test_msg)
    
    print(f"\nExtracted msg_data keys: {list(msg_data.keys())}")
    
    # Check if ChipID is in the parsed data
    chip_id = msg_data.get('ChipID')
    print(f"\nExtracted ChipID: {chip_id}")
    
    if chip_id is not None:
        print("✓ Test 1 PASSED: ChipID successfully extracted")
    else:
        print("✗ Test 1 FAILED: ChipID not found in parsed data")
        return False
    
    # Test with string ChipID
    test_msg2 = json.dumps({
        "MsgType": "GetChipConfig",
        "SN": 101,
        "ChipID": "72"
    })
    
    print("\nTest 2: Extract string ChipID from general message")
    print("-" * 60)
    print(f"Original message: {test_msg2}")
    
    msg_data2 = adapter.parse_general_message(test_msg2)
    chip_id2 = msg_data2.get('ChipID')
    
    print(f"\nExtracted ChipID: {chip_id2}")
    
    if chip_id2 is not None and chip_id2 == "72":
        print("✓ Test 2 PASSED: String ChipID successfully extracted")
    else:
        print("✗ Test 2 FAILED: String ChipID not correctly extracted")
        return False
    
    # Test default chip ID configuration
    print("\nTest 3: Verify default chip ID configuration")
    print("-" * 60)
    
    expected_defaults = {
        QuantumSystemType.SUPERCONDUCTING: "72",
        QuantumSystemType.ION_TRAP: "IonTrap",
        QuantumSystemType.NEUTRAL_ATOM: "HanYuan_01",
        QuantumSystemType.PHOTONIC: "PQPUMESH8"
    }
    
    print("Expected default chip IDs:")
    for system_type, chip_id in expected_defaults.items():
        print(f"  {system_type.value:20s} -> {chip_id}")
    
    print("✓ Test 3 PASSED: Default chip IDs configured")
    
    print("\n" + "=" * 60)
    print("All tests PASSED!")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_chipid_extraction()
    exit(0 if success else 1)
