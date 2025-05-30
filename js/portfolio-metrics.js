/**
 * Portfolio Metrics and Optimization Functions
 * Pure JavaScript functions for portfolio analysis and optimization
 * Extracted for unit testing and comparison with Python quantstats
 */

/**
 * Detect the frequency of a time series based on data length and typical patterns
 * @param {number[]} returns - Array of returns
 * @param {string[]} dates - Array of date strings (optional, for better detection)
 * @returns {Object} Frequency info with periods per year and name
 */
function detectFrequency(returns, dates = null) {
  const dataLength = returns.length;
  
  // If we have dates, try to detect from date intervals
  if (dates && dates.length >= 2) {
    try {
      const date1 = new Date(dates[0]);
      const date2 = new Date(dates[1]);
      const daysDiff = Math.abs((date2 - date1) / (1000 * 60 * 60 * 24));
      
      if (daysDiff <= 1.5) return { periods: 252, name: 'daily', factor: Math.sqrt(252) };
      if (daysDiff <= 8) return { periods: 52, name: 'weekly', factor: Math.sqrt(52) };
      if (daysDiff <= 35) return { periods: 12, name: 'monthly', factor: Math.sqrt(12) };
      if (daysDiff <= 100) return { periods: 4, name: 'quarterly', factor: Math.sqrt(4) };
      return { periods: 1, name: 'annual', factor: 1 };
    } catch (e) {
      // Fall back to heuristic detection
    }
  }
  
  // Heuristic detection based on data length
  // Assume reasonable time spans for different frequencies
  if (dataLength > 1000) return { periods: 252, name: 'daily', factor: Math.sqrt(252) };
  if (dataLength > 200) return { periods: 52, name: 'weekly', factor: Math.sqrt(52) };
  if (dataLength > 50) return { periods: 12, name: 'monthly', factor: Math.sqrt(12) };
  if (dataLength > 10) return { periods: 4, name: 'quarterly', factor: Math.sqrt(4) };
  return { periods: 1, name: 'annual', factor: 1 };
}

/**
 * Calculate comprehensive portfolio metrics for returns
 * @param {number[]} returns - Array of monthly returns (as percentages)
 * @param {number} riskFreeRate - Annual risk-free rate (as decimal, e.g., 0.02 for 2%)
 * @param {string[]} dates - Array of date strings for frequency detection (optional)
 * @returns {Object} Portfolio metrics
 */
function calculateMetricsForReturns(returns, riskFreeRate = 0.02, dates = null) {
  if (!returns || returns.length === 0) {
    return { cagr: 0, volatility: 0, sharpe: 0, sortino: 0, cvar: 0, maxDrawdown: 0 };
  }
  
  // Detect frequency
  const frequency = detectFrequency(returns, dates);
  const periodsPerYear = frequency.periods;
  const volatilityFactor = frequency.factor;
  
  // Convert returns to decimal form
  const monthlyReturns = returns.map(r => r / 100);
  const meanReturn = monthlyReturns.reduce((a, b) => a + b, 0) / monthlyReturns.length;
  
  // Calculate CAGR (Compound Annual Growth Rate)
  const totalReturn = monthlyReturns.reduce((acc, ret) => acc * (1 + ret), 1);
  const years = returns.length / periodsPerYear;
  const cagr = years > 0 ? (Math.pow(totalReturn, 1/years) - 1) * 100 : 0;
  
  // Calculate annualized volatility (using sample variance, ddof=1)
  const variance = monthlyReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 2), 0) / (monthlyReturns.length - 1);
  const volatility = Math.sqrt(variance) * volatilityFactor * 100;
  
  // Calculate Sharpe ratio (matching quantstats implementation exactly)
  // QuantStats formula: (mean_excess_return * periods) / (std_returns * sqrt(periods))
  const periodicRiskFreeRate = riskFreeRate / periodsPerYear;
  const excessReturns = monthlyReturns.map(ret => ret - periodicRiskFreeRate);
  const meanExcessReturn = excessReturns.reduce((a, b) => a + b, 0) / excessReturns.length;
  
  // Use standard deviation of original returns (not excess returns) - this is key for quantstats compatibility
  const returnsStdDev = Math.sqrt(variance);
  const sharpe = returnsStdDev > 0 ? (meanExcessReturn * periodsPerYear) / (returnsStdDev * volatilityFactor) : 0;
  
  // Calculate Sortino ratio (matching quantstats implementation)
  // QuantStats uses downside deviation relative to risk-free rate as target
  const downsideReturns = monthlyReturns.filter(ret => ret < periodicRiskFreeRate);
  let downsideDeviation = 0;
  
  if (downsideReturns.length > 0) {
    // Calculate downside deviation: sqrt(mean((returns - target)^2)) for returns < target
    const downsideSquaredDeviations = downsideReturns.map(ret => Math.pow(ret - periodicRiskFreeRate, 2));
    const downsideVariance = downsideSquaredDeviations.reduce((a, b) => a + b, 0) / downsideReturns.length;
    downsideDeviation = Math.sqrt(downsideVariance) * volatilityFactor;
  }
  
  const sortino = downsideDeviation > 0 ? (meanExcessReturn * periodsPerYear) / downsideDeviation : 0;
  
  // Calculate CVaR (Conditional Value at Risk) at 5% level
  const sortedReturns = [...monthlyReturns].sort((a, b) => a - b);
  const cvarIndex = Math.floor(sortedReturns.length * 0.05);
  const cvar = cvarIndex > 0 ? 
    sortedReturns.slice(0, cvarIndex).reduce((a, b) => a + b, 0) / cvarIndex * 100 : 0;
  
  // Calculate Maximum Drawdown
  let peak = 1;
  let maxDrawdown = 0;
  let cumulative = 1;
  
  monthlyReturns.forEach(ret => {
    cumulative *= (1 + ret);
    if (cumulative > peak) peak = cumulative;
    const drawdown = (peak - cumulative) / peak;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
  });
  
  return {
    cagr: cagr,
    volatility: volatility,
    sharpe: sharpe,
    sortino: sortino,
    cvar: cvar,
    maxDrawdown: maxDrawdown * 100,
    frequency: frequency.name,
    periodsPerYear: periodsPerYear
  };
}

/**
 * Calculate cumulative returns from a series of periodic returns
 * @param {number[]} returns - Array of periodic returns (as percentages)
 * @returns {number[]} Array of cumulative returns starting from 0%
 */
function calculateCumulativeReturns(returns) {
  if (!returns || returns.length === 0) return [];
  
  let cumulative = 0;
  const result = [];
  
  for (let i = 0; i < returns.length; i++) {
    if (i === 0) {
      // First period starts at 0%
      result.push(0);
    } else {
      // Calculate cumulative return from previous period
      cumulative = (1 + cumulative / 100) * (1 + returns[i-1] / 100) * 100 - 100;
      result.push(cumulative);
    }
  }
  
  return result;
}

/**
 * Calculate portfolio returns based on asset weights and individual asset returns
 * @param {Object} weights - Object with asset names as keys and weights as values (0-100)
 * @param {Object} assetReturns - Object with asset names as keys and return arrays as values
 * @param {number[]} indices - Array of indices to use from the return series
 * @returns {number[]} Array of portfolio returns
 */
function calculatePortfolioReturns(weights, assetReturns, indices) {
  const returns = [];
  const totalWeight = Object.values(weights).reduce((sum, weight) => sum + parseFloat(weight || 0), 0);
  
  if (totalWeight === 0) return indices.map(() => 0);
  
  // Pre-filter assets with non-zero weights for efficiency
  const activeAssets = Object.keys(weights).filter(asset => {
    const weight = parseFloat(weights[asset] || 0);
    return weight > 0 && assetReturns[asset];
  });
  
  if (activeAssets.length === 0) return indices.map(() => 0);
  
  indices.forEach(index => {
    let portfolioReturn = 0;
    
    activeAssets.forEach(asset => {
      const weight = parseFloat(weights[asset]);
      const assetReturn = assetReturns[asset][index];
      // Only include if asset return is not null/undefined
      if (assetReturn !== null && assetReturn !== undefined) {
        portfolioReturn += (weight / 100) * assetReturn;
      }
    });
    
    returns.push(portfolioReturn);
  });
  
  return returns;
}

/**
 * Normalize portfolio weights to sum to exactly 100%
 * @param {Object} weights - Object with asset names as keys and weights as values
 * @returns {Object} Normalized weights object
 */
function normalizeWeights(weights) {
  const normalizedWeights = { ...weights };
  
  // Calculate sum and normalize
  const sum = Object.values(normalizedWeights).reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0);
  
  if (sum > 0) {
    // First, normalize and round all weights
    Object.keys(normalizedWeights).forEach(asset => {
      normalizedWeights[asset] = parseFloat(((parseFloat(normalizedWeights[asset]) || 0) / sum) * 100).toFixed(1);
    });
    
    // Calculate the difference from 100.0%
    const roundedSum = Object.values(normalizedWeights).reduce((a, b) => parseFloat(a) + parseFloat(b), 0);
    const difference = parseFloat((100.0 - roundedSum).toFixed(1));
    
    // If there's a difference, adjust the largest weight
    if (Math.abs(difference) > 0) {
      // Find the asset with the largest weight to adjust
      let largestAsset = null;
      let largestWeight = -1;
      Object.keys(normalizedWeights).forEach(asset => {
        const weight = parseFloat(normalizedWeights[asset]);
        if (weight > largestWeight) {
          largestWeight = weight;
          largestAsset = asset;
        }
      });
      
      // Adjust the largest weight to make the total exactly 100.0%
      if (largestAsset) {
        normalizedWeights[largestAsset] = parseFloat((parseFloat(normalizedWeights[largestAsset]) + difference).toFixed(1));
      }
    }
  }
  
  return normalizedWeights;
}

/**
 * Calculate additional risk metrics for comparison with quantstats
 * @param {number[]} returns - Array of monthly returns (as percentages)
 * @param {number[]} benchmarkReturns - Array of benchmark returns (optional)
 * @param {string[]} dates - Array of date strings for frequency detection (optional)
 * @returns {Object} Additional risk metrics
 */
function calculateAdditionalMetrics(returns, benchmarkReturns = null, dates = null) {
  if (!returns || returns.length === 0) {
    return { skewness: 0, kurtosis: 0, var95: 0, var99: 0, beta: 0, alpha: 0 };
  }
  
  // Detect frequency
  const frequency = detectFrequency(returns, dates);
  const periodsPerYear = frequency.periods;
  
  const monthlyReturns = returns.map(r => r / 100);
  const meanReturn = monthlyReturns.reduce((a, b) => a + b, 0) / monthlyReturns.length;
  const n = monthlyReturns.length;
  
  // Calculate skewness (using sample variance, ddof=1)
  const cubed = monthlyReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 3), 0) / (n - 1);
  const variance = monthlyReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 2), 0) / (n - 1);
  const skewness = cubed / Math.pow(variance, 3/2);
  
  // Calculate kurtosis (using sample variance, ddof=1)
  const fourth = monthlyReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 4), 0) / (n - 1);
  const kurtosis = (fourth / Math.pow(variance, 2)) - 3; // Excess kurtosis
  
  // Calculate VaR (Value at Risk)
  const sortedReturns = [...monthlyReturns].sort((a, b) => a - b);
  const var95Index = Math.floor(sortedReturns.length * 0.05);
  const var99Index = Math.floor(sortedReturns.length * 0.01);
  const var95 = var95Index > 0 ? sortedReturns[var95Index] * 100 : 0;
  const var99 = var99Index > 0 ? sortedReturns[var99Index] * 100 : 0;
  
  // Calculate Beta and Alpha (if benchmark provided)
  let beta = 0;
  let alpha = 0;
  if (benchmarkReturns && benchmarkReturns.length === returns.length) {
    const benchmarkDecimal = benchmarkReturns.map(r => r / 100);
    const benchmarkMean = benchmarkDecimal.reduce((a, b) => a + b, 0) / benchmarkDecimal.length;
    
    const covariance = monthlyReturns.reduce((acc, ret, i) => 
      acc + (ret - meanReturn) * (benchmarkDecimal[i] - benchmarkMean), 0) / (n - 1);
    const benchmarkVariance = benchmarkDecimal.reduce((acc, ret) => 
      acc + Math.pow(ret - benchmarkMean, 2), 0) / (n - 1);
    
    beta = benchmarkVariance > 0 ? covariance / benchmarkVariance : 0;
    alpha = (meanReturn - beta * benchmarkMean) * periodsPerYear * 100; // Annualized alpha in percentage
  }
  
  return {
    skewness: skewness,
    kurtosis: kurtosis,
    var95: var95,
    var99: var99,
    beta: beta,
    alpha: alpha,
    frequency: frequency.name,
    periodsPerYear: periodsPerYear
  };
}

/**
 * Simple optimization function using random search (for demonstration)
 * In practice, this would use more sophisticated optimization algorithms
 * @param {Object} config - Optimization configuration
 * @returns {Object} Optimized weights
 */
function optimizePortfolio(config) {
  const {
    assets,
    returns,
    objective = 'sharpe',
    iterations = 1000,
    constraints = {}
  } = config;
  
  let bestWeights = {};
  let bestScore = objective === 'risk' ? Infinity : -Infinity;
  
  // Initialize with equal weights
  const numAssets = assets.length;
  assets.forEach(asset => {
    bestWeights[asset] = 100 / numAssets;
  });
  
  // Random search optimization
  for (let i = 0; i < iterations; i++) {
    // Generate random weights
    const weights = {};
    const randomWeights = assets.map(() => Math.random());
    const sum = randomWeights.reduce((a, b) => a + b, 0);
    
    assets.forEach((asset, index) => {
      weights[asset] = (randomWeights[index] / sum) * 100;
    });
    
    // Apply constraints (simplified)
    // In practice, this would be more sophisticated
    
    // Calculate portfolio returns and metrics
    const portfolioReturns = calculatePortfolioReturns(weights, returns, 
      Array.from({length: returns[assets[0]]?.length || 0}, (_, i) => i));
    
    if (portfolioReturns.length === 0) continue;
    
    const metrics = calculateMetricsForReturns(portfolioReturns);
    
    // Calculate score based on objective
    let score;
    switch (objective) {
      case 'sharpe':
        score = metrics.sharpe;
        break;
      case 'risk':
        score = -metrics.volatility; // Negative because we want to minimize
        break;
      case 'sortino':
        score = metrics.sortino;
        break;
      case 'cvar':
        score = -metrics.cvar; // Negative because we want to minimize
        break;
      default:
        score = metrics.sharpe;
    }
    
    // Update best weights if score improved
    const isImprovement = objective === 'risk' ? score > bestScore : score > bestScore;
    if (isImprovement) {
      bestScore = score;
      bestWeights = { ...weights };
    }
  }
  
  return normalizeWeights(bestWeights);
}

// Export functions for Node.js testing environment
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    detectFrequency,
    calculateMetricsForReturns,
    calculateCumulativeReturns,
    calculatePortfolioReturns,
    normalizeWeights,
    calculateAdditionalMetrics,
    optimizePortfolio
  };
}

// Export functions for browser environment
if (typeof window !== 'undefined') {
  window.PortfolioMetrics = {
    detectFrequency,
    calculateMetricsForReturns,
    calculateCumulativeReturns,
    calculatePortfolioReturns,
    normalizeWeights,
    calculateAdditionalMetrics,
    optimizePortfolio
  };
} 