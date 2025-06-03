#!/usr/bin/env python3
"""
Test to demonstrate the difference between JavaScript (ddof=0) and Python (ddof=1) variance calculations
"""

import numpy as np

def test_variance_difference():
    # Test data
    data = [1.5, 2.3, -0.8, 1.2, 0.5, -1.1, 2.0, 0.3, -0.5, 1.8]
    
    print("Test data:", data)
    print(f"Number of observations: {len(data)}")
    print()
    
    # Calculate mean
    mean = sum(data) / len(data)
    print(f"Mean: {mean:.6f}")
    print()
    
    # JavaScript-style calculation (population variance, ddof=0)
    # variance = sum((x - mean)^2) / N
    js_variance = sum((x - mean)**2 for x in data) / len(data)
    js_volatility = np.sqrt(js_variance)
    
    # Python/quantstats style (sample variance, ddof=1)  
    # variance = sum((x - mean)^2) / (N - 1)
    py_variance = sum((x - mean)**2 for x in data) / (len(data) - 1)
    py_volatility = np.sqrt(py_variance)
    
    # Using numpy for verification
    numpy_js_variance = np.var(data, ddof=0)
    numpy_py_variance = np.var(data, ddof=1)
    
    print("=== VARIANCE CALCULATIONS ===")
    print(f"JavaScript (ddof=0, population): {js_variance:.8f}")
    print(f"Python (ddof=1, sample):         {py_variance:.8f}")
    print(f"NumPy verification (ddof=0):     {numpy_js_variance:.8f}")
    print(f"NumPy verification (ddof=1):     {numpy_py_variance:.8f}")
    print()
    
    print("=== VOLATILITY CALCULATIONS ===")
    print(f"JavaScript (ddof=0): {js_volatility:.8f}")
    print(f"Python (ddof=1):     {py_volatility:.8f}")
    print(f"Difference:          {abs(js_volatility - py_volatility):.8f}")
    print(f"Relative difference: {abs(js_volatility - py_volatility) / py_volatility * 100:.4f}%")
    print()
    
    # Show the mathematical relationship
    print("=== MATHEMATICAL RELATIONSHIP ===")
    print(f"Sample variance = Population variance * N / (N-1)")
    print(f"Sample variance = {js_variance:.8f} * {len(data)} / {len(data)-1}")
    print(f"Sample variance = {js_variance * len(data) / (len(data) - 1):.8f}")
    print(f"Actual sample variance = {py_variance:.8f}")
    print()
    
    # Annualization factor (assuming monthly data)
    annualization_factor = np.sqrt(12)
    print("=== ANNUALIZED VOLATILITY (assuming monthly data) ===")
    print(f"JavaScript annualized: {js_volatility * annualization_factor:.8f}")
    print(f"Python annualized:     {py_volatility * annualization_factor:.8f}")
    print(f"Difference:            {abs(js_volatility - py_volatility) * annualization_factor:.8f}")

if __name__ == "__main__":
    test_variance_difference() 