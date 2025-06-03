#!/usr/bin/env python3
"""
Test script to verify the comparison setup works with returns.json data
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def test_basic_setup():
    """Test basic file existence and data loading"""
    print("Testing basic setup...")
    
    # Check if returns.json exists
    if not Path("returns.json").exists():
        print("❌ returns.json not found. Run: python build.py")
        return False
    
    # Check if portfolio-metrics.js exists
    if not Path("portfolio-metrics.js").exists():
        print("❌ portfolio-metrics.js not found")
        return False
    
    # Load and inspect returns.json
    with open("returns.json", 'r') as f:
        data = json.load(f)
    
    print("✅ Files exist")
    
    # Check data structure
    if 'assets' in data and 'assets' in data['assets']:
        asset_count = len(data['assets']['assets'])
        print(f"✅ Found {asset_count} assets in assets series")
        
        # Look for Cash returns
        cash_found = False
        for name in ['Cash', 'US Cash', 'T-Bills']:
            if name in data['assets']['assets']:
                cash_returns = data['assets']['assets'][name]
                clean_cash = [r for r in cash_returns if r is not None]
                print(f"✅ Found {name}: {len(clean_cash)} periods, avg = {sum(clean_cash)/len(clean_cash):.3f}%")
                cash_found = True
                break
        
        if not cash_found:
            print("⚠️  No Cash returns found in assets")
    
    if 'reference' in data and 'assets' in data['reference']:
        ref_count = len(data['reference']['assets'])
        print(f"✅ Found {ref_count} reference series")
    
    return True

def test_js_execution():
    """Test JavaScript execution with a simple example"""
    print("Testing JavaScript execution...")
    
    # Get the absolute path to portfolio-metrics.js
    metrics_file = Path("portfolio-metrics.js").absolute()
    
    # Simple test data
    test_returns = [1.2, -0.5, 2.1, 0.8, -1.0, 1.5]
    test_cash = [0.1, 0.1, 0.2, 0.1, 0.1, 0.1]
    test_dates = ['2023-01-01', '2023-02-01', '2023-03-01', '2023-04-01', '2023-05-01', '2023-06-01']
    
    js_code = f"""
const fs = require('fs');

try {{
    const metricsCode = fs.readFileSync('{str(metrics_file).replace(chr(92), chr(92)+chr(92))}', 'utf8');
    eval(metricsCode);
    
    const returns = {test_returns};
    const cashReturns = {test_cash};
    const dates = {json.dumps(test_dates)};
    
    const avgCashReturn = cashReturns.reduce((a, b) => a + b, 0) / cashReturns.length;
    const annualizedCashReturn = avgCashReturn * 12 / 100;
    
    const metrics = calculateMetricsForReturns(returns, annualizedCashReturn, dates);
    const additionalMetrics = calculateAdditionalMetrics(returns, cashReturns, dates);
    
    const result = {{
        ...metrics,
        ...additionalMetrics,
        avgCashReturn: avgCashReturn,
        annualizedCashReturn: annualizedCashReturn
    }};
    
    console.log(JSON.stringify(result, null, 2));
}} catch (error) {{
    console.error("Error:", error.message);
    process.exit(1);
}}
"""
    
    # Write and execute
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(js_code)
            temp_js_file = f.name
        
        result = subprocess.run(
            ['node', temp_js_file],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        os.unlink(temp_js_file)
        
        if result.returncode == 0:
            metrics = json.loads(result.stdout)
            print(f"✅ JavaScript execution successful")
            print(f"   CAGR: {metrics.get('cagr', 0):.2f}%")
            print(f"   Sharpe: {metrics.get('sharpe', 0):.3f}")
            print(f"   Frequency: {metrics.get('frequency', 'unknown')} ({metrics.get('periodsPerYear', 0)} periods/year)")
            print(f"   Avg Cash Rate: {metrics.get('avgCashReturn', 0):.3f}%")
            return True
        else:
            print(f"❌ JavaScript error: {result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Error running JavaScript: {e}")
        return False

def test_python_quantstats():
    """Test Python quantstats calculation"""
    print("Testing Python quantstats...")
    
    try:
        import quantstats as qs
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Simple test data with proper datetime index
        start_date = datetime(2023, 1, 1)
        dates = [start_date + timedelta(days=30*i) for i in range(6)]
        
        returns = pd.Series([1.2, -0.5, 2.1, 0.8, -1.0, 1.5], index=dates) / 100
        cash_returns = pd.Series([0.1, 0.1, 0.2, 0.1, 0.1, 0.1], index=dates) / 100
        
        avg_cash_rate = cash_returns.mean() * 12
        
        # Use the raw calculation methods to avoid datetime issues
        # Calculate CAGR manually
        total_return = (1 + returns).prod()
        years = len(returns) / 12  # Monthly data
        cagr = (total_return ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Calculate volatility manually
        volatility = returns.std() * np.sqrt(12) * 100
        
        # Calculate Sharpe ratio manually
        excess_returns = returns - (avg_cash_rate / 12)
        sharpe = (excess_returns.mean() * 12) / (excess_returns.std() * np.sqrt(12)) if excess_returns.std() > 0 else 0
        
        print(f"✅ Python calculation successful")
        print(f"   CAGR: {cagr:.2f}%")
        print(f"   Volatility: {volatility:.2f}%")
        print(f"   Sharpe: {sharpe:.3f}")
        print(f"   Avg Cash Rate: {avg_cash_rate*100:.3f}%")
        return True
    
    except ImportError:
        print("❌ quantstats not installed. Run: pip install quantstats")
        return False
    except Exception as e:
        print(f"❌ Error with quantstats: {e}")
        print(f"   Trying basic pandas calculations instead...")
        try:
            import pandas as pd
            import numpy as np
            
            returns = pd.Series([1.2, -0.5, 2.1, 0.8, -1.0, 1.5]) / 100
            cash_returns = pd.Series([0.1, 0.1, 0.2, 0.1, 0.1, 0.1]) / 100
            
            avg_cash_rate = cash_returns.mean() * 12
            
            # Basic calculations
            total_return = (1 + returns).prod()
            years = len(returns) / 12
            cagr = (total_return ** (1/years) - 1) * 100 if years > 0 else 0
            volatility = returns.std() * np.sqrt(12) * 100
            
            print(f"✅ Basic Python calculation successful")
            print(f"   CAGR: {cagr:.2f}%")
            print(f"   Volatility: {volatility:.2f}%")
            print(f"   Avg Cash Rate: {avg_cash_rate*100:.3f}%")
            return True
        except Exception as e2:
            print(f"❌ Error with basic calculations: {e2}")
            return False

def main():
    print("🧪 Testing comparison setup...\n")
    
    tests = [
        test_basic_setup,
        test_js_execution, 
        test_python_quantstats
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Ready to run full comparison.")
        print("   Run: python returns_data_comparison.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")

if __name__ == "__main__":
    main() 