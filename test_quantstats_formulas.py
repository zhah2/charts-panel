#!/usr/bin/env python3
"""
Test to understand the exact quantstats implementation of Sharpe and Sortino ratios
"""

import numpy as np
import pandas as pd

def test_quantstats_formulas():
    # Test data - 36 months of returns
    returns_data = [
        1.5, 2.3, -0.8, 1.2, 0.5, -1.1, 2.0, 0.3, -0.5, 1.8,
        -0.2, 1.7, 0.9, -1.3, 2.1, 0.7, -0.9, 1.4, 0.1, -0.6,
        1.9, -0.4, 1.6, 0.8, -1.0, 2.2, 0.6, -0.7, 1.3, 0.2,
        -0.3, 1.1, 0.4, -1.2, 2.4, 0.0
    ]
    
    # Convert to pandas Series (as percentages)
    returns_series = pd.Series(returns_data)
    
    print("=== Testing QuantStats Formulas ===")
    print(f"Test data: {len(returns_data)} monthly returns")
    print(f"Returns range: {min(returns_data):.2f}% to {max(returns_data):.2f}%")
    print()
    
    try:
        import quantstats as qs
        
        # Test Sharpe ratio
        print("--- QuantStats Sharpe Ratio ---")
        sharpe_result = qs.stats.sharpe(returns_series)
        print(f"QuantStats Sharpe: {sharpe_result:.6f}")
        
        # Test Sortino ratio  
        print("\n--- QuantStats Sortino Ratio ---")
        sortino_result = qs.stats.sortino(returns_series)
        print(f"QuantStats Sortino: {sortino_result:.6f}")
        
        # Test volatility
        print("\n--- QuantStats Volatility ---")
        vol_result = qs.stats.volatility(returns_series)
        print(f"QuantStats Volatility: {vol_result:.6f}")
        
        # Let's also test with different risk-free rates
        print("\n--- Testing with different risk-free rates ---")
        for rf in [0.0, 0.02, 0.05]:
            sharpe_rf = qs.stats.sharpe(returns_series, rf=rf)
            sortino_rf = qs.stats.sortino(returns_series, rf=rf)
            print(f"RF={rf:.1%}: Sharpe={sharpe_rf:.6f}, Sortino={sortino_rf:.6f}")
        
        # Test with periods parameter
        print("\n--- Testing with periods parameter ---")
        for periods in [12, 252]:
            try:
                sharpe_periods = qs.stats.sharpe(returns_series, periods=periods)
                sortino_periods = qs.stats.sortino(returns_series, periods=periods)
                vol_periods = qs.stats.volatility(returns_series, periods=periods)
                print(f"Periods={periods}: Sharpe={sharpe_periods:.6f}, Sortino={sortino_periods:.6f}, Vol={vol_periods:.6f}")
            except Exception as e:
                print(f"Periods={periods}: Error - {e}")
        
    except ImportError:
        print("QuantStats not available. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "quantstats"], check=True)
        import quantstats as qs
        
        # Retry the tests
        sharpe_result = qs.stats.sharpe(returns_series)
        sortino_result = qs.stats.sortino(returns_series)
        vol_result = qs.stats.volatility(returns_series)
        
        print(f"QuantStats Sharpe: {sharpe_result:.6f}")
        print(f"QuantStats Sortino: {sortino_result:.6f}")
        print(f"QuantStats Volatility: {vol_result:.6f}")
    
    # Manual calculations to understand the formulas
    print("\n=== Manual Calculations ===")
    
    # Convert to decimal returns
    returns_decimal = np.array(returns_data) / 100
    
    # Basic statistics
    mean_return = np.mean(returns_decimal)
    std_return = np.std(returns_decimal, ddof=1)  # Sample standard deviation
    
    print(f"Mean return (monthly): {mean_return:.6f}")
    print(f"Std deviation (monthly): {std_return:.6f}")
    
    # Annualized values
    annual_return = (1 + mean_return) ** 12 - 1
    annual_vol = std_return * np.sqrt(12)
    
    print(f"Annualized return: {annual_return:.6f}")
    print(f"Annualized volatility: {annual_vol:.6f}")
    
    # Manual Sharpe calculation (assuming 2% risk-free rate)
    rf_annual = 0.02
    rf_monthly = (1 + rf_annual) ** (1/12) - 1
    
    excess_returns = returns_decimal - rf_monthly
    mean_excess = np.mean(excess_returns)
    std_excess = np.std(excess_returns, ddof=1)
    
    # Method 1: Using excess returns std
    sharpe_method1 = (mean_excess * 12) / (std_excess * np.sqrt(12))
    
    # Method 2: Using original returns std  
    sharpe_method2 = (annual_return - rf_annual) / annual_vol
    
    print(f"\nManual Sharpe (excess returns std): {sharpe_method1:.6f}")
    print(f"Manual Sharpe (original returns std): {sharpe_method2:.6f}")
    
    # Manual Sortino calculation
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) > 0:
        downside_std = np.std(downside_returns, ddof=1)
        sortino_manual = (mean_excess * 12) / (downside_std * np.sqrt(12))
    else:
        sortino_manual = float('inf')
    
    print(f"Manual Sortino: {sortino_manual:.6f}")
    
    # Alternative Sortino using target return = risk-free rate
    downside_vs_rf = returns_decimal[returns_decimal < rf_monthly] - rf_monthly
    if len(downside_vs_rf) > 0:
        downside_var = np.mean(downside_vs_rf ** 2)
        downside_dev = np.sqrt(downside_var)
        sortino_alt = (annual_return - rf_annual) / (downside_dev * np.sqrt(12))
        print(f"Manual Sortino (alt method): {sortino_alt:.6f}")

if __name__ == "__main__":
    test_quantstats_formulas() 