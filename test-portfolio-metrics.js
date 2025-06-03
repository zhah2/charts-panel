/**
 * Unit tests for portfolio metrics functions
 * Run with: node test-portfolio-metrics.js
 */

const PortfolioMetrics = require('./portfolio-metrics.js');

// Sample test data (monthly returns as percentages)
const sampleReturns = [
  1.2, -0.5, 2.1, 0.8, -1.2, 3.4, 0.2, -0.8, 1.5, 2.3, -0.3, 1.1,
  2.1, 0.4, -1.1, 1.8, 0.9, -2.1, 1.7, 0.6, -0.4, 1.3, 2.5, 0.7,
  -0.8, 1.4, 2.0, -0.6, 1.1, 0.3, -1.5, 2.2, 0.9, 1.6, -0.2, 1.0
];

const benchmarkReturns = [
  1.0, -0.3, 1.8, 0.6, -1.0, 3.0, 0.0, -0.6, 1.2, 2.0, -0.1, 0.9,
  1.8, 0.2, -0.9, 1.5, 0.7, -1.8, 1.4, 0.4, -0.2, 1.0, 2.2, 0.5,
  -0.6, 1.2, 1.7, -0.4, 0.9, 0.1, -1.2, 1.9, 0.7, 1.3, 0.0, 0.8
];

// Test functions
function testCalculateMetricsForReturns() {
  console.log('\n=== Testing calculateMetricsForReturns ===');
  
  const metrics = PortfolioMetrics.calculateMetricsForReturns(sampleReturns);
  
  console.log('Results:');
  console.log(`CAGR: ${metrics.cagr}%`);
  console.log(`Volatility: ${metrics.volatility}%`);
  console.log(`Sharpe Ratio: ${metrics.sharpe}`);
  console.log(`Sortino Ratio: ${metrics.sortino}`);
  console.log(`CVaR (5%): ${metrics.cvar}%`);
  console.log(`Max Drawdown: ${metrics.maxDrawdown}%`);
  
  // Basic validation
  console.log('\nValidation:');
  console.log(`✓ CAGR is number: ${typeof metrics.cagr === 'number'}`);
  console.log(`✓ Volatility > 0: ${metrics.volatility > 0}`);
  console.log(`✓ All metrics defined: ${Object.values(metrics).every(v => v !== undefined)}`);
}

function testCalculateCumulativeReturns() {
  console.log('\n=== Testing calculateCumulativeReturns ===');
  
  const cumulative = PortfolioMetrics.calculateCumulativeReturns(sampleReturns.slice(0, 12));
  
  console.log('First 12 months cumulative returns:');
  cumulative.forEach((ret, i) => {
    console.log(`Month ${i + 1}: ${ret.toFixed(2)}%`);
  });
  
  console.log('\nValidation:');
  console.log(`✓ Starts at 0: ${cumulative[0] === 0}`);
  console.log(`✓ Length matches input: ${cumulative.length === 12}`);
  console.log(`✓ All numbers: ${cumulative.every(v => typeof v === 'number')}`);
}

function testCalculatePortfolioReturns() {
  console.log('\n=== Testing calculatePortfolioReturns ===');
  
  // Sample portfolio weights
  const weights = {
    'Asset A': 60,
    'Asset B': 40
  };
  
  // Sample asset returns (first 12 months)
  const assetReturns = {
    'Asset A': sampleReturns.slice(0, 12),
    'Asset B': benchmarkReturns.slice(0, 12)
  };
  
  const indices = Array.from({length: 12}, (_, i) => i);
  const portfolioReturns = PortfolioMetrics.calculatePortfolioReturns(weights, assetReturns, indices);
  
  console.log('Portfolio returns for first 12 months:');
  portfolioReturns.forEach((ret, i) => {
    console.log(`Month ${i + 1}: ${ret.toFixed(3)}%`);
  });
  
  console.log('\nValidation:');
  console.log(`✓ Length matches indices: ${portfolioReturns.length === 12}`);
  console.log(`✓ All numbers: ${portfolioReturns.every(v => typeof v === 'number')}`);
}

function testNormalizeWeights() {
  console.log('\n=== Testing normalizeWeights ===');
  
  const originalWeights = {
    'Asset A': 45.5,
    'Asset B': 30.2,
    'Asset C': 24.1
  };
  
  console.log('Original weights:', originalWeights);
  console.log('Original sum:', Object.values(originalWeights).reduce((a, b) => a + b, 0));
  
  const normalizedWeights = PortfolioMetrics.normalizeWeights(originalWeights);
  
  console.log('Normalized weights:', normalizedWeights);
  console.log('Normalized sum:', Object.values(normalizedWeights).reduce((a, b) => parseFloat(a) + parseFloat(b), 0));
  
  const sum = Object.values(normalizedWeights).reduce((a, b) => parseFloat(a) + parseFloat(b), 0);
  console.log('\nValidation:');
  console.log(`✓ Sums to 100%: ${Math.abs(sum - 100) < 0.01}`);
}

function testCalculateAdditionalMetrics() {
  console.log('\n=== Testing calculateAdditionalMetrics ===');
  
  const additionalMetrics = PortfolioMetrics.calculateAdditionalMetrics(sampleReturns, benchmarkReturns);
  
  console.log('Additional metrics:');
  console.log(`Skewness: ${additionalMetrics.skewness}`);
  console.log(`Kurtosis: ${additionalMetrics.kurtosis}`);
  console.log(`VaR 95%: ${additionalMetrics.var95}%`);
  console.log(`VaR 99%: ${additionalMetrics.var99}%`);
  console.log(`Beta: ${additionalMetrics.beta}`);
  console.log(`Alpha: ${additionalMetrics.alpha}%`);
  
  console.log('\nValidation:');
  console.log(`✓ All metrics defined: ${Object.values(additionalMetrics).every(v => v !== undefined)}`);
  console.log(`✓ Beta > 0: ${additionalMetrics.beta > 0}`);
}

function compareWithQuantstatsFormat() {
  console.log('\n=== Format for Quantstats Comparison ===');
  
  // Calculate metrics using our functions
  const metrics = PortfolioMetrics.calculateMetricsForReturns(sampleReturns);
  const additionalMetrics = PortfolioMetrics.calculateAdditionalMetrics(sampleReturns, benchmarkReturns);
  
  // Output in format similar to quantstats
  console.log('\nPortfolio Metrics (for comparison with Python quantstats):');
  console.log('==========================================');
  console.log(`Total Return [%]        ${((Math.pow(1 + metrics.cagr/100, 3) - 1) * 100).toFixed(2)}`); // 3 years
  console.log(`CAGR [%]                ${metrics.cagr}`);
  console.log(`Volatility [%]          ${metrics.volatility}`);
  console.log(`Sharpe                  ${metrics.sharpe}`);
  console.log(`Sortino                 ${metrics.sortino}`);
  console.log(`Max Drawdown [%]        ${metrics.maxDrawdown}`);
  console.log(`CVaR [%]                ${metrics.cvar}`);
  console.log(`Skewness                ${additionalMetrics.skewness}`);
  console.log(`Kurtosis                ${additionalMetrics.kurtosis}`);
  console.log(`VaR (95%) [%]           ${additionalMetrics.var95}`);
  console.log(`VaR (99%) [%]           ${additionalMetrics.var99}`);
  console.log(`Beta                    ${additionalMetrics.beta}`);
  console.log(`Alpha [%]               ${additionalMetrics.alpha}`);
  
  // Output sample data for Python comparison
  console.log('\n=== Sample Data for Python Testing ===');
  console.log('Returns (monthly %):', JSON.stringify(sampleReturns));
  console.log('Benchmark (monthly %):', JSON.stringify(benchmarkReturns));
}

// Run all tests
function runAllTests() {
  console.log('Portfolio Metrics Unit Tests');
  console.log('============================');
  
  testCalculateMetricsForReturns();
  testCalculateCumulativeReturns();
  testCalculatePortfolioReturns();
  testNormalizeWeights();
  testCalculateAdditionalMetrics();
  compareWithQuantstatsFormat();
  
  console.log('\n✅ All tests completed!');
  console.log('\nTo compare with Python quantstats:');
  console.log('1. Install quantstats: pip install quantstats');
  console.log('2. Use the sample data arrays printed above');
  console.log('3. Convert monthly % returns to decimal (divide by 100)');
  console.log('4. Create pandas Series with monthly frequency');
  console.log('5. Run quantstats.stats.* functions');
}

// Export test functions for external use
if (require.main === module) {
  runAllTests();
} else {
  module.exports = {
    testCalculateMetricsForReturns,
    testCalculateCumulativeReturns,
    testCalculatePortfolioReturns,
    testNormalizeWeights,
    testCalculateAdditionalMetrics,
    compareWithQuantstatsFormat,
    sampleReturns,
    benchmarkReturns
  };
} 