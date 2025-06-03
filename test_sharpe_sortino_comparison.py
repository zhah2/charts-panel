#!/usr/bin/env python3
"""
Test to compare JavaScript and Python quantstats implementations of Sharpe and Sortino ratios
"""

import numpy as np
import pandas as pd
import subprocess
import json
import tempfile
import os

def test_sharpe_sortino_differences():
    # Test data - 36 months of returns
    returns_data = [
        1.5, 2.3, -0.8, 1.2, 0.5, -1.1, 2.0, 0.3, -0.5, 1.8,
        -0.2, 1.7, 0.9, -1.3, 2.1, 0.7, -0.9, 1.4, 0.1, -0.6,
        1.9, -0.4, 1.6, 0.8, -1.0, 2.2, 0.6, -0.7, 1.3, 0.2,
        -0.3, 1.1, 0.4, -1.2, 2.4, 0.0
    ]
    
    risk_free_rate = 0.02  # 2% annual
    
    print("=== Sharpe and Sortino Ratio Comparison ===")
    print(f"Test data: {len(returns_data)} monthly returns")
    print(f"Risk-free rate: {risk_free_rate*100}% annual")
    print()
    
    # JavaScript calculation
    js_results = calculate_js_metrics(returns_data, risk_free_rate)
    
    # Python quantstats calculation
    py_results = calculate_python_metrics(returns_data, risk_free_rate)
    
    # Manual calculation for verification
    manual_results = calculate_manual_metrics(returns_data, risk_free_rate)
    
    # Compare results
    print("=== RESULTS COMPARISON ===")
    print(f"{'Metric':<15} {'JavaScript':<12} {'Python':<12} {'Manual':<12} {'JS-PY Diff':<12} {'JS-Manual Diff':<15}")
    print("-" * 90)
    
    for metric in ['sharpe', 'sortino']:
        js_val = js_results.get(metric, 0)
        py_val = py_results.get(metric, 0)
        manual_val = manual_results.get(metric, 0)
        
        js_py_diff = js_val - py_val
        js_manual_diff = js_val - manual_val
        
        print(f"{metric.capitalize():<15} {js_val:<12.6f} {py_val:<12.6f} {manual_val:<12.6f} {js_py_diff:<12.6f} {js_manual_diff:<15.6f}")
    
    print()
    print("=== DETAILED ANALYSIS ===")
    
    # Analyze Sharpe ratio differences
    print("\n1. SHARPE RATIO ANALYSIS:")
    print("   Standard formula: (Mean Excess Return * Periods) / (Std Dev of Excess Returns * sqrt(Periods))")
    
    # Calculate components manually
    monthly_returns = np.array(returns_data) / 100
    monthly_rf = risk_free_rate / 12
    excess_returns = monthly_returns - monthly_rf
    
    mean_excess = np.mean(excess_returns)
    std_excess_sample = np.std(excess_returns, ddof=1)  # Sample std (N-1)
    std_excess_pop = np.std(excess_returns, ddof=0)     # Population std (N)
    
    sharpe_sample = (mean_excess * 12) / (std_excess_sample * np.sqrt(12))
    sharpe_pop = (mean_excess * 12) / (std_excess_pop * np.sqrt(12))
    
    print(f"   Mean excess return (monthly): {mean_excess:.6f}")
    print(f"   Std dev excess (sample, ddof=1): {std_excess_sample:.6f}")
    print(f"   Std dev excess (population, ddof=0): {std_excess_pop:.6f}")
    print(f"   Sharpe (sample std): {sharpe_sample:.6f}")
    print(f"   Sharpe (population std): {sharpe_pop:.6f}")
    
    # Analyze Sortino ratio differences
    print("\n2. SORTINO RATIO ANALYSIS:")
    print("   Standard formula: (Mean Excess Return * Periods) / (Downside Deviation * sqrt(Periods))")
    
    # Calculate downside deviation
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) > 1:
        downside_var_sample = np.sum(downside_returns**2) / (len(downside_returns) - 1)
        downside_dev_sample = np.sqrt(downside_var_sample) * np.sqrt(12)
        sortino_sample = (mean_excess * 12) / downside_dev_sample
    else:
        downside_dev_sample = 0
        sortino_sample = 0
    
    if len(downside_returns) > 0:
        downside_var_pop = np.sum(downside_returns**2) / len(downside_returns)
        downside_dev_pop = np.sqrt(downside_var_pop) * np.sqrt(12)
        sortino_pop = (mean_excess * 12) / downside_dev_pop if downside_dev_pop > 0 else 0
    else:
        downside_dev_pop = 0
        sortino_pop = 0
    
    print(f"   Downside returns count: {len(downside_returns)} out of {len(excess_returns)}")
    print(f"   Downside deviation (sample, ddof=1): {downside_dev_sample:.6f}")
    print(f"   Downside deviation (population, ddof=0): {downside_dev_pop:.6f}")
    print(f"   Sortino (sample std): {sortino_sample:.6f}")
    print(f"   Sortino (population std): {sortino_pop:.6f}")
    
    print("\n=== POTENTIAL ISSUES IDENTIFIED ===")
    
    # Check for common differences
    if abs(js_results['sharpe'] - sharpe_sample) < 0.001:
        print("✓ JavaScript Sharpe uses sample standard deviation (ddof=1)")
    elif abs(js_results['sharpe'] - sharpe_pop) < 0.001:
        print("✗ JavaScript Sharpe uses population standard deviation (ddof=0)")
    else:
        print("? JavaScript Sharpe calculation differs from both sample and population methods")
    
    if abs(js_results['sortino'] - sortino_sample) < 0.001:
        print("✓ JavaScript Sortino uses sample downside deviation (ddof=1)")
    elif abs(js_results['sortino'] - sortino_pop) < 0.001:
        print("✗ JavaScript Sortino uses population downside deviation (ddof=0)")
    else:
        print("? JavaScript Sortino calculation differs from both sample and population methods")

def calculate_js_metrics(returns, risk_free_rate):
    """Calculate metrics using JavaScript implementation"""
    
    # Create temporary JavaScript file
    js_code = f"""
    // Load the portfolio-metrics.js functions
    const fs = require('fs');
    const path = require('path');
    
    // Read the portfolio-metrics.js file
    const metricsCode = fs.readFileSync(path.join(__dirname, 'portfolio-metrics.js'), 'utf8');
    eval(metricsCode);
    
    // Test data
    const returns = {json.dumps(returns)};
    const riskFreeRate = {risk_free_rate};
    
    // Calculate metrics
    const results = calculateMetricsForReturns(returns, riskFreeRate);
    
    // Output results
    console.log(JSON.stringify({{
        sharpe: results.sharpe,
        sortino: results.sortino,
        volatility: results.volatility,
        cagr: results.cagr
    }}));
    """
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(js_code)
        temp_js_file = f.name
    
    try:
        # Run JavaScript
        result = subprocess.run(['node', temp_js_file], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            print(f"JavaScript error: {result.stderr}")
            return {}
    finally:
        # Clean up
        os.unlink(temp_js_file)

def calculate_python_metrics(returns, risk_free_rate):
    """Calculate metrics using Python quantstats (if available)"""
    try:
        import quantstats as qs
        
        # Convert to pandas Series
        returns_series = pd.Series([r/100 for r in returns])  # Convert to decimal
        
        # Calculate metrics
        sharpe = qs.stats.sharpe(returns_series, rf=risk_free_rate)
        sortino = qs.stats.sortino(returns_series, rf=risk_free_rate)
        volatility = qs.stats.volatility(returns_series) * 100  # Convert back to percentage
        cagr = qs.stats.cagr(returns_series) * 100  # Convert back to percentage
        
        return {
            'sharpe': sharpe,
            'sortino': sortino,
            'volatility': volatility,
            'cagr': cagr
        }
    except ImportError:
        print("quantstats not available, using manual calculation")
        return calculate_manual_metrics(returns, risk_free_rate)

def calculate_manual_metrics(returns, risk_free_rate):
    """Manual calculation for verification"""
    
    # Convert to numpy array and decimal form
    monthly_returns = np.array(returns) / 100
    monthly_rf = risk_free_rate / 12
    
    # Calculate excess returns
    excess_returns = monthly_returns - monthly_rf
    mean_excess = np.mean(excess_returns)
    
    # Calculate volatility (sample standard deviation)
    volatility = np.std(monthly_returns, ddof=1) * np.sqrt(12) * 100
    
    # Calculate CAGR
    total_return = np.prod(1 + monthly_returns)
    years = len(monthly_returns) / 12
    cagr = (total_return ** (1/years) - 1) * 100
    
    # Calculate Sharpe ratio
    excess_vol = np.std(excess_returns, ddof=1) * np.sqrt(12)
    sharpe = (mean_excess * 12) / excess_vol if excess_vol > 0 else 0
    
    # Calculate Sortino ratio
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) > 1:
        downside_var = np.sum(downside_returns**2) / (len(downside_returns) - 1)
        downside_dev = np.sqrt(downside_var) * np.sqrt(12)
        sortino = (mean_excess * 12) / downside_dev if downside_dev > 0 else 0
    else:
        sortino = 0
    
    return {
        'sharpe': sharpe,
        'sortino': sortino,
        'volatility': volatility,
        'cagr': cagr
    }

if __name__ == "__main__":
    test_sharpe_sortino_differences() 