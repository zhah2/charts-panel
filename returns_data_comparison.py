#!/usr/bin/env python3
"""
Compare portfolio metrics calculated by JavaScript functions vs Python quantstats
using real data from returns.json with Cash returns as risk-free rate
"""

import json
import pandas as pd
import numpy as np
import subprocess
import tempfile
import os
import sys
from pathlib import Path

try:
    import quantstats as qs
except ImportError:
    print("Please install quantstats: pip install quantstats")
    sys.exit(1)

def load_returns_data():
    """Load returns data from returns.json"""
    returns_file = Path("returns.json")
    if not returns_file.exists():
        print("returns.json not found. Please run build.py first.")
        sys.exit(1)
    
    with open(returns_file, 'r') as f:
        return json.load(f)

def get_cash_returns(returns_data):
    """Extract Cash returns to use as risk-free rate"""
    cash_returns = None
    
    # Look for Cash returns in assets series first
    if 'assets' in returns_data and 'assets' in returns_data['assets']:
        if 'Cash' in returns_data['assets']['assets']:
            cash_returns = returns_data['assets']['assets']['Cash']
        # Try alternative names for cash
        elif 'US Cash' in returns_data['assets']['assets']:
            cash_returns = returns_data['assets']['assets']['US Cash']
        elif 'T-Bills' in returns_data['assets']['assets']:
            cash_returns = returns_data['assets']['assets']['T-Bills']
    
    # If not found in assets, check reference series
    if not cash_returns and 'reference' in returns_data and 'assets' in returns_data['reference']:
        if 'Cash' in returns_data['reference']['assets']:
            cash_returns = returns_data['reference']['assets']['Cash']
        elif 'T-Bills' in returns_data['reference']['assets']:
            cash_returns = returns_data['reference']['assets']['T-Bills']
        elif 'US Cash' in returns_data['reference']['assets']:
            cash_returns = returns_data['reference']['assets']['US Cash']
    
    if cash_returns:
        # Clean the cash returns (remove None values)
        clean_cash = []
        for ret in cash_returns:
            if ret is not None:
                try:
                    clean_cash.append(float(ret))
                except (ValueError, TypeError):
                    clean_cash.append(0.0)  # Use 0 for missing cash returns
            else:
                clean_cash.append(0.0)
        return clean_cash
    
    print("Warning: No Cash returns found, using 0.2% monthly as fallback")
    # Fallback: generate a reasonable cash return series (0.2% monthly ≈ 2.4% annually)
    return None

def align_returns_with_cash(asset_returns, cash_returns, asset_start_index=0):
    """Align asset returns with cash returns for the same periods"""
    if not cash_returns:
        # Fallback to 0.2% monthly if no cash data
        return asset_returns, [0.2] * len(asset_returns)
    
    # Make sure both series have the same length for the comparison period
    min_length = min(len(asset_returns), len(cash_returns) - asset_start_index)
    
    aligned_asset = asset_returns[:min_length]
    aligned_cash = cash_returns[asset_start_index:asset_start_index + min_length]
    
    return aligned_asset, aligned_cash

def detect_frequency_python(returns_data, dates=None):
    """Detect the frequency of a time series"""
    data_length = len(returns_data)
    
    # If we have dates, try to detect from date intervals
    if dates and len(dates) >= 2:
        try:
            from datetime import datetime
            date1 = datetime.strptime(dates[0][:10], '%Y-%m-%d')
            date2 = datetime.strptime(dates[1][:10], '%Y-%m-%d')
            days_diff = abs((date2 - date1).days)
            
            if days_diff <= 1.5:
                return {'periods': 252, 'name': 'daily', 'factor': np.sqrt(252)}
            elif days_diff <= 8:
                return {'periods': 52, 'name': 'weekly', 'factor': np.sqrt(52)}
            elif days_diff <= 35:
                return {'periods': 12, 'name': 'monthly', 'factor': np.sqrt(12)}
            elif days_diff <= 100:
                return {'periods': 4, 'name': 'quarterly', 'factor': np.sqrt(4)}
            else:
                return {'periods': 1, 'name': 'annual', 'factor': 1}
        except:
            # Fall back to heuristic detection
            pass
    
    # Heuristic detection based on data length
    if data_length > 1000:
        return {'periods': 252, 'name': 'daily', 'factor': np.sqrt(252)}
    elif data_length > 200:
        return {'periods': 52, 'name': 'weekly', 'factor': np.sqrt(52)}
    elif data_length > 50:
        return {'periods': 12, 'name': 'monthly', 'factor': np.sqrt(12)}
    elif data_length > 10:
        return {'periods': 4, 'name': 'quarterly', 'factor': np.sqrt(4)}
    else:
        return {'periods': 1, 'name': 'annual', 'factor': 1}

def create_js_test_file(asset_name, returns_data, cash_returns, dates=None):
    """Create a temporary JavaScript file to test a specific asset"""
    # Get the absolute path to portfolio-metrics.js
    metrics_file = Path("portfolio-metrics.js").absolute()
    
    js_code = f"""
// Import the portfolio metrics functions
const fs = require('fs');

// Read the portfolio-metrics.js file using absolute path
const metricsCode = fs.readFileSync('{str(metrics_file).replace(chr(92), chr(92)+chr(92))}', 'utf8');

// Execute the code to make functions available
eval(metricsCode);

// Test data for {asset_name}
const returns = {json.dumps(returns_data)};
const cashReturns = {json.dumps(cash_returns)};
const dates = {json.dumps(dates) if dates else 'null'};

// Calculate average cash return to use as risk-free rate
const avgCashReturn = cashReturns.reduce((a, b) => a + b, 0) / cashReturns.length;
const annualizedCashReturn = avgCashReturn * 12 / 100; // Convert to annual decimal

// Calculate metrics using cash return as risk-free rate and dates for frequency detection
const metrics = calculateMetricsForReturns(returns, annualizedCashReturn, dates);
const additionalMetrics = calculateAdditionalMetrics(returns, cashReturns, dates);
const cumulativeReturns = calculateCumulativeReturns(returns);

// Combine all metrics
const allMetrics = {{
    ...metrics,
    ...additionalMetrics,
    finalCumulativeReturn: cumulativeReturns[cumulativeReturns.length - 1],
    totalReturns: cumulativeReturns.length,
    avgCashReturn: avgCashReturn,
    annualizedCashReturn: annualizedCashReturn
}};

// Output as JSON
console.log(JSON.stringify(allMetrics, null, 2));
"""
    return js_code

def run_js_calculation(asset_name, returns_data, cash_returns, dates=None):
    """Run JavaScript calculation for a specific asset"""
    try:
        # Create temporary JS file
        js_code = create_js_test_file(asset_name, returns_data, cash_returns, dates)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(js_code)
            temp_js_file = f.name
        
        # Run with Node.js
        result = subprocess.run(
            ['node', temp_js_file],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Clean up
        os.unlink(temp_js_file)
        
        if result.returncode != 0:
            print(f"JavaScript error for {asset_name}: {result.stderr}")
            return None
        
        # Parse JSON result
        return json.loads(result.stdout)
    
    except Exception as e:
        print(f"Error running JS calculation for {asset_name}: {e}")
        return None

def calculate_python_metrics(returns_data, cash_returns, asset_name, dates=None):
    """Calculate metrics using Python quantstats with cash returns as risk-free rate"""
    try:
        # Convert to pandas Series
        returns_series = pd.Series(returns_data, dtype=float)
        cash_series = pd.Series(cash_returns, dtype=float)
        
        # Remove any NaN values from both series
        returns_series = returns_series.dropna()
        cash_series = cash_series.dropna()
        
        if len(returns_series) == 0:
            return None
        
        # Detect frequency
        frequency = detect_frequency_python(returns_data, dates)
        periods_per_year = frequency['periods']
        
        # Align the series lengths
        min_length = min(len(returns_series), len(cash_series))
        returns_series = returns_series.iloc[:min_length]
        cash_series = cash_series.iloc[:min_length]
        
        # Convert monthly returns to decimal form for quantstats
        returns_decimal = returns_series / 100.0
        cash_decimal = cash_series / 100.0
        
        # Calculate average cash return for annualized risk-free rate
        avg_cash_periodic = cash_decimal.mean()
        annualized_cash_rate = avg_cash_periodic * periods_per_year
        
        # Calculate metrics using quantstats with proper periods
        metrics = {}
        
        # Try quantstats functions first, fall back to manual calculation if they fail
        try:
            metrics['cagr'] = qs.stats.cagr(returns_decimal, periods=periods_per_year) * 100
        except:
            # Manual CAGR calculation
            total_return = (1 + returns_decimal).prod()
            years = len(returns_decimal) / periods_per_year
            metrics['cagr'] = (total_return ** (1/years) - 1) * 100 if years > 0 else 0
        
        try:
            metrics['volatility'] = qs.stats.volatility(returns_decimal, periods=periods_per_year) * 100
        except:
            # Manual volatility calculation
            metrics['volatility'] = returns_decimal.std() * frequency['factor'] * 100
        
        try:
            # Use cash returns as risk-free rate for Sharpe calculation
            metrics['sharpe'] = qs.stats.sharpe(returns_decimal, rf=annualized_cash_rate, periods=periods_per_year)
        except:
            # Manual Sharpe calculation
            excess_returns = returns_decimal - avg_cash_periodic
            metrics['sharpe'] = (excess_returns.mean() * periods_per_year) / (excess_returns.std() * frequency['factor']) if excess_returns.std() > 0 else 0
        
        try:
            # Use cash returns as risk-free rate for Sortino calculation
            metrics['sortino'] = qs.stats.sortino(returns_decimal, rf=annualized_cash_rate, periods=periods_per_year)
        except:
            # Manual Sortino calculation
            excess_returns = returns_decimal - avg_cash_periodic
            downside_returns = excess_returns[excess_returns < 0]
            downside_deviation = downside_returns.std() * frequency['factor'] if len(downside_returns) > 0 else 0.01
            metrics['sortino'] = (excess_returns.mean() * periods_per_year) / downside_deviation if downside_deviation > 0 else 0
        
        try:
            metrics['maxDrawdown'] = abs(qs.stats.max_drawdown(returns_decimal)) * 100
        except:
            # Manual max drawdown calculation
            cumulative = (1 + returns_decimal).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            metrics['maxDrawdown'] = abs(drawdown.min()) * 100
        
        # Additional metrics
        try:
            metrics['skewness'] = qs.stats.skew(returns_decimal)
        except:
            # Manual skewness calculation
            metrics['skewness'] = returns_decimal.skew()
        
        try:
            metrics['kurtosis'] = qs.stats.kurtosis(returns_decimal)
        except:
            # Manual kurtosis calculation
            metrics['kurtosis'] = returns_decimal.kurtosis()
        
        try:
            # VaR at 5% confidence level
            metrics['var95'] = np.percentile(returns_decimal * 100, 5)
        except:
            metrics['var95'] = 0
        
        try:
            # CVaR at 5% confidence level
            var_threshold = np.percentile(returns_decimal, 5)
            cvar_returns = returns_decimal[returns_decimal <= var_threshold]
            metrics['cvar'] = np.mean(cvar_returns) * 100 if len(cvar_returns) > 0 else 0
        except:
            metrics['cvar'] = 0
        
        # Cumulative return
        try:
            cumulative = (1 + returns_decimal).cumprod()
            metrics['finalCumulativeReturn'] = (cumulative.iloc[-1] - 1) * 100
        except:
            metrics['finalCumulativeReturn'] = 0
        
        metrics['totalReturns'] = len(returns_series)
        metrics['avgCashReturn'] = avg_cash_periodic * 100  # Back to percentage
        metrics['annualizedCashReturn'] = annualized_cash_rate
        metrics['frequency'] = frequency['name']
        metrics['periodsPerYear'] = periods_per_year
        
        return metrics
    
    except Exception as e:
        print(f"Error calculating Python metrics for {asset_name}: {e}")
        return None

def compare_metrics(js_metrics, py_metrics, asset_name):
    """Compare JavaScript and Python metrics"""
    if not js_metrics or not py_metrics:
        return None
    
    comparison = {
        'asset_name': asset_name,
        'total_periods': js_metrics.get('totalReturns', 0),
        'frequency_js': js_metrics.get('frequency', 'unknown'),
        'frequency_py': py_metrics.get('frequency', 'unknown'),
        'periods_per_year_js': js_metrics.get('periodsPerYear', 0),
        'periods_per_year_py': py_metrics.get('periodsPerYear', 0),
        'avg_cash_return_js': js_metrics.get('avgCashReturn', 0),
        'avg_cash_return_py': py_metrics.get('avgCashReturn', 0),
        'annualized_cash_rate_js': js_metrics.get('annualizedCashReturn', 0),
        'annualized_cash_rate_py': py_metrics.get('annualizedCashReturn', 0)
    }
    
    # Define metrics to compare
    metric_mappings = {
        'cagr': 'cagr',
        'volatility': 'volatility', 
        'sharpe': 'sharpe',
        'sortino': 'sortino',
        'maxDrawdown': 'maxDrawdown',
        'skewness': 'skewness',
        'kurtosis': 'kurtosis',
        'var95': 'var95',
        'cvar': 'cvar',
        'finalCumulativeReturn': 'finalCumulativeReturn'
    }
    
    for js_key, py_key in metric_mappings.items():
        js_val = js_metrics.get(js_key, 0)
        py_val = py_metrics.get(py_key, 0)
        
        comparison[f'{js_key}_js'] = js_val
        comparison[f'{js_key}_py'] = py_val
        
        # Calculate difference and percentage difference
        diff = js_val - py_val
        pct_diff = (diff / py_val * 100) if py_val != 0 else (0 if js_val == 0 else float('inf'))
        
        comparison[f'{js_key}_diff'] = diff
        comparison[f'{js_key}_pct_diff'] = pct_diff
    
    return comparison

def main():
    print("Loading returns data from returns.json...")
    returns_data = load_returns_data()
    
    # Check if portfolio-metrics.js exists
    if not Path("portfolio-metrics.js").exists():
        print("portfolio-metrics.js not found in current directory")
        sys.exit(1)
    
    # Extract cash returns to use as risk-free rate
    print("Extracting Cash returns for risk-free rate...")
    cash_returns = get_cash_returns(returns_data)
    
    if cash_returns:
        print(f"Found Cash returns: {len(cash_returns)} periods, avg = {np.mean(cash_returns):.3f}% monthly")
    else:
        print("Using fallback risk-free rate")
    
    # Get dates for frequency detection
    dates = None
    if 'assets' in returns_data and 'dates' in returns_data['assets']:
        dates = returns_data['assets']['dates']
        print(f"Found {len(dates)} date entries for frequency detection")
    
    # Collect all asset series from both assets and reference
    all_series = {}
    
    # Add assets series
    if 'assets' in returns_data and 'assets' in returns_data['assets']:
        for asset_name, asset_returns in returns_data['assets']['assets'].items():
            # Skip Cash since we're using it as risk-free rate
            if asset_name.lower() in ['cash', 'us cash', 't-bills']:
                continue
                
            # Filter out None values and convert to float
            clean_returns = []
            for ret in asset_returns:
                if ret is not None:
                    try:
                        clean_returns.append(float(ret))
                    except (ValueError, TypeError):
                        continue
            
            if len(clean_returns) > 12:  # Only include series with enough data
                all_series[f"assets_{asset_name}"] = clean_returns
    
    # Add reference series
    if 'reference' in returns_data and 'assets' in returns_data['reference']:
        for asset_name, asset_returns in returns_data['reference']['assets'].items():
            # Skip Cash since we're using it as risk-free rate
            if asset_name.lower() in ['cash', 'us cash', 't-bills']:
                continue
                
            # Filter out None values and convert to float
            clean_returns = []
            for ret in asset_returns:
                if ret is not None:
                    try:
                        clean_returns.append(float(ret))
                    except (ValueError, TypeError):
                        continue
            
            if len(clean_returns) > 12:  # Only include series with enough data
                all_series[f"reference_{asset_name}"] = clean_returns
    
    print(f"Found {len(all_series)} asset series to analyze")
    
    # Run comparisons
    results = []
    for i, (asset_name, asset_returns) in enumerate(all_series.items(), 1):
        print(f"Processing {i}/{len(all_series)}: {asset_name} ({len(asset_returns)} periods)")
        
        # Align returns with cash returns
        aligned_asset_returns, aligned_cash_returns = align_returns_with_cash(asset_returns, cash_returns)
        
        # Get corresponding dates for this asset (if available)
        asset_dates = None
        if dates and len(dates) >= len(aligned_asset_returns):
            asset_dates = dates[:len(aligned_asset_returns)]
        
        # Calculate JavaScript metrics
        js_metrics = run_js_calculation(asset_name, aligned_asset_returns, aligned_cash_returns, asset_dates)
        
        # Calculate Python metrics
        py_metrics = calculate_python_metrics(aligned_asset_returns, aligned_cash_returns, asset_name, asset_dates)
        
        # Compare metrics
        comparison = compare_metrics(js_metrics, py_metrics, asset_name)
        
        if comparison:
            results.append(comparison)
            # Show frequency detection results
            if js_metrics and py_metrics:
                js_freq = js_metrics.get('frequency', 'unknown')
                py_freq = py_metrics.get('frequency', 'unknown')
                js_periods = js_metrics.get('periodsPerYear', 0)
                py_periods = py_metrics.get('periodsPerYear', 0)
                print(f"  📊 Frequency: JS={js_freq}({js_periods}), PY={py_freq}({py_periods})")
        else:
            print(f"  ⚠️  Failed to calculate metrics for {asset_name}")
    
    # Convert to DataFrame and save to CSV
    if results:
        df = pd.DataFrame(results)
        
        # Round numeric columns to reasonable precision
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(6)
        
        # Save to CSV
        output_file = "returns_data_comparison.csv"
        df.to_csv(output_file, index=False)
        
        print(f"\n✅ Comparison complete! Results saved to {output_file}")
        print(f"Analyzed {len(results)} asset series")
        
        # Print frequency detection summary
        if 'frequency_js' in df.columns:
            freq_summary = df['frequency_js'].value_counts()
            print(f"\n📊 Frequency detection summary:")
            for freq, count in freq_summary.items():
                print(f"  {freq}: {count} series")
        
        # Print summary statistics
        print("\n📊 Summary of differences:")
        for metric in ['cagr', 'volatility', 'sharpe', 'sortino', 'maxDrawdown']:
            diff_col = f'{metric}_diff'
            pct_diff_col = f'{metric}_pct_diff'
            
            if diff_col in df.columns:
                mean_diff = df[diff_col].mean()
                max_diff = df[diff_col].abs().max()
                mean_pct_diff = df[pct_diff_col].mean()
                
                print(f"  {metric.upper():12}: Mean diff = {mean_diff:8.4f}, Max diff = {max_diff:8.4f}, Mean % diff = {mean_pct_diff:8.2f}%")
        
        # Show risk-free rate info
        if 'avg_cash_return_js' in df.columns:
            avg_rf_rate = df['avg_cash_return_js'].iloc[0] if len(df) > 0 else 0
            print(f"\n💰 Risk-free rate used: {avg_rf_rate:.3f}% monthly ({avg_rf_rate*12:.3f}% annualized)")
        
        # Show assets with largest differences
        print("\n🔍 Assets with largest Sharpe ratio differences:")
        sharpe_diff_col = 'sharpe_diff'
        if sharpe_diff_col in df.columns:
            top_diffs = df.nlargest(5, sharpe_diff_col)[['asset_name', 'frequency_js', 'sharpe_js', 'sharpe_py', 'sharpe_diff', 'total_periods']]
            for _, row in top_diffs.iterrows():
                print(f"  {row['asset_name']:30}: {row['frequency_js']:8} JS={row['sharpe_js']:6.3f}, PY={row['sharpe_py']:6.3f}, Diff={row['sharpe_diff']:6.3f} ({row['total_periods']} periods)")
    
    else:
        print("❌ No successful comparisons completed")

if __name__ == "__main__":
    main() 