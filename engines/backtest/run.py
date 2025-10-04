#!/usr/bin/env python3
"""
Backtesting engine for AI Trading Agent

Loads historical candles, simulates bracket entries from simple rules,
and produces equity curve + trade statistics with HTML reports.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import json
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'BUY' or 'SELL'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    duration_minutes: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_reason: str = "MANUAL"

@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: float = 10000.0
    position_size_pct: float = 0.1  # 10% of capital per trade
    stop_loss_pct: float = 0.02     # 2% stop loss
    take_profit_pct: float = 0.04   # 4% take profit
    commission_pct: float = 0.001   # 0.1% commission
    slippage_pct: float = 0.0005    # 0.05% slippage
    max_trades_per_day: int = 10
    trading_hours_start: int = 9    # 9 AM
    trading_hours_end: int = 16     # 4 PM

@dataclass
class BacktestResults:
    """Backtesting results."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    avg_trade_duration: float
    equity_curve: List[Dict[str, Any]]
    trades: List[Trade]

class BacktestEngine:
    """Main backtesting engine."""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.current_capital = config.initial_capital
        self.peak_capital = config.initial_capital
        self.max_drawdown = 0.0
        
    def load_data(self, data_path: str) -> pd.DataFrame:
        """
        Load historical candle data from CSV or Parquet file.
        
        Expected columns: timestamp, open, high, low, close, volume
        """
        data_path = Path(data_path)
        
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")
        
        logger.info("Loading historical data", path=str(data_path))
        
        if data_path.suffix.lower() == '.csv':
            df = pd.read_csv(data_path)
        elif data_path.suffix.lower() == '.parquet':
            df = pd.read_parquet(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")
        
        # Ensure required columns exist
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Add technical indicators
        df = self._add_technical_indicators(df)
        
        logger.info("Data loaded successfully", 
                   rows=len(df), 
                   start=df['timestamp'].min(), 
                   end=df['timestamp'].max())
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the dataframe."""
        # Simple Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals using simple rules.
        
        BUY signals:
        - Price above SMA 20 and SMA 50
        - RSI between 30 and 70
        - MACD above signal line
        
        SELL signals:
        - Price below SMA 20 and SMA 50
        - RSI above 70 or below 30
        - MACD below signal line
        """
        df = df.copy()
        df['signal'] = 0
        df['signal_strength'] = 0.0
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # Skip if we don't have enough data for indicators
            if pd.isna(row['sma_20']) or pd.isna(row['sma_50']) or pd.isna(row['rsi']):
                continue
            
            signal_strength = 0
            
            # BUY conditions
            if (row['close'] > row['sma_20'] and 
                row['close'] > row['sma_50'] and
                30 < row['rsi'] < 70 and
                row['macd'] > row['macd_signal'] and
                prev_row['macd'] <= prev_row['macd_signal']):  # MACD crossover
                
                df.at[i, 'signal'] = 1  # BUY
                signal_strength = min(1.0, (row['rsi'] - 30) / 40)  # Normalize RSI
                df.at[i, 'signal_strength'] = signal_strength
            
            # SELL conditions
            elif (row['close'] < row['sma_20'] and 
                  row['close'] < row['sma_50'] and
                  (row['rsi'] > 70 or row['rsi'] < 30) and
                  row['macd'] < row['macd_signal'] and
                  prev_row['macd'] >= prev_row['macd_signal']):  # MACD crossover
                
                df.at[i, 'signal'] = -1  # SELL
                signal_strength = min(1.0, abs(row['rsi'] - 50) / 50)  # Distance from 50
                df.at[i, 'signal_strength'] = signal_strength
        
        logger.info("Signals generated", 
                   buy_signals=len(df[df['signal'] == 1]),
                   sell_signals=len(df[df['signal'] == -1]))
        
        return df
    
    def simulate_trading(self, df: pd.DataFrame) -> None:
        """Simulate trading based on signals."""
        logger.info("Starting trading simulation", 
                   initial_capital=self.config.initial_capital)
        
        current_position = None
        daily_trades = 0
        last_trade_date = None
        
        for i, row in df.iterrows():
            current_time = row['timestamp']
            current_date = current_time.date()
            
            # Reset daily trade counter
            if last_trade_date != current_date:
                daily_trades = 0
                last_trade_date = current_date
            
            # Check trading hours
            if not (self.config.trading_hours_start <= current_time.hour < self.config.trading_hours_end):
                continue
            
            # Check daily trade limit
            if daily_trades >= self.config.max_trades_per_day:
                continue
            
            # Skip if we don't have enough data
            if pd.isna(row['signal']) or pd.isna(row['close']):
                continue
            
            # Handle existing position
            if current_position:
                exit_price, exit_reason = self._check_exit_conditions(
                    current_position, row, df.iloc[i+1:] if i+1 < len(df) else None
                )
                
                if exit_price:
                    self._close_position(current_position, row['timestamp'], 
                                       exit_price, exit_reason)
                    current_position = None
                    daily_trades += 1
            
            # Handle new signals
            if not current_position and row['signal'] != 0:
                if row['signal'] == 1:  # BUY signal
                    current_position = self._open_position(
                        'BUY', row['timestamp'], row['close'], row['signal_strength']
                    )
                elif row['signal'] == -1:  # SELL signal
                    current_position = self._open_position(
                        'SELL', row['timestamp'], row['close'], row['signal_strength']
                    )
            
            # Update equity curve
            self._update_equity_curve(row['timestamp'], row['close'])
        
        # Close any remaining position
        if current_position:
            last_row = df.iloc[-1]
            self._close_position(current_position, last_row['timestamp'], 
                               last_row['close'], "END_OF_DATA")
        
        logger.info("Trading simulation completed", 
                   total_trades=len(self.trades),
                   final_capital=self.current_capital)
    
    def _open_position(self, side: str, entry_time: datetime, 
                      entry_price: float, signal_strength: float) -> Dict[str, Any]:
        """Open a new position."""
        # Calculate position size based on signal strength and available capital
        position_value = self.current_capital * self.config.position_size_pct * signal_strength
        quantity = position_value / entry_price
        
        # Apply slippage
        if side == 'BUY':
            actual_entry_price = entry_price * (1 + self.config.slippage_pct)
        else:
            actual_entry_price = entry_price * (1 - self.config.slippage_pct)
        
        # Calculate stop loss and take profit
        if side == 'BUY':
            stop_loss = actual_entry_price * (1 - self.config.stop_loss_pct)
            take_profit = actual_entry_price * (1 + self.config.take_profit_pct)
        else:
            stop_loss = actual_entry_price * (1 + self.config.stop_loss_pct)
            take_profit = actual_entry_price * (1 - self.config.take_profit_pct)
        
        position = {
            'side': side,
            'entry_time': entry_time,
            'entry_price': actual_entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signal_strength': signal_strength
        }
        
        logger.debug("Position opened", 
                    side=side, 
                    entry_price=actual_entry_price,
                    quantity=quantity)
        
        return position
    
    def _check_exit_conditions(self, position: Dict[str, Any], 
                              current_row: pd.Series, 
                              future_data: Optional[pd.DataFrame]) -> Tuple[Optional[float], str]:
        """Check if position should be closed."""
        current_price = current_row['close']
        side = position['side']
        
        # Check stop loss
        if side == 'BUY' and current_price <= position['stop_loss']:
            return current_price, "STOP_LOSS"
        elif side == 'SELL' and current_price >= position['stop_loss']:
            return current_price, "STOP_LOSS"
        
        # Check take profit
        if side == 'BUY' and current_price >= position['take_profit']:
            return current_price, "TAKE_PROFIT"
        elif side == 'SELL' and current_price <= position['take_profit']:
            return current_price, "TAKE_PROFIT"
        
        # Check for opposite signal
        if current_row['signal'] != 0:
            if (side == 'BUY' and current_row['signal'] == -1) or \
               (side == 'SELL' and current_row['signal'] == 1):
                return current_price, "SIGNAL_REVERSAL"
        
        return None, "HOLD"
    
    def _close_position(self, position: Dict[str, Any], exit_time: datetime, 
                       exit_price: float, exit_reason: str) -> None:
        """Close a position and record the trade."""
        # Apply slippage
        if position['side'] == 'BUY':
            actual_exit_price = exit_price * (1 - self.config.slippage_pct)
        else:
            actual_exit_price = exit_price * (1 + self.config.slippage_pct)
        
        # Calculate P&L
        if position['side'] == 'BUY':
            pnl = (actual_exit_price - position['entry_price']) * position['quantity']
        else:
            pnl = (position['entry_price'] - actual_exit_price) * position['quantity']
        
        # Apply commission
        entry_commission = position['entry_price'] * position['quantity'] * self.config.commission_pct
        exit_commission = actual_exit_price * position['quantity'] * self.config.commission_pct
        pnl -= (entry_commission + exit_commission)
        
        pnl_pct = pnl / (position['entry_price'] * position['quantity'])
        duration_minutes = int((exit_time - position['entry_time']).total_seconds() / 60)
        
        # Create trade record
        trade = Trade(
            entry_time=position['entry_time'],
            exit_time=exit_time,
            symbol="BTCUSD",  # Default symbol
            side=position['side'],
            entry_price=position['entry_price'],
            exit_price=actual_exit_price,
            quantity=position['quantity'],
            pnl=pnl,
            pnl_pct=pnl_pct,
            duration_minutes=duration_minutes,
            stop_loss=position['stop_loss'],
            take_profit=position['take_profit'],
            exit_reason=exit_reason
        )
        
        self.trades.append(trade)
        
        # Update capital
        self.current_capital += pnl
        
        # Update peak capital and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        logger.debug("Position closed", 
                    side=position['side'],
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    exit_reason=exit_reason)
    
    def _update_equity_curve(self, timestamp: datetime, price: float) -> None:
        """Update the equity curve."""
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': self.current_capital,
            'price': price,
            'drawdown': (self.peak_capital - self.current_capital) / self.peak_capital
        })
    
    def calculate_statistics(self) -> BacktestResults:
        """Calculate backtesting statistics."""
        if not self.trades:
            logger.warning("No trades to analyze")
            return self._empty_results()
        
        trades_df = pd.DataFrame([asdict(trade) for trade in self.trades])
        
        # Basic statistics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L statistics
        total_pnl = trades_df['pnl'].sum()
        total_pnl_pct = (self.current_capital - self.config.initial_capital) / self.config.initial_capital
        
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        largest_win = trades_df['pnl'].max()
        largest_loss = trades_df['pnl'].min()
        
        # Risk metrics
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 else float('inf')
        
        # Sharpe ratio (simplified)
        if len(self.equity_curve) > 1:
            equity_returns = pd.Series([point['equity'] for point in self.equity_curve]).pct_change().dropna()
            sharpe_ratio = equity_returns.mean() / equity_returns.std() * np.sqrt(252) if equity_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        avg_trade_duration = trades_df['duration_minutes'].mean()
        
        results = BacktestResults(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            max_drawdown=self.max_drawdown,
            max_drawdown_pct=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_trade_duration=avg_trade_duration,
            equity_curve=self.equity_curve,
            trades=self.trades
        )
        
        logger.info("Statistics calculated", 
                   total_trades=total_trades,
                   win_rate=win_rate,
                   total_pnl=total_pnl,
                   max_drawdown=self.max_drawdown)
        
        return results
    
    def _empty_results(self) -> BacktestResults:
        """Return empty results when no trades."""
        return BacktestResults(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            total_pnl=0,
            total_pnl_pct=0,
            max_drawdown=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            profit_factor=0,
            avg_win=0,
            avg_loss=0,
            largest_win=0,
            largest_loss=0,
            avg_trade_duration=0,
            equity_curve=self.equity_curve,
            trades=[]
        )

class ReportGenerator:
    """Generates HTML reports for backtesting results."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
    
    def generate_report(self, results: BacktestResults, config: BacktestConfig, 
                       data_file: str) -> Path:
        """Generate HTML report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"backtest_{timestamp}.html"
        
        logger.info("Generating backtest report", path=str(report_path))
        
        # Generate HTML content
        html_content = self._create_html_content(results, config, data_file, timestamp)
        
        # Write to file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("Report generated successfully", path=str(report_path))
        return report_path
    
    def _create_html_content(self, results: BacktestResults, config: BacktestConfig,
                            data_file: str, timestamp: str) -> str:
        """Create HTML content for the report."""
        
        # Prepare trade data for charts
        trades_data = []
        for trade in results.trades:
            trades_data.append({
                'entry_time': trade.entry_time.isoformat(),
                'exit_time': trade.exit_time.isoformat(),
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'side': trade.side,
                'exit_reason': trade.exit_reason
            })
        
        # Prepare equity curve data
        equity_data = []
        for point in results.equity_curve:
            equity_data.append({
                'timestamp': point['timestamp'].isoformat(),
                'equity': point['equity'],
                'drawdown': point['drawdown']
            })
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - {timestamp}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        .stat-card.positive {{
            border-left-color: #28a745;
        }}
        .stat-card.negative {{
            border-left-color: #dc3545;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .chart-container {{
            padding: 30px;
            border-top: 1px solid #eee;
        }}
        .chart-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
        }}
        .chart {{
            height: 400px;
            margin-bottom: 40px;
        }}
        .config-section {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-top: 1px solid #eee;
        }}
        .config-title {{
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #333;
        }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .config-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .trades-table {{
            padding: 30px;
            border-top: 1px solid #eee;
        }}
        .trades-table h3 {{
            margin-bottom: 20px;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .positive {{
            color: #28a745;
        }}
        .negative {{
            color: #dc3545;
        }}
        .side-buy {{
            background-color: #d4edda;
            color: #155724;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
        .side-sell {{
            background-color: #f8d7da;
            color: #721c24;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Backtest Report</h1>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Data source: {Path(data_file).name}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card {'positive' if results.total_pnl >= 0 else 'negative'}">
                <div class="stat-value">${results.total_pnl:,.2f}</div>
                <div class="stat-label">Total P&L</div>
            </div>
            <div class="stat-card {'positive' if results.total_pnl_pct >= 0 else 'negative'}">
                <div class="stat-value">{results.total_pnl_pct:.2%}</div>
                <div class="stat-label">Total Return</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{results.total_trades}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat-card {'positive' if results.win_rate >= 0.5 else 'negative'}">
                <div class="stat-value">{results.win_rate:.2%}</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{results.profit_factor:.2f}</div>
                <div class="stat-label">Profit Factor</div>
            </div>
            <div class="stat-card {'negative' if results.max_drawdown_pct > 0.1 else 'positive'}">
                <div class="stat-value">{results.max_drawdown_pct:.2%}</div>
                <div class="stat-label">Max Drawdown</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{results.sharpe_ratio:.2f}</div>
                <div class="stat-label">Sharpe Ratio</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{results.avg_trade_duration:.0f}</div>
                <div class="stat-label">Avg Duration (min)</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">Equity Curve</div>
            <canvas id="equityChart" class="chart"></canvas>
            
            <div class="chart-title">Drawdown</div>
            <canvas id="drawdownChart" class="chart"></canvas>
            
            <div class="chart-title">Trade P&L Distribution</div>
            <canvas id="pnlChart" class="chart"></canvas>
        </div>
        
        <div class="config-section">
            <div class="config-title">Backtest Configuration</div>
            <div class="config-grid">
                <div class="config-item">
                    <span>Initial Capital:</span>
                    <span>${config.initial_capital:,.2f}</span>
                </div>
                <div class="config-item">
                    <span>Position Size:</span>
                    <span>{config.position_size_pct:.1%}</span>
                </div>
                <div class="config-item">
                    <span>Stop Loss:</span>
                    <span>{config.stop_loss_pct:.1%}</span>
                </div>
                <div class="config-item">
                    <span>Take Profit:</span>
                    <span>{config.take_profit_pct:.1%}</span>
                </div>
                <div class="config-item">
                    <span>Commission:</span>
                    <span>{config.commission_pct:.3%}</span>
                </div>
                <div class="config-item">
                    <span>Slippage:</span>
                    <span>{config.slippage_pct:.3%}</span>
                </div>
                <div class="config-item">
                    <span>Max Trades/Day:</span>
                    <span>{config.max_trades_per_day}</span>
                </div>
                <div class="config-item">
                    <span>Trading Hours:</span>
                    <span>{config.trading_hours_start}:00 - {config.trading_hours_end}:00</span>
                </div>
            </div>
        </div>
        
        <div class="trades-table">
            <h3>Trade History ({len(results.trades)} trades)</h3>
            <table>
                <thead>
                    <tr>
                        <th>Entry Time</th>
                        <th>Exit Time</th>
                        <th>Side</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>P&L</th>
                        <th>P&L %</th>
                        <th>Duration</th>
                        <th>Exit Reason</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Add trade rows
        for trade in results.trades:
            html += f"""
                    <tr>
                        <td>{trade.entry_time.strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade.exit_time.strftime('%Y-%m-%d %H:%M')}</td>
                        <td><span class="side-{'buy' if trade.side == 'BUY' else 'sell'}">{trade.side}</span></td>
                        <td>${trade.entry_price:.4f}</td>
                        <td>${trade.exit_price:.4f}</td>
                        <td class="{'positive' if trade.pnl >= 0 else 'negative'}">${trade.pnl:.2f}</td>
                        <td class="{'positive' if trade.pnl_pct >= 0 else 'negative'}">{trade.pnl_pct:.2%}</td>
                        <td>{trade.duration_minutes} min</td>
                        <td>{trade.exit_reason}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Equity Curve Chart
        const equityCtx = document.getElementById('equityChart').getContext('2d');
        const equityData = """ + str(equity_data) + """;
        
        new Chart(equityCtx, {
            type: 'line',
            data: {
                labels: equityData.map(d => new Date(d.timestamp).toLocaleDateString()),
                datasets: [{
                    label: 'Equity',
                    data: equityData.map(d => d.equity),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
        
        // Drawdown Chart
        const drawdownCtx = document.getElementById('drawdownChart').getContext('2d');
        new Chart(drawdownCtx, {
            type: 'line',
            data: {
                labels: equityData.map(d => new Date(d.timestamp).toLocaleDateString()),
                datasets: [{
                    label: 'Drawdown %',
                    data: equityData.map(d => d.drawdown * 100),
                    borderColor: '#dc3545',
                    backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        // P&L Distribution Chart
        const pnlCtx = document.getElementById('pnlChart').getContext('2d');
        const tradesData = """ + str(trades_data) + """;
        const pnlValues = tradesData.map(t => t.pnl);
        
        new Chart(pnlCtx, {
            type: 'bar',
            data: {
                labels: tradesData.map((t, i) => `Trade ${i+1}`),
                datasets: [{
                    label: 'P&L',
                    data: pnlValues,
                    backgroundColor: pnlValues.map(v => v >= 0 ? 'rgba(40, 167, 69, 0.7)' : 'rgba(220, 53, 69, 0.7)'),
                    borderColor: pnlValues.map(v => v >= 0 ? '#28a745' : '#dc3545'),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: 'P&L ($)'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
        """
        
        return html

def main():
    """Main function to run backtesting."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtesting simulation')
    parser.add_argument('data_file', help='Path to historical data file (CSV/Parquet)')
    parser.add_argument('--initial-capital', type=float, default=10000.0, help='Initial capital')
    parser.add_argument('--position-size', type=float, default=0.1, help='Position size as % of capital')
    parser.add_argument('--stop-loss', type=float, default=0.02, help='Stop loss %')
    parser.add_argument('--take-profit', type=float, default=0.04, help='Take profit %')
    parser.add_argument('--output-dir', default='reports/backtests', help='Output directory for reports')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure backtesting
    config = BacktestConfig(
        initial_capital=args.initial_capital,
        position_size_pct=args.position_size,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit
    )
    
    # Run backtesting
    engine = BacktestEngine(config)
    
    try:
        # Load data
        df = engine.load_data(args.data_file)
        
        # Generate signals
        df_with_signals = engine.generate_signals(df)
        
        # Simulate trading
        engine.simulate_trading(df_with_signals)
        
        # Calculate results
        results = engine.calculate_statistics()
        
        # Generate report
        report_generator = ReportGenerator(output_dir)
        report_path = report_generator.generate_report(results, config, args.data_file)
        
        print(f"Backtesting completed successfully!")
        print(f"Total trades: {results.total_trades}")
        print(f"Win rate: {results.win_rate:.2%}")
        print(f"Total P&L: ${results.total_pnl:.2f} ({results.total_pnl_pct:.2%})")
        print(f"Max drawdown: {results.max_drawdown_pct:.2%}")
        print(f"Report saved: {report_path}")
        
    except Exception as e:
        logger.error("Backtesting failed", error=str(e))
        raise

if __name__ == "__main__":
    main()
