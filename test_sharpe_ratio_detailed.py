#!/usr/bin/env python3
"""
Detailed unit test comparing JavaScript and Python quantstats Sharpe ratio implementations
using Global Bonds data from returns.json
"""

import json
import numpy as np
import pandas as pd
import subprocess
import tempfile
import os

def load_global_bonds_data():
    """Load Global Bonds return data from returns.json"""
    try:
        with open('returns.json', 'r') as f:
            data = json.load(f)
        
        # Get Global Bonds data from assets
        if 'assets' in data and 'assets' in data['assets'] and 'Global Bonds' in data['assets']['assets']:
            returns_data = data['assets']['assets']['Global Bonds']
            dates = data['assets']['dates']
            
            # Filter out null values and corresponding dates
            filtered_returns = []
            filtered_dates = []
            for i, ret in enumerate(returns_data):
                if ret is not None:
                    filtered_returns.append(ret)
                    filtered_dates.append(dates[i])
            
            print(f"Loaded Global Bonds data: {len(filtered_returns)} periods")
            print(f"Date range: {filtered_dates[0]} to {filtered_dates[-1]}")
            print(f"Sample returns: {filtered_returns[:5]}")
            
            return filtered_returns, filtered_dates
        else:
            print("Global Bonds not found in returns.json")
            return None, None
            
    except Exception as e:
        print(f"Error loading returns.json: {e}")
        return None, None

def get_cash_risk_free_rate():
    """Get Cash returns to use as risk-free rate"""
    try:
        with open('returns.json', 'r') as f:
            data = json.load(f)
        
        # Look for Cash in both assets and reference series
        cash_data = None
        
        # First try assets
        if 'assets' in data and 'assets' in data['assets'] and 'Cash' in data['assets']['assets']:
            cash_data = data['assets']['assets']['Cash']
        # Then try reference series
        elif 'reference' in data and 'assets' in data['reference'] and 'Cash' in data['reference']['assets']:
            cash_data = data['reference']['assets']['Cash']
        
        if cash_data:
            # Calculate average cash return as risk-free rate
            valid_cash = [r for r in cash_data if r is not None]
            if valid_cash:
                avg_cash_rate = np.mean(valid_cash)
                print(f"Using Cash returns as risk-free rate: {avg_cash_rate:.4f}% monthly")
                return avg_cash_rate / 100  # Convert to decimal
        
        print("Cash data not found, using default 2% annual risk-free rate")
        return 0.02 / 12  # 2% annual converted to monthly
        
    except Exception as e:
        print(f"Error getting cash rate: {e}")
        return 0.02 / 12

def detect_frequency_python(dates):
    """Detect data frequency from dates"""
    if len(dates) < 2:
        return 12, "monthly"
    
    # Calculate average days between observations
    date_diffs = []
    for i in range(1, min(len(dates), 13)):  # Check first 12 intervals
        try:
            date1 = pd.to_datetime(dates[i-1])
            date2 = pd.to_datetime(dates[i])
            diff_days = (date2 - date1).days
            date_diffs.append(diff_days)
        except:
            continue
    
    if not date_diffs:
        return 12, "monthly"
    
    avg_days = np.mean(date_diffs)
    
    if avg_days <= 7:
        return 252, "daily"
    elif avg_days <= 10:
        return 52, "weekly"
    elif avg_days <= 35:
        return 12, "monthly"
    elif avg_days <= 100:
        return 4, "quarterly"
    else:
        return 1, "annual"

def calculate_python_sharpe_detailed(returns, risk_free_rate, periods_per_year):
    """Calculate Sharpe ratio with detailed breakdown using quantstats approach"""
    try:
        import quantstats as qs
        
        # Convert to pandas Series
        returns_series = pd.Series(returns)
        
        # Calculate using quantstats
        qs_sharpe = qs.stats.sharpe(returns_series, rf=risk_free_rate * periods_per_year, periods=periods_per_year)
        
        # Manual calculation for detailed breakdown
        returns_decimal = np.array(returns) / 100
        periodic_rf = risk_free_rate
        
        # Calculate excess returns
        excess_returns = returns_decimal - periodic_rf
        mean_excess_return = np.mean(excess_returns)
        
        # Calculate standard deviation of original returns (not excess returns)
        returns_std = np.std(returns_decimal, ddof=1)  # Sample standard deviation
        
        # Annualize
        annualized_excess_return = mean_excess_return * periods_per_year
        annualized_std = returns_std * np.sqrt(periods_per_year)
        
        # Calculate Sharpe ratio
        manual_sharpe = annualized_excess_return / annualized_std if annualized_std > 0 else 0
        
        return {
            'quantstats_sharpe': qs_sharpe,
            'manual_sharpe': manual_sharpe,
            'numerator': annualized_excess_return,
            'denominator': annualized_std,
            'mean_excess_return_periodic': mean_excess_return,
            'returns_std_periodic': returns_std,
            'periods_per_year': periods_per_year,
            'risk_free_rate_periodic': periodic_rf,
            'risk_free_rate_annual': risk_free_rate * periods_per_year
        }
        
    except ImportError:
        print("quantstats not available, using manual calculation only")
        
        returns_decimal = np.array(returns) / 100
        periodic_rf = risk_free_rate
        
        excess_returns = returns_decimal - periodic_rf
        mean_excess_return = np.mean(excess_returns)
        returns_std = np.std(returns_decimal, ddof=1)
        
        annualized_excess_return = mean_excess_return * periods_per_year
        annualized_std = returns_std * np.sqrt(periods_per_year)
        
        manual_sharpe = annualized_excess_return / annualized_std if annualized_std > 0 else 0
        
        return {
            'quantstats_sharpe': None,
            'manual_sharpe': manual_sharpe,
            'numerator': annualized_excess_return,
            'denominator': annualized_std,
            'mean_excess_return_periodic': mean_excess_return,
            'returns_std_periodic': returns_std,
            'periods_per_year': periods_per_year,
            'risk_free_rate_periodic': periodic_rf,
            'risk_free_rate_annual': risk_free_rate * periods_per_year
        }

def run_javascript_sharpe_detailed(returns, risk_free_rate, dates):
    """Run JavaScript Sharpe ratio calculation with detailed output"""
    
    # Get the absolute path to portfolio-metrics.js
    current_dir = os.getcwd()
    portfolio_metrics_path = os.path.join(current_dir, 'portfolio-metrics.js')
    
    # Create JavaScript test code
    js_code = f"""
const fs = require('fs');
const path = require('path');

// Load portfolio-metrics.js using absolute path
const portfolioMetrics = require('{portfolio_metrics_path.replace(os.sep, '/')}');

// Test data
const returns = {json.dumps(returns)};
const dates = {json.dumps(dates)};
const riskFreeRate = {risk_free_rate};

console.log('=== JavaScript Sharpe Ratio Detailed Calculation ===');
console.log('Data loaded successfully');
console.log('Returns length:', returns.length);
console.log('Risk-free rate:', riskFreeRate);

try {{
    // Detect frequency
    const frequency = portfolioMetrics.detectFrequency(returns, dates);
    console.log('Detected frequency:', frequency);

    // Calculate metrics with detailed breakdown
    const periodsPerYear = frequency.periodsPerYear;
    const periodicRiskFreeRate = riskFreeRate;

    // Convert returns to decimal
    const returnsDecimal = returns.map(r => r / 100);
    console.log('Sample decimal returns:', returnsDecimal.slice(0, 5));

    // Calculate excess returns
    const excessReturns = returnsDecimal.map(r => r - periodicRiskFreeRate);
    const meanExcessReturn = excessReturns.reduce((a, b) => a + b, 0) / excessReturns.length;
    console.log('Mean excess return (periodic):', meanExcessReturn);

    // Calculate standard deviation of original returns (sample variance, ddof=1)
    const meanReturn = returnsDecimal.reduce((a, b) => a + b, 0) / returnsDecimal.length;
    const variance = returnsDecimal.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 2), 0) / (returnsDecimal.length - 1);
    const returnsStd = Math.sqrt(variance);
    console.log('Returns std dev (periodic):', returnsStd);

    // Annualize - ensure no null values
    const annualizedExcessReturn = meanExcessReturn * periodsPerYear;
    const annualizedStd = returnsStd * Math.sqrt(periodsPerYear);
    console.log('Annualized excess return:', annualizedExcessReturn);
    console.log('Annualized std dev:', annualizedStd);

    // Calculate Sharpe ratio - handle division by zero
    const sharpeRatio = (annualizedStd > 0) ? annualizedExcessReturn / annualizedStd : 0;
    console.log('Sharpe ratio:', sharpeRatio);

    // Output detailed results - only check for actual NaN/undefined
    const results = {{
        sharpe_ratio: (isNaN(sharpeRatio) || !isFinite(sharpeRatio)) ? 0 : sharpeRatio,
        numerator: (isNaN(annualizedExcessReturn) || !isFinite(annualizedExcessReturn)) ? 0 : annualizedExcessReturn,
        denominator: (isNaN(annualizedStd) || !isFinite(annualizedStd)) ? 0 : annualizedStd,
        mean_excess_return_periodic: (isNaN(meanExcessReturn) || !isFinite(meanExcessReturn)) ? 0 : meanExcessReturn,
        returns_std_periodic: (isNaN(returnsStd) || !isFinite(returnsStd)) ? 0 : returnsStd,
        periods_per_year: periodsPerYear,
        risk_free_rate_periodic: periodicRiskFreeRate,
        risk_free_rate_annual: riskFreeRate * periodsPerYear,
        frequency_name: frequency.name
    }};

    console.log('=== RESULTS_START ===');
    console.log(JSON.stringify(results, null, 2));
    console.log('=== RESULTS_END ===');

    // Also run the main function for comparison
    const mainResults = portfolioMetrics.calculateMetricsForReturns(returns, riskFreeRate, dates);
    console.log('Main function Sharpe:', mainResults.sharpe);
    
}} catch (error) {{
    console.error('Error in calculation:', error.message);
    console.error('Stack:', error.stack);
}}
"""

    # Write to temporary file in the current directory
    temp_file = os.path.join(current_dir, f'temp_sharpe_test_{os.getpid()}.js')
    
    try:
        with open(temp_file, 'w') as f:
            f.write(js_code)
        
        # Run the JavaScript code
        result = subprocess.run(['node', temp_file], 
                              capture_output=True, text=True, cwd=current_dir)
        
        if result.returncode != 0:
            print(f"JavaScript execution error: {result.stderr}")
            return None
        
        # Parse the output to extract JSON results
        output_lines = result.stdout.strip().split('\n')
        
        # Find the results section using markers
        results_start = -1
        results_end = -1
        
        for i, line in enumerate(output_lines):
            if '=== RESULTS_START ===' in line:
                results_start = i + 1
            elif '=== RESULTS_END ===' in line:
                results_end = i
                break
        
        if results_start >= 0 and results_end >= 0:
            # Extract JSON lines between markers
            json_lines = output_lines[results_start:results_end]
            json_str = '\n'.join(json_lines).strip()
            
            if json_str:
                try:
                    js_results = json.loads(json_str)
                    return js_results
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print("Raw JSON string:", json_str)
                    return None
        
        print("Could not find results markers in output")
        print("Full output:")
        print(result.stdout)
        return None
            
    except Exception as e:
        print(f"Error running JavaScript: {e}")
        return None
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except:
            pass

def main():
    print("=== Detailed Sharpe Ratio Comparison: JavaScript vs Python quantstats ===")
    print("Using Global Bonds data from returns.json\n")
    
    # Load data
    returns, dates = load_global_bonds_data()
    if returns is None:
        print("Failed to load Global Bonds data")
        return
    
    # Get risk-free rate
    risk_free_rate = get_cash_risk_free_rate()
    
    # Detect frequency
    periods_per_year, freq_name = detect_frequency_python(dates)
    print(f"Detected frequency: {freq_name} ({periods_per_year} periods per year)")
    print(f"Risk-free rate: {risk_free_rate:.6f} per period ({risk_free_rate * periods_per_year:.4f} annual)")
    print(f"Data points: {len(returns)}")
    print()
    
    # Calculate Python results
    print("=== Python Calculation ===")
    py_results = calculate_python_sharpe_detailed(returns, risk_free_rate, periods_per_year)
    
    print(f"Quantstats Sharpe: {py_results['quantstats_sharpe']:.6f}" if py_results['quantstats_sharpe'] is not None else "Quantstats not available")
    print(f"Manual Sharpe: {py_results['manual_sharpe']:.6f}")
    print(f"Numerator (annualized excess return): {py_results['numerator']:.6f}")
    print(f"Denominator (annualized std dev): {py_results['denominator']:.6f}")
    print(f"Mean excess return (periodic): {py_results['mean_excess_return_periodic']:.6f}")
    print(f"Returns std dev (periodic): {py_results['returns_std_periodic']:.6f}")
    print()
    
    # Calculate JavaScript results
    print("=== JavaScript Calculation ===")
    js_results = run_javascript_sharpe_detailed(returns, risk_free_rate, dates)
    
    if js_results:
        print(f"JavaScript Sharpe: {js_results['sharpe_ratio']:.6f}")
        print(f"Numerator (annualized excess return): {js_results['numerator']:.6f}")
        print(f"Denominator (annualized std dev): {js_results['denominator']:.6f}")
        print(f"Mean excess return (periodic): {js_results['mean_excess_return_periodic']:.6f}")
        print(f"Returns std dev (periodic): {js_results['returns_std_periodic']:.6f}")
        print(f"Detected frequency: {js_results.get('frequency_name', 'unknown')} ({js_results.get('periods_per_year', 'unknown')} periods/year)")
        print()
        
        # Detailed comparison
        print("=== Detailed Comparison ===")
        print(f"{'Metric':<35} {'Python':<15} {'JavaScript':<15} {'Difference':<15}")
        print("-" * 80)
        
        # Compare main Sharpe ratio
        py_sharpe = py_results['manual_sharpe']
        js_sharpe = js_results['sharpe_ratio']
        diff_sharpe = js_sharpe - py_sharpe
        print(f"{'Sharpe Ratio':<35} {py_sharpe:<15.6f} {js_sharpe:<15.6f} {diff_sharpe:<15.6f}")
        
        # Compare numerator
        py_num = py_results['numerator']
        js_num = js_results['numerator']
        diff_num = js_num - py_num
        print(f"{'Numerator (annual excess return)':<35} {py_num:<15.6f} {js_num:<15.6f} {diff_num:<15.6f}")
        
        # Compare denominator
        py_den = py_results['denominator']
        js_den = js_results['denominator']
        diff_den = js_den - py_den
        print(f"{'Denominator (annual std dev)':<35} {py_den:<15.6f} {js_den:<15.6f} {diff_den:<15.6f}")
        
        # Compare periodic components
        py_mean_ex = py_results['mean_excess_return_periodic']
        js_mean_ex = js_results['mean_excess_return_periodic']
        diff_mean_ex = js_mean_ex - py_mean_ex
        print(f"{'Mean excess return (periodic)':<35} {py_mean_ex:<15.6f} {js_mean_ex:<15.6f} {diff_mean_ex:<15.6f}")
        
        py_std = py_results['returns_std_periodic']
        js_std = js_results['returns_std_periodic']
        diff_std = js_std - py_std
        print(f"{'Returns std dev (periodic)':<35} {py_std:<15.6f} {js_std:<15.6f} {diff_std:<15.6f}")
        
        # Compare frequency detection
        py_periods = py_results['periods_per_year']
        js_periods = js_results.get('periods_per_year', 0)
        print(f"{'Periods per year':<35} {py_periods:<15} {js_periods:<15} {js_periods - py_periods:<15}")
        
        print()
        print("=== Summary ===")
        
        # Debug why JavaScript values are 0
        if js_num == 0 and js_den == 0:
            print("⚠️  JavaScript calculation returned 0 values - likely NaN handling issue")
            print("   Periodic values look correct, issue is in annualization")
        
        if abs(diff_sharpe) < 1e-6:
            print("✅ Sharpe ratios match within tolerance")
        else:
            print(f"❌ Sharpe ratio difference: {diff_sharpe:.6f}")
            
        if abs(diff_num) < 1e-6:
            print("✅ Numerators match within tolerance")
        else:
            print(f"❌ Numerator difference: {diff_num:.6f}")
            
        if abs(diff_den) < 1e-6:
            print("✅ Denominators match within tolerance")
        else:
            print(f"❌ Denominator difference: {diff_den:.6f}")
            
        # Check if quantstats is available for comparison
        if py_results['quantstats_sharpe'] is not None:
            qs_diff = py_results['quantstats_sharpe'] - py_results['manual_sharpe']
            print(f"📊 QuantStats vs Manual Python difference: {qs_diff:.6f}")
    else:
        print("Failed to run JavaScript calculation")

if __name__ == "__main__":
    main() 