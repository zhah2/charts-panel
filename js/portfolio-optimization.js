/**
 * Portfolio Optimization Library
 * Contains gradient descent optimization and related mathematical functions
 */

class PortfolioOptimizer {
  constructor(options = {}) {
    this.stepSize = options.stepSize || 0.1; // Gradient descent step size (%)
    this.maxIterations = options.maxIterations || 100;
    this.tolerance = options.tolerance || 1e-6;
    this.maxStagnation = options.maxStagnation || 10;
  }

  /**
   * Main gradient descent optimization function
   * @param {Object} weights - Initial portfolio weights
   * @param {string} objective - Optimization objective ('sharpe', 'risk', 'sortino', 'cvar')
   * @param {Function} calculateMetrics - Function to calculate portfolio metrics
   * @param {number} turnoverLimit - Maximum portfolio weight change allowed (%)
   * @returns {Object} Optimization result
   */
  gradientDescentOptimization(weights, objective, calculateMetrics, turnoverLimit = 1.0) {
    try {
      const turnoverLimitPercent = parseFloat(turnoverLimit);
      const stepSize = parseFloat(this.stepSize); // Gradient descent step size
      const maxIterations = Math.floor(turnoverLimitPercent / stepSize);
      
      let currentWeights = { ...weights };
      Object.keys(currentWeights).forEach(asset => {
        currentWeights[asset] = parseFloat(currentWeights[asset]) || 0;
      });
      
      const initialMetric = this.calculateObjectiveFunction(currentWeights, objective, calculateMetrics);
      let bestMetric = initialMetric;
      let bestWeights = { ...currentWeights };
      
      // Track total changes to respect turnover limit
      let totalChanges = {};
      Object.keys(weights).forEach(asset => {
        totalChanges[asset] = 0;
      });
      
      let iteration = 0;
      let stagnationCount = 0;
      
      while (iteration < maxIterations && stagnationCount < this.maxStagnation) {
        const gradients = this.calculateGradients(currentWeights, stepSize, objective, calculateMetrics);
        
        if (!gradients || Object.keys(gradients).length === 0) {
          break;
        }
        
        const sortedAssets = Object.keys(gradients).sort((a, b) => gradients[b] - gradients[a]);
        const assetsToIncrease = sortedAssets.filter(asset => gradients[asset] > 0);
        const assetsToDecrease = sortedAssets.filter(asset => gradients[asset] < 0);
        
        if (assetsToIncrease.length === 0 || assetsToDecrease.length === 0) {
          stagnationCount++;
          iteration++;
          continue;
        }
        
        // Check if we can still make changes within turnover limit
        const canIncrease = assetsToIncrease.some(asset => 
          Math.abs(totalChanges[asset]) < turnoverLimitPercent && currentWeights[asset] < 100
        );
        const canDecrease = assetsToDecrease.some(asset => 
          Math.abs(totalChanges[asset]) < turnoverLimitPercent && currentWeights[asset] > 0
        );
        
        if (!canIncrease || !canDecrease) {
          break; // Reached turnover limit
        }
        
        let improved = false;
        
        for (const asset of assetsToIncrease) {
          if (Math.abs(totalChanges[asset]) < turnoverLimitPercent && 
              currentWeights[asset] < 100 && 
              currentWeights[asset] + stepSize <= 100) {
            
            for (const decreaseAsset of assetsToDecrease) {
              if (Math.abs(totalChanges[decreaseAsset]) < turnoverLimitPercent && 
                  currentWeights[decreaseAsset] > 0 && 
                  currentWeights[decreaseAsset] - stepSize >= 0) {
                
                const newWeights = { ...currentWeights };
                newWeights[asset] += stepSize;
                newWeights[decreaseAsset] -= stepSize;
                
                if (this.isValidWeightAllocation(newWeights)) {
                  const newMetric = this.calculateObjectiveFunction(newWeights, objective, calculateMetrics);
                  
                  if (this.isMetricImprovement(newMetric, bestMetric, objective)) {
                    currentWeights = newWeights;
                    bestMetric = newMetric;
                    bestWeights = { ...newWeights };
                    
                    totalChanges[asset] += stepSize;
                    totalChanges[decreaseAsset] -= stepSize;
                    
                    improved = true;
                    stagnationCount = 0;
                    break;
                  }
                }
              }
            }
            
            if (improved) break;
          }
        }
        
        if (!improved) {
          stagnationCount++;
        }
        
        iteration++;
      }
      
      const finalWeights = this.normalizeWeights(bestWeights);
      
      return {
        success: true,
        weights: finalWeights,
        initialMetric: initialMetric,
        finalMetric: bestMetric,
        iterations: iteration,
        improvement: bestMetric - initialMetric
      };
      
    } catch (error) {
      console.error('Gradient descent optimization failed:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Calculate gradients using finite differences
   * @param {Object} weights - Portfolio weights
   * @param {number} stepSize - Gradient calculation step size (internal, not user turnover limit)
   * @param {string} objective - Optimization objective
   * @param {Function} calculateMetrics - Metrics calculation function
   * @returns {Object} Gradients for each asset
   */
  calculateGradients(weights, stepSize, objective, calculateMetrics) {
    const gradients = {};
    const baseMetric = this.calculateObjectiveFunction(weights, objective, calculateMetrics);
    
    Object.keys(weights).forEach(asset => {
      const perturbedWeights = { ...weights };
      
      let decreaseAsset = null;
      for (const otherAsset of Object.keys(weights)) {
        if (otherAsset !== asset && perturbedWeights[otherAsset] >= stepSize) {
          decreaseAsset = otherAsset;
          break;
        }
      }
      
      if (decreaseAsset && perturbedWeights[asset] + stepSize <= 100) {
        perturbedWeights[asset] += stepSize;
        perturbedWeights[decreaseAsset] -= stepSize;
        
        if (this.isValidWeightAllocation(perturbedWeights)) {
          const perturbedMetric = this.calculateObjectiveFunction(perturbedWeights, objective, calculateMetrics);
          gradients[asset] = (perturbedMetric - baseMetric) / stepSize;
        } else {
          gradients[asset] = 0;
        }
      } else {
        gradients[asset] = 0;
      }
    });
    
    return gradients;
  }

  /**
   * Calculate objective function value
   */
  calculateObjectiveFunction(weights, objective, calculateMetrics) {
    try {
      const metrics = calculateMetrics(weights);
      
      if (!metrics) {
        return objective === 'risk' ? 999 : -999;
      }
      
      switch (objective) {
        case 'sharpe':
          return metrics.sharpe || -999;
        case 'risk':
          return -(metrics.volatility || 999);
        case 'sortino':
          return metrics.sortino || -999;
        case 'cvar':
          return -(Math.abs(metrics.cvar) || 999);
        default:
          return metrics.sharpe || -999;
      }
    } catch (error) {
      console.error('Error calculating objective function:', error);
      return objective === 'risk' ? 999 : -999;
    }
  }

  /**
   * Validate weight allocation
   */
  isValidWeightAllocation(weights) {
    const sum = Object.values(weights).reduce((a, b) => a + b, 0);
    const allNonNegative = Object.values(weights).every(w => w >= 0);
    const allWithinBounds = Object.values(weights).every(w => w <= 100);
    
    return allNonNegative && allWithinBounds && Math.abs(sum - 100) < 0.01;
  }

  /**
   * Check if new metric is improvement
   */
  isMetricImprovement(newMetric, currentBest, objective) {
    if (objective === 'risk' || objective === 'cvar') {
      return newMetric > currentBest;
    } else {
      return newMetric > currentBest;
    }
  }

  /**
   * Normalize weights to sum to 100%
   */
  normalizeWeights(weights) {
    const sum = Object.values(weights).reduce((a, b) => a + b, 0);
    const normalized = {};
    
    if (sum > 0) {
      Object.keys(weights).forEach(asset => {
        normalized[asset] = parseFloat(((weights[asset] / sum) * 100).toFixed(1));
      });
      
      const normalizedSum = Object.values(normalized).reduce((a, b) => a + b, 0);
      const difference = parseFloat((100.0 - normalizedSum).toFixed(1));
      
      if (Math.abs(difference) > 0) {
        let largestAsset = null;
        let largestWeight = -1;
        Object.keys(normalized).forEach(asset => {
          if (normalized[asset] > largestWeight) {
            largestWeight = normalized[asset];
            largestAsset = asset;
          }
        });
        
        if (largestAsset) {
          normalized[largestAsset] = parseFloat((normalized[largestAsset] + difference).toFixed(1));
        }
      }
    } else {
      const equalWeight = parseFloat((100 / Object.keys(weights).length).toFixed(1));
      Object.keys(weights).forEach(asset => {
        normalized[asset] = equalWeight;
      });
    }
    
    return normalized;
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PortfolioOptimizer;
} else if (typeof window !== 'undefined') {
  window.PortfolioOptimizer = PortfolioOptimizer;
} 