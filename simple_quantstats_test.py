#!/usr/bin/env python3
"""
Simple test to understand quantstats Sharpe and Sortino formulas
"""

import numpy as np
import pandas as pd

def test_quantstats_simple():
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
        # Import only the stats module to avoid IPython dependency
        from quantstats import stats as qs_stats
        
        # Test Sharpe ratio with default parameters
        print("--- QuantStats Sharpe Ratio ---")
        sharpe_result = qs_stats.sharpe(returns_series)
        print(f"QuantStats Sharpe (default): {sharpe_result:.6f}")
        
        # Test Sortino ratio with default parameters
        print("\n--- QuantStats Sortino Ratio ---")
        sortino_result = qs_stats.sortino(returns_series)
        print(f"QuantStats Sortino (default): {sortino_result:.6f}")
        
        # Test volatility
        print("\n--- QuantStats Volatility ---")
        vol_result = qs_stats.volatility(returns_series)
        print(f"QuantStats Volatility (default): {vol_result:.6f}")
        
        # Test with different risk-free rates
        print("\n--- Testing with different risk-free rates ---")
        for rf in [0.0, 0.02, 0.05]:
            try:
                sharpe_rf = qs_stats.sharpe(returns_series, rf=rf)
                sortino_rf = qs_stats.sortino(returns_series, rf=rf)
                print(f"RF={rf:.1%}: Sharpe={sharpe_rf:.6f}, Sortino={sortino_rf:.6f}")
            except Exception as e:
                print(f"RF={rf:.1%}: Error - {e}")
        
        # Test with periods parameter
        print("\n--- Testing with periods parameter ---")
        for periods in [12, 252]:
            try:
                sharpe_periods = qs_stats.sharpe(returns_series, periods=periods)
                sortino_periods = qs_stats.sortino(returns_series, periods=periods)
                vol_periods = qs_stats.volatility(returns_series, periods=periods)
                print(f"Periods={periods}: Sharpe={sharpe_periods:.6f}, Sortino={sortino_periods:.6f}, Vol={vol_periods:.6f}")
            except Exception as e:
                print(f"Periods={periods}: Error - {e}")
        
    except ImportError as e:
        print(f"QuantStats import error: {e}")
        return
    
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
    
    # Manual Sortino calculation - Method 1: Using excess returns
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) > 0:
        downside_std = np.std(downside_returns, ddof=1)
        sortino_method1 = (mean_excess * 12) / (downside_std * np.sqrt(12))
    else:
        sortino_method1 = float('inf')
    
    print(f"Manual Sortino (excess downside std): {sortino_method1:.6f}")
    
    # Manual Sortino calculation - Method 2: Using downside deviation from target
    target_return = rf_monthly  # Target = risk-free rate
    downside_vs_target = returns_decimal[returns_decimal < target_return] - target_return
    if len(downside_vs_target) > 0:
        # Calculate downside deviation (semi-deviation)
        downside_variance = np.mean(downside_vs_target ** 2)
        downside_deviation = np.sqrt(downside_variance)
        sortino_method2 = (annual_return - rf_annual) / (downside_deviation * np.sqrt(12))
        print(f"Manual Sortino (downside deviation): {sortino_method2:.6f}")
    
    # Manual Sortino calculation - Method 3: Using all returns vs target
    all_vs_target = returns_decimal - target_return
    downside_only = np.where(all_vs_target < 0, all_vs_target, 0)
    downside_variance_all = np.mean(downside_only ** 2)
    downside_deviation_all = np.sqrt(downside_variance_all)
    sortino_method3 = (annual_return - rf_annual) / (downside_deviation_all * np.sqrt(12))
    print(f"Manual Sortino (all periods method): {sortino_method3:.6f}")

if __name__ == "__main__":
    test_quantstats_simple() 