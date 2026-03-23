#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simplified integration test for Advanced Simulator
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

project_root = Path.cwd()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Engine_Matrix.advanced_simulator import AdvancedExchangeSimulator, ExchangeConfig
from Strategy_Pool.strategies import STRATEGIES

# Generate test data
np.random.seed(42)
dates = pd.date_range('2024-01-01', periods=150, freq='D')
close_prices = 100 * np.exp(np.cumsum(np.random.randn(150) * 0.01))
open_prices = close_prices * (1 + np.random.randn(150) * 0.005)
high_prices = np.maximum(open_prices, close_prices) * (1 + np.abs(np.random.randn(150) * 0.005))
low_prices = np.minimum(open_prices, close_prices) * (1 - np.abs(np.random.randn(150) * 0.005))
volumes = 1000000 + np.random.randint(-200000, 200000, 150)

test_data = pd.DataFrame({
    'open': open_prices,
    'high': high_prices,
    'low': low_prices,
    'close': close_prices,
    'volume': volumes,
}, index=dates)

print('===== Advanced Simulator Integration Test =====')
print('Test data: {} days'.format(len(test_data)))
print('Available strategies: {}'.format(len(STRATEGIES)))

strategy = STRATEGIES[0]
print('Selected strategy: {}'.format(strategy.name))

# Generate signals
signal_data = strategy.backtest(test_data.copy(), {})
print('Signal columns: {}'.format(list(signal_data.columns)))

# Test advanced simulator
config = ExchangeConfig(
    commission_rate=0.0005,
    impact_coefficient=0.5,
    max_order_ratio=0.05
)

simulator = AdvancedExchangeSimulator(config)
print('Simulator config:')
print('  Commission: {:.3f}%'.format(config.commission_rate*100))
print('  Impact coefficient: {}'.format(config.impact_coefficient))
print('  Max order ratio: {:.1f}%'.format(config.max_order_ratio*100))

print('Running backtest...')
result = simulator.run(signal_data, initial_capital=30000, strategy_name=strategy.name)

print('Backtest complete! Output shape: {}'.format(result.shape))
print('Output columns: {}'.format(list(result.columns)))

# Analysis
final_equity = result['equity'].iloc[-1]
total_return = (final_equity - 30000) / 30000
total_commission = result['commission_cost'].sum()
total_impact = result['market_impact_cost'].sum()
trades = result[result['trade_log'] != '']

print('Initial capital: ${:,.2f}'.format(30000))
print('Final equity: ${:,.2f}'.format(final_equity))
print('Total return: {:+.2%}'.format(total_return))
print('Total commission: ${:,.2f}'.format(total_commission))
print('Total impact cost: ${:,.2f}'.format(total_impact))
print('Number of trades: {}'.format(len(trades)))
print('')
print('SUCCESS: Advanced simulator integration verified!')
print('No FutureWarning should appear above this message.')
