"""
XGBoost 独立工作进程 — 通过文件系统与 Streamlit GUI 通信
避免 GPU/ML 计算阻塞 Streamlit 事件循环导致 WebSocket 断连
"""
import sys
import os
import json
import time
import pickle
import traceback

import pandas as pd
import numpy as np
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def update_progress(progress_file: str, step: float, total: float, message: str,
                    done: bool = False, error: str = None):
    """原子写入进度文件（先写临时文件再重命名，防止读到半成品）"""
    data = {
        'step': step,
        'total': total,
        'message': message,
        'done': done,
        'error': error,
        'timestamp': time.time()
    }
    tmp_file = progress_file + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    # 原子替换
    if os.path.exists(progress_file):
        os.remove(progress_file)
    os.rename(tmp_file, progress_file)


def run_worker(config_path: str):
    """XGBoost 工作主函数"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    progress_file = config['progress_file']
    result_file = config['result_file']

    try:
        update_progress(progress_file, 0, 5, "📂 加载数据...")

        # 加载数据
        df = pd.read_parquet(config['data_path'])
        start_ts = pd.Timestamp(config['start_date'])
        end_ts = pd.Timestamp(config['end_date'])
        mask = (df.index >= start_ts) & (df.index <= end_ts)
        df_filtered = df[mask].copy()

        update_progress(progress_file, 1, 5, f"📊 数据已加载 ({len(df_filtered)} 行)")

        # 初始化策略
        from Strategy_Pool.custom.xgboost_ml_strategy import XGBoostMLStrategy

        model_id = config.get('model_id')
        strategy = XGBoostMLStrategy(
            model_id=model_id,
            time_limit=config.get('time_limit', 300) if model_id is None else None,
            target_limit=config.get('target_limit', 100) if model_id is None else None,
            progress_callback=lambda s, t, m: update_progress(progress_file, s, t, m)
        )

        # 运行回测
        signal_result = strategy.backtest(df_filtered, {})

        # 用 signal 列模拟真实交易（与 BacktestEngine._simulate_trading 逻辑一致）
        initial_capital = config.get('initial_capital', 100000)
        cash = float(initial_capital)
        shares = 0
        trades = []
        equity_values = []

        if not signal_result.empty and 'signal' in signal_result.columns:
            prev_signal = 0
            for current_date, row in signal_result.iterrows():
                current_price = row.get('close', 0)
                current_signal = row.get('signal', 0)

                if current_price <= 0:
                    equity_values.append(cash + shares * max(current_price, 0))
                    prev_signal = current_signal
                    continue

                if prev_signal == 1 and shares == 0:
                    buy_shares = int(cash / current_price)
                    if buy_shares > 0:
                        cost = buy_shares * current_price
                        shares = buy_shares
                        cash -= cost
                        trades.append({
                            'date': current_date,
                            'action': 'BUY',
                            'price': current_price,
                            'shares': buy_shares,
                            'cost': cost,
                            'cash_after': cash,
                        })

                elif prev_signal == -1 and shares > 0:
                    revenue = shares * current_price
                    cost_basis = trades[-1]['cost'] if trades and trades[-1]['action'] == 'BUY' else 0
                    pnl = revenue - cost_basis
                    cash += revenue
                    trades.append({
                        'date': current_date,
                        'action': 'SELL',
                        'price': current_price,
                        'shares': shares,
                        'revenue': revenue,
                        'pnl': pnl,
                        'cash_after': cash,
                    })
                    shares = 0

                equity_values.append(cash + shares * current_price)
                prev_signal = current_signal

            equity_curve = pd.Series(equity_values, index=signal_result.index, name='equity')
        else:
            equity_curve = pd.Series([initial_capital] * len(df_filtered), index=df_filtered.index, name='equity')

        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        total_return = (equity_curve.iloc[-1] / initial_capital - 1) if len(equity_curve) > 0 else 0

        # 计算核心指标
        daily_returns = equity_curve.pct_change().dropna()
        max_drawdown = 0.0
        if len(equity_curve) > 1:
            running_max = equity_curve.cummax()
            drawdown = (equity_curve - running_max) / running_max
            max_drawdown = float(drawdown.min())

        sharpe = 0.0
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = float((daily_returns.mean() / daily_returns.std()) * (252 ** 0.5))

        n_days = (equity_curve.index[-1] - equity_curve.index[0]).days if len(equity_curve) > 1 else 1
        annual_return = float((1 + total_return) ** (365 / max(n_days, 1)) - 1)

        win_trades = [t for t in trades if t.get('action') == 'SELL' and t.get('pnl', 0) > 0]
        sell_trades_list = [t for t in trades if t.get('action') == 'SELL']
        win_rate = len(win_trades) / len(sell_trades_list) if sell_trades_list else 0.0

        # 保存结果到 pickle
        result_data = {
            'signal_result': signal_result,
            'equity_curve': equity_curve,
            'trades': trades_df,
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(trades),
            'initial_capital': initial_capital,
            'symbol': config['symbol'],
            'start_date': config['start_date'],
            'end_date': config['end_date'],
            'strategy_params': config.get('strategy_params', {}),
        }
        with open(result_file, 'wb') as f:
            pickle.dump(result_data, f)

        update_progress(progress_file, 5, 5, "✅ 回测完成！", done=True)

    except Exception:
        update_progress(progress_file, 0, 5, "❌ 回测失败",
                        done=True, error=traceback.format_exc())


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python xgboost_worker.py <config.json>")
        sys.exit(1)
    run_worker(sys.argv[1])
