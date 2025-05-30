/**
 * Backup of Embedded Calculation Functions from index_template.html
 * These functions were originally embedded in the Vue component methods
 * Created as backup before switching to external JS libraries
 */

// ====================================
// OPTIMIZATION FUNCTIONS
// ====================================

/**
 * Original embedded gradient descent optimization
 */
function backupGradientDescentOptimization() {
  // This would contain the original function from the HTML
  // Implementation moved to backup for reference
}

/**
 * Original embedded calculate objective function
 */
function backupCalculateObjectiveFunction(weights) {
  // Original implementation from HTML
}

/**
 * Original embedded calculate gradients
 */
function backupCalculateGradients(weights, stepSize) {
  // Original implementation from HTML
}

// ====================================
// PORTFOLIO METRICS FUNCTIONS
// ====================================

/**
 * Original embedded calculate metrics for returns
 */
function backupCalculateMetricsForReturns(returns) {
  if (!returns || returns.length === 0) {
    return { cagr: 0, volatility: 0, sharpe: 0, sortino: 0, cvar: 0, maxDrawdown: 0 };
  }
  
  // Convert monthly returns to decimal form
  const monthlyReturns = returns.map(r => r / 100);
  
  // Calculate annualized return (CAGR)
  const totalReturn = monthlyReturns.reduce((acc, ret) => acc * (1 + ret), 1);
  const years = returns.length / 12;
  const cagr = years > 0 ? (Math.pow(totalReturn, 1/years) - 1) * 100 : 0;
  
  // Calculate volatility (annualized standard deviation)
  const meanReturn = monthlyReturns.reduce((a, b) => a + b, 0) / monthlyReturns.length;
  const variance = monthlyReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 2), 0) / monthlyReturns.length;
  const volatility = Math.sqrt(variance * 12) * 100; // Annualized
  
  // Calculate Sharpe ratio (assuming 2% risk-free rate)
  const riskFreeRate = 0.02;
  const sharpe = volatility > 0 ? (cagr - riskFreeRate) / volatility : 0;
  
  // Calculate Sortino ratio (downside deviation)
  const downsideReturns = monthlyReturns.filter(ret => ret < meanReturn);
  const downsideVariance = downsideReturns.length > 0 ? 
    downsideReturns.reduce((acc, ret) => acc + Math.pow(ret - meanReturn, 2), 0) / downsideReturns.length : 0;
  const downsideDeviation = Math.sqrt(downsideVariance * 12) * 100;
  const sortino = downsideDeviation > 0 ? (cagr - riskFreeRate) / downsideDeviation : 0;
  
  // Calculate CVaR (5% worst returns)
  const sortedReturns = [...monthlyReturns].sort((a, b) => a - b);
  const cvarIndex = Math.floor(sortedReturns.length * 0.05);
  const cvar = cvarIndex > 0 ? 
    sortedReturns.slice(0, cvarIndex).reduce((a, b) => a + b, 0) / cvarIndex * 100 : 0;
  
  // Calculate maximum drawdown
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
    cagr: parseFloat(cagr.toFixed(2)),
    volatility: parseFloat(volatility.toFixed(2)),
    sharpe: parseFloat(sharpe.toFixed(2)),
    sortino: parseFloat(sortino.toFixed(2)),
    cvar: parseFloat(cvar.toFixed(2)),
    maxDrawdown: parseFloat((maxDrawdown * 100).toFixed(2))
  };
}

// ====================================
// UTILITY FUNCTIONS
// ====================================

/**
 * Original embedded is valid weight allocation
 */
function backupIsValidWeightAllocation(weights) {
  const sum = Object.values(weights).reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0);
  return Math.abs(sum - 100) < 0.01 && Object.values(weights).every(w => (parseFloat(w) || 0) >= 0);
}

/**
 * Original embedded is metric improvement
 */
function backupIsMetricImprovement(newMetric, currentBest) {
  if (this.optimizationObjective === 'risk' || this.optimizationObjective === 'cvar') {
    return newMetric < currentBest; // Lower is better for risk measures
  } else {
    return newMetric > currentBest; // Higher is better for return/ratio measures
  }
}

/**
 * Original embedded normalize weights
 */
function backupNormalizeWeights(weights) {
  const normalizedWeights = { ...weights };
  
  // Calculate sum and normalize
  const sum = Object.values(normalizedWeights).reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0);
  
  if (sum > 0) {
    Object.keys(normalizedWeights).forEach(asset => {
      normalizedWeights[asset] = (parseFloat(normalizedWeights[asset]) || 0) * 100 / sum;
    });
  }
  
  return normalizedWeights;
}

/**
 * Original embedded calculate portfolio returns
 */
function backupCalculatePortfolioReturns(indices, weights) {
  const returns = [];
  const totalWeight = Object.values(weights).reduce((sum, weight) => sum + parseFloat(weight || 0), 0);
  
  if (totalWeight === 0) return indices.map(() => 0);
  
  // Get filtered data based on current date range
  const filteredData = this.getFilteredReturnsData();
  
  if (!filteredData.assets) return indices.map(() => 0);
  
  indices.forEach(index => {
    let portfolioReturn = 0;
    let totalValidWeight = 0;
    
    Object.keys(weights).forEach(asset => {
      const weight = parseFloat(weights[asset]);
      if (weight > 0 && filteredData.assets[asset] && filteredData.assets[asset][index] !== null) {
        portfolioReturn += (weight / 100) * filteredData.assets[asset][index];
        totalValidWeight += weight;
      }
    });
    
    // Normalize if some assets were missing
    if (totalValidWeight > 0 && totalValidWeight !== 100) {
      portfolioReturn = portfolioReturn * (100 / totalValidWeight);
    }
    
    returns.push(portfolioReturn);
  });
  
  return returns;
}

/**
 * Original embedded calculate cumulative returns
 */
function backupCalculateCumulativeReturns(returns) {
  if (!returns || returns.length === 0) return [];
  
  let cumulative = 0;
  const result = [];
  
  for (let i = 0; i < returns.length; i++) {
    if (i === 0) {
      result.push(0);
    } else {
      cumulative = (1 + cumulative / 100) * (1 + returns[i-1] / 100) * 100 - 100;
      result.push(cumulative);
    }
  }
  
  return result;
}

// Note: This file serves as a backup of the original embedded functions
// before they were replaced with calls to external JS libraries 