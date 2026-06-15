"""
Test script for chip configuration loading
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chip_config_loader import ChipConfigLoader


def test_chip_config_loader():
    """Test chip configuration loader"""
    print("=" * 60)
    print("Testing Chip Configuration Loader")
    print("=" * 60)
    
    # Initialize loader
    loader = ChipConfigLoader()
    
    # Test 1: List available chips
    print("\n1. Available Chips:")
    print("-" * 40)
    chips = loader.get_available_chips()
    for chip in chips:
        print(f"  Chip ID: {chip['chip_id']}")
        print(f"    Name: {chip['chip_name']}")
        print(f"    System Type: {chip['system_type']}")
        print(f"    Work Areas: {chip['work_areas']}")
        print()
    
    # Test 2: Load each chip configuration
    print("\n2. Loading Chip Configurations:")
    print("-" * 40)
    
    test_chip_ids = ["72", "HanYuan_01", "IonTrap", "PQPUMESH8"]
    
    for chip_id in test_chip_ids:
        print(f"\nTesting Chip ID: {chip_id}")
        chip_config, point_label_list = loader.get_chip_config(chip_id)
        
        if chip_config:
            print(f"  ✓ Configuration loaded successfully")
            print(f"  ✓ Work areas: {point_label_list}")
            
            # Show structure of first work area
            first_area = str(list(chip_config.keys())[0])
            config_data = chip_config[first_area]
            
            print(f"  ✓ Config keys: {list(config_data.keys())[:5]}...")
            
            # Show some details if available
            if 'QuantumChipArch' in config_data:
                arch = config_data['QuantumChipArch']
                print(f"  ✓ Chip: {arch.get('Chip', 'N/A')}")
                print(f"  ✓ Qubit Count: {arch.get('QubitCount', 'N/A')}")
        else:
            print(f"  ✗ Failed to load configuration")
    
    # Test 3: Test invalid chip ID
    print("\n3. Testing Invalid Chip ID:")
    print("-" * 40)
    invalid_chip_id = "INVALID_999"
    chip_config, point_label_list = loader.get_chip_config(invalid_chip_id)
    
    if not chip_config:
        print(f"  ✓ Correctly returned empty config for invalid chip ID")
    else:
        print(f"  ✗ Unexpectedly loaded config for invalid chip ID")
    
    # Test 4: Test chip info retrieval
    print("\n4. Testing Chip Info Retrieval:")
    print("-" * 40)
    for chip_id in test_chip_ids:
        info = loader.get_chip_info(chip_id)
        if info:
            print(f"  {chip_id}: {info.get('chip_name', 'N/A')} ({info.get('system_type', 'N/A')})")
        else:
            print(f"  {chip_id}: Not found")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_chip_config_loader()
