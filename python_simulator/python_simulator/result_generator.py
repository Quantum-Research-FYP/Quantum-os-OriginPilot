"""
Random result generation for quantum simulation
"""
import random
import time
from typing import Dict, List

def generate_hex_string(num_bits: int) -> str:
    """
    Generate a random hexadecimal string representation of quantum state
    
    Args:
        num_bits: Number of qubits
        
    Returns:
        Hexadecimal string (e.g., "0x1a")
    """
    hex_digits = "0123456789abcdef"
    
    # Generate random state based on number of bits
    max_state = (1 << num_bits) - 1
    random_state = random.randint(0, max_state)
    
    # Convert to hex
    if random_state == 0:
        return "0x0"
    
    hex_str = ""
    while random_state > 0:
        hex_str = hex_digits[random_state % 16] + hex_str
        random_state = random_state // 16
    
    return f"0x{hex_str}" if hex_str else "0x0"


def generate_random_results(num_qubits: int, shots: int) -> Dict[str, int]:
    """
    Generate random measurement results for quantum simulation
    
    Args:
        num_qubits: Number of measured qubits
        shots: Number of measurement shots (100-10000)
        
    Returns:
        Dictionary mapping quantum states (hex) to count
    """
    results = {}
    
    for _ in range(shots):
        state = generate_hex_string(num_qubits)
        results[state] = results.get(state, 0) + 1
    
    return results


def generate_random_results_multiple(measured_qubits: List[int], shots: int) -> List[Dict[str, int]]:
    """
    Generate random results for multiple measurement circuits
    
    Args:
        measured_qubits: List of qubit counts for each circuit
        shots: Number of shots
        
    Returns:
        List of result dictionaries, one per circuit
    """
    result_vec = []
    for num_qubits in measured_qubits:
        result = generate_random_results(num_qubits, shots)
        result_vec.append(result)
    return result_vec
