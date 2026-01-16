# reports/plotter.py

"""
Basic plotting module for backtest results.
Phase 2: Simple matplotlib visualizations.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BacktestPlotter:
    """
    Creates basic visualizations for backtest results.
    """
    
    def __init__(self, output_dir: str = "results"):
        """
        Initialize plotter.
        
        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')
        
        logger.info(f"BacktestPlotter initialized. Output directory: {self.output_dir}")
    
    def plot_equity_curve(self, equity_curve: List[Dict[str, Any]], 
                          save_path: Optional[Path] = None) -> Path:
        """
        Plot equity curve with drawdown.
        
        Args:
            equity_curve: List of equity values from BacktestEngine
            save_path: Optional specific path to save plot
            
        Returns:
            Path to saved plot
        """
        if not equity_curve:
            logger.warning("No equity curve data to plot")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(equity_curve)
        
        if 'timestamp' not in df.columns and 'index' in df.columns:
            # Use index as x-axis if no timestamp
            df['x'] = df['index']
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['x'] = df['timestamp']
        else:
            df['x'] = np.arange(len(df))
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot 1: Equity curve
        ax1.plot(df['x'], df['equity'], label='Portfolio Equity', 
                color='blue', linewidth=2)
        
        # Add initial capital line
        if len(df) > 0:
            initial_equity = df['equity'].iloc[0]
            ax1.axhline(y=initial_equity, color='green', linestyle='--', 
                       alpha=0.5, label='Initial Capital')
        
        ax1.set_title('Portfolio Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Format x-axis if datetime
        if 'timestamp' in df.columns:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Plot 2: Drawdown
        if 'equity' in df.columns and len(df) > 0:
            # Calculate drawdown
            equity_series = df['equity'].values
            running_max = np.maximum.accumulate(equity_series)
            drawdown = (equity_series - running_max) / running_max * 100
            
            ax2.fill_between(df['x'], drawdown, 0, 
                            where=drawdown < 0, 
                            color='red', alpha=0.3, label='Drawdown')
            ax2.plot(df['x'], drawdown, color='red', linewidth=1, alpha=0.7)
            
            # Highlight max drawdown
            max_dd_idx = np.argmin(drawdown)
            max_dd_value = drawdown[max_dd_idx]
            
            if max_dd_value < 0:
                ax2.plot(df['x'].iloc[max_dd_idx], max_dd_value, 'ro', 
                        markersize=8, label=f'Max DD: {max_dd_value:.1f}%')
        
        ax2.set_title('Drawdown (%)', fontsize=12)
        ax2.set_ylabel('Drawdown %', fontsize=10)
        ax2.set_xlabel('Time' if 'timestamp' in df.columns else 'Candle Index', 
                      fontsize=10)
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis for drawdown plot
        if 'timestamp' in df.columns:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f'equity_curve_{timestamp}.png'
        else:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Equity curve plot saved to: {save_path}")
        return save_path
    
    def plot_trade_distribution(self, trades: List[Dict[str, Any]], 
                               save_path: Optional[Path] = None) -> Path:
        """
        Plot trade P&L distribution.
        
        Args:
            trades: List of trades from BacktestEngine
            save_path: Optional specific path to save plot
            
        Returns:
            Path to saved plot
        """
        if not trades:
            logger.warning("No trade data to plot")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        if 'net_pnl' not in df.columns:
            logger.warning("No P&L data in trades")
            return None
        
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Plot 1: Histogram of P&L
        ax1 = axes[0, 0]
        profits = df[df['net_pnl'] > 0]['net_pnl']
        losses = df[df['net_pnl'] < 0]['net_pnl']
        
        if len(profits) > 0:
            ax1.hist(profits, bins=30, alpha=0.7, color='green', 
                    label=f'Profits ({len(profits)})', edgecolor='black')
        if len(losses) > 0:
            ax1.hist(losses, bins=30, alpha=0.7, color='red', 
                    label=f'Losses ({len(losses)})', edgecolor='black')
        
        ax1.set_title('Distribution of Trade P&L', fontsize=12, fontweight='bold')
        ax1.set_xlabel('P&L ($)', fontsize=10)
        ax1.set_ylabel('Frequency', fontsize=10)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Cumulative P&L
        ax2 = axes[0, 1]
        df_sorted = df.sort_values('exit_time' if 'exit_time' in df.columns else 'entry_time')
        cumulative_pnl = df_sorted['net_pnl'].cumsum()
        
        ax2.plot(range(len(cumulative_pnl)), cumulative_pnl, 
                color='blue', linewidth=2, label='Cumulative P&L')
        ax2.fill_between(range(len(cumulative_pnl)), 0, cumulative_pnl, 
                        where=cumulative_pnl > 0, color='green', alpha=0.3)
        ax2.fill_between(range(len(cumulative_pnl)), 0, cumulative_pnl, 
                        where=cumulative_pnl < 0, color='red', alpha=0.3)
        
        ax2.set_title('Cumulative P&L Over Trades', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Trade Number', fontsize=10)
        ax2.set_ylabel('Cumulative P&L ($)', fontsize=10)
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Win/Loss by exit reason
        ax3 = axes[1, 0]
        if 'exit_reason' in df.columns:
            reason_stats = df.groupby('exit_reason').agg({
                'net_pnl': ['count', 'sum', 'mean'],
                'bars_held': 'mean'
            }).round(2)
            
            if not reason_stats.empty:
                reasons = reason_stats.index.tolist()
                counts = reason_stats[('net_pnl', 'count')].values
                
                bars = ax3.bar(range(len(reasons)), counts, color='skyblue', edgecolor='black')
                ax3.set_title('Trades by Exit Reason', fontsize=12, fontweight='bold')
                ax3.set_xlabel('Exit Reason', fontsize=10)
                ax3.set_ylabel('Number of Trades', fontsize=10)
                ax3.set_xticks(range(len(reasons)))
                ax3.set_xticklabels(reasons, rotation=45, ha='right')
                
                # Add count labels on bars
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(count)}', ha='center', va='bottom')
        
        # Plot 4: Scatter plot of trade performance
        ax4 = axes[1, 1]
        if 'bars_held' in df.columns and 'net_pnl' in df.columns:
            winning_trades = df[df['net_pnl'] > 0]
            losing_trades = df[df['net_pnl'] < 0]
            
            if len(winning_trades) > 0:
                ax4.scatter(winning_trades['bars_held'], winning_trades['net_pnl'], 
                          color='green', alpha=0.6, label='Winning Trades', s=30)
            if len(losing_trades) > 0:
                ax4.scatter(losing_trades['bars_held'], losing_trades['net_pnl'], 
                          color='red', alpha=0.6, label='Losing Trades', s=30)
            
            ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5, alpha=0.5)
            ax4.set_title('Trade P&L vs Holding Period', fontsize=12, fontweight='bold')
            ax4.set_xlabel('Bars Held', fontsize=10)
            ax4.set_ylabel('P&L ($)', fontsize=10)
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f'trade_distribution_{timestamp}.png'
        else:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Trade distribution plot saved to: {save_path}")
        return save_path
    
    def plot_price_with_signals(self, journal: List[Dict[str, Any]], 
                               trades: List[Dict[str, Any]],
                               save_path: Optional[Path] = None) -> Path:
        """
        Plot price chart with entry/exit signals.
        
        Args:
            journal: Journal data with price information
            trades: Trade data with entry/exit points
            save_path: Optional specific path to save plot
            
        Returns:
            Path to saved plot
        """
        if not journal or not trades:
            logger.warning("Insufficient data for price signals plot")
            return None
        
        # Convert to DataFrames
        journal_df = pd.DataFrame(journal)
        trades_df = pd.DataFrame(trades)
        
        if 'price' not in journal_df.columns:
            logger.warning("No price data in journal")
            return None
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Plot 1: Price with signals
        if 'timestamp' in journal_df.columns:
            journal_df['timestamp'] = pd.to_datetime(journal_df['timestamp'])
            x_price = journal_df['timestamp']
        else:
            x_price = journal_df.index
        
        ax1.plot(x_price, journal_df['price'], label='Price', 
                color='black', linewidth=1, alpha=0.7)
        
        # Plot entry and exit points
        entry_times = []
        entry_prices = []
        exit_times = []
        exit_prices = []
        
        for _, trade in trades_df.iterrows():
            # Entry point
            if 'entry_time' in trade and 'entry_price' in trade:
                entry_times.append(trade['entry_time'])
                entry_prices.append(trade['entry_price'])
            
            # Exit point
            if 'exit_time' in trade and 'exit_price' in trade:
                exit_times.append(trade['exit_time'])
                exit_prices.append(trade['exit_price'])
        
        # Convert to datetime if needed
        if entry_times and isinstance(entry_times[0], str):
            entry_times = pd.to_datetime(entry_times)
        if exit_times and isinstance(exit_times[0], str):
            exit_times = pd.to_datetime(exit_times)
        
        # Plot markers
        if entry_times:
            ax1.scatter(entry_times, entry_prices, color='green', 
                       marker='^', s=100, label='Entry', zorder=5)
        if exit_times:
            ax1.scatter(exit_times, exit_prices, color='red', 
                       marker='v', s=100, label='Exit', zorder=5)
        
        # Connect entry-exit pairs with lines
        for _, trade in trades_df.iterrows():
            if ('entry_time' in trade and 'entry_price' in trade and 
                'exit_time' in trade and 'exit_price' in trade):
                
                entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
                exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
                
                # Color based on P&L
                if 'net_pnl' in trade and trade['net_pnl'] > 0:
                    line_color = 'green'
                    line_alpha = 0.3
                else:
                    line_color = 'red'
                    line_alpha = 0.3
                
                ax1.plot([entry_time, exit_time], 
                        [trade['entry_price'], trade['exit_price']],
                        color=line_color, alpha=line_alpha, linewidth=1)
        
        ax1.set_title('Price Chart with Entry/Exit Signals', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.legend(loc='best')
        ax1.grid(True, alpha=0.3)
        
        # Format x-axis if datetime
        if 'timestamp' in journal_df.columns:
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Plot 2: Position indicator
        if 'in_position' in journal_df.columns:
            position_signal = journal_df['in_position'].astype(float)
            
            ax2.fill_between(x_price, 0, position_signal, 
                            where=position_signal > 0, 
                            color='blue', alpha=0.3, label='In Position')
            ax2.plot(x_price, position_signal, color='blue', linewidth=1)
            
            # Add entry/exit markers on position chart too
            if entry_times:
                ax2.scatter(entry_times, [1] * len(entry_times), 
                          color='green', marker='^', s=50, zorder=5)
            if exit_times:
                ax2.scatter(exit_times, [0] * len(exit_times), 
                          color='red', marker='v', s=50, zorder=5)
        
        ax2.set_title('Position Status', fontsize=12)
        ax2.set_xlabel('Time', fontsize=10)
        ax2.set_ylabel('Position', fontsize=10)
        ax2.set_yticks([0, 1])
        ax2.set_yticklabels(['Out', 'In'])
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis for position plot
        if 'timestamp' in journal_df.columns:
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        
        # Save plot
        if save_path is None:
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f'price_signals_{timestamp}.png'
        else:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        logger.info(f"Price signals plot saved to: {save_path}")
        return save_path
    
    def create_all_plots(self, results: Dict[str, Any], run_dir: Path) -> Dict[str, Path]:
        """
        Create all standard plots for a backtest run.
        
        Args:
            results: Results dictionary from BacktestEngine
            run_dir: Directory to save plots
            
        Returns:
            Dictionary with plot file paths
        """
        plot_paths = {}
        
        try:
            # 1. Equity curve plot
            if results.get('equity_curve'):
                equity_plot_path = run_dir / 'equity_curve.png'
                plot_paths['equity'] = self.plot_equity_curve(
                    results['equity_curve'], equity_plot_path
                )
            
            # 2. Trade distribution plot
            if results.get('trades'):
                trade_plot_path = run_dir / 'trade_distribution.png'
                plot_paths['trades'] = self.plot_trade_distribution(
                    results['trades'], trade_plot_path
                )
            
            # 3. Price with signals plot
            if results.get('journal') and results.get('trades'):
                price_plot_path = run_dir / 'price_signals.png'
                plot_paths['price'] = self.plot_price_with_signals(
                    results['journal'], results['trades'], price_plot_path
                )
            
            logger.info(f"Created {len(plot_paths)} plots in {run_dir}")
            
        except Exception as e:
            logger.error(f"Error creating plots: {e}")
        
        return plot_paths
