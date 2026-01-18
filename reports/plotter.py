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
    
    def plot_price_with_signals(self, 
                           journal: List[Dict[str, Any]], 
                           trades: List[Dict[str, Any]],
                           config: Dict[str, Any],
                           save_path: Optional[Path] = None) -> Path:
        """
        Plot price chart with entry/exit signals AND indicators OVERLAID.
        """
        if not journal:
            logger.warning("No journal data for price signals plot")
            return None
        
        # Convert to DataFrames
        journal_df = pd.DataFrame(journal)
        
        if 'price' not in journal_df.columns:
            logger.warning("No price data in journal")
            return None
        
        # Get plotting configuration
        plotting_config = config.get('plotting', {})
        indicators_to_plot = plotting_config.get('indicators_to_plot', [])

        # DEBUG
        indicator_data = self._load_indicator_data(journal_df, config)
        
        if not indicator_data:
            logger.error("NO INDICATOR DATA LOADED!")
            for indicator_def in config.get('indicators', []):
                logger.error(f"Config indicator: {indicator_def}")
        else:
            logger.info(f"INDICATOR DATA LOADED: {len(indicator_data)} indicators:")
            for col_name, series in indicator_data.items():
                logger.info(f"  - {col_name}: {len(series)} values, "
                        f"min={series.min():.2f}, max={series.max():.2f}, "
                        f"NaN count={series.isna().sum()}")
        
        # END DEBUG
        
        # Create figure with 2 subplots: price (with indicators) + position
        num_rows = 2  # Sempre: price + position
        height_ratios = [
            plotting_config.get('layout', {}).get('price_height_ratio', 3),
            plotting_config.get('layout', {}).get('position_height_ratio', 1)
        ]
        
        fig, axes = plt.subplots(num_rows, 1, figsize=(14, 10),
                                gridspec_kw={'height_ratios': height_ratios})
        
        # Asse 0: Price chart with indicators OVERLAID
        ax_price = axes[0]
        self._plot_price_chart_with_indicators(ax_price, journal_df, trades, 
                                            config, indicators_to_plot)
        
        # Asse 1: Position chart
        ax_position = axes[1]
        self._plot_position_chart(ax_position, journal_df, trades)
        
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
        
        logger.info(f"Enhanced price signals plot saved to: {save_path}")
        return save_path

    def _plot_price_chart_with_indicators(self, ax, journal_df, trades, 
                                     config, indicators_to_plot):
        """
        Plot price chart with entry/exit signals AND indicators on same axis.
        """
        if 'timestamp' in journal_df.columns:
            journal_df['timestamp'] = pd.to_datetime(journal_df['timestamp'])
            x_axis = journal_df['timestamp']
        else:
            x_axis = journal_df.index
        
        # DEBUG: mostra range dei dati
        logger.info(f"Price range: {journal_df['price'].min():.2f} - {journal_df['price'].max():.2f}")
        
        # Plot price
        price_line, = ax.plot(x_axis, journal_df['price'], label='Price', 
                            color='black', linewidth=1.5, alpha=0.8, zorder=5)
        logger.info(f"Price line plotted: {len(journal_df['price'])} points")
        
        # Load indicator data
        indicator_data = self._load_indicator_data(journal_df, config)
        
        # Plot each indicator
        for idx, indicator_config in enumerate(indicators_to_plot):
            expected_label = indicator_config.get('label', 
                                                indicator_config.get('column', f'Indicator {idx}'))
            
            if expected_label in indicator_data:
                indicator_series = indicator_data[expected_label]
                
                # DEBUG: mostra range dell'indicatore
                logger.info(f"{expected_label} range: {indicator_series.min():.2f} - {indicator_series.max():.2f}")
                
                # Configurazione stile
                color = indicator_config.get('color', '#ff9900')  # FIX: usa colore specifico
                linewidth = indicator_config.get('linewidth', 2.0)  # Aumenta spessore
                alpha = indicator_config.get('alpha', 1.0)  # Rimuovi trasparenza
                linestyle = indicator_config.get('linestyle', '-')
                
                logger.info(f"Plotting {expected_label} with color={color}, linewidth={linewidth}")
                
                # Plot con stile molto visibile
                indicator_line, = ax.plot(x_axis, indicator_series,
                        color=color, linewidth=linewidth, alpha=alpha,
                        linestyle=linestyle, label=expected_label, zorder=10)  # Alto zorder
                
                logger.info(f"Indicator line plotted: {len(indicator_series)} points")
                
                # DEBUG: confronta primi valori
                logger.debug(f"First 3 price values: {journal_df['price'].iloc[:3].tolist()}")
                logger.debug(f"First 3 {expected_label} values: {indicator_series.iloc[:3].tolist()}")
            else:
                logger.error(f"Indicator '{expected_label}' not found in data!")
                logger.error(f"Available: {list(indicator_data.keys())}")
        
        # Plot trades
        self._plot_trade_signals(ax, trades, x_axis)
        
        # Configure axis
        ax.set_title('Price Chart with Indicators & Entry/Exit Signals', 
                    fontsize=14, fontweight='bold')
        ax.set_ylabel('Price ($)', fontsize=12)
        
        # Forza la legenda a mostrare tutto
        handles, labels = ax.get_legend_handles_labels()
        logger.info(f"Legend handles: {len(handles)}, labels: {labels}")
        ax.legend(handles, labels, loc='upper left', fontsize=9)
        
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        if 'timestamp' in journal_df.columns:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        else:
            ax.tick_params(labelbottom=False)  # Hide x-labels for top plot

    def _plot_trade_signals(self, ax, trades, x_axis):
        """
        Plot trade entry/exit signals on price chart.
        """
        if not trades:
            return
        
        trades_df = pd.DataFrame(trades)
        
        # Plot entry and exit points
        entry_points = []
        exit_points = []
        
        for _, trade in trades_df.iterrows():
            # Entry point
            if 'entry_time' in trade and 'entry_price' in trade:
                entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
                entry_points.append((entry_time, trade['entry_price']))
            
            # Exit point
            if 'exit_time' in trade and 'exit_price' in trade:
                exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
                exit_points.append((exit_time, trade['exit_price']))
        
        # Plot markers with high zorder to be visible
        if entry_points:
            entry_times, entry_prices = zip(*entry_points)
            ax.scatter(entry_times, entry_prices, color='green', 
                    marker='^', s=100, label='Entry', zorder=100, edgecolors='black', linewidth=1)
        
        if exit_points:
            exit_times, exit_prices = zip(*exit_points)
            ax.scatter(exit_times, exit_prices, color='red', 
                    marker='v', s=100, label='Exit', zorder=100, edgecolors='black', linewidth=1)
        
        # Connect entry-exit pairs
        for _, trade in trades_df.iterrows():
            if all(k in trade for k in ['entry_time', 'entry_price', 'exit_time', 'exit_price']):
                entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
                exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
                
                # Color based on P&L
                if 'net_pnl' in trade and trade['net_pnl'] > 0:
                    line_color = 'green'
                    line_style = '--'
                else:
                    line_color = 'red'
                    line_style = ':'
                
                ax.plot([entry_time, exit_time], 
                    [trade['entry_price'], trade['exit_price']],
                    color=line_color, alpha=0.5, linewidth=1,
                    linestyle=line_style, zorder=50)

    # Rimuovi i metodi non più necessari:
    # - _plot_indicator() non serve più (indicatori nello stesso panel)
    # - _plot_price_chart() originale sostituito con _plot_price_chart_with_indicators()

    def _load_indicator_data(self, journal_df: pd.DataFrame, 
                        config: Dict[str, Any]) -> Dict[str, pd.Series]:
        """
        Load pre-calculated indicator data from Parquet files.
        Adatta automaticamente: cerca prima la colonna configurata, poi 'value'.
        """
        indicator_data = {}
        
        base_data_dir = Path(config.get('data', {}).get('source_dir', 'data/raw'))
        indicators_dir = base_data_dir.parent / 'indicators'
        
        # Per ogni indicatore definito in plotting (non in indicators!)
        plotting_config = config.get('plotting', {})
        indicators_to_plot = plotting_config.get('indicators_to_plot', [])
        
        for plot_config in indicators_to_plot:
            indicator_name = plot_config.get('name')
            config_column_name = plot_config.get('column', 'sma_200')  # default
            expected_label = plot_config.get('label', config_column_name)
            
            # Trova la definizione originale dell'indicatore
            indicator_def = None
            for ind in config.get('indicators', []):
                if ind.get('name') == indicator_name:
                    indicator_def = ind
                    break
            
            if not indicator_def:
                logger.warning(f"No indicator definition found for {indicator_name}")
                continue
            
            symbol = config['data']['symbols'][0] if config['data']['symbols'] else 'UNKNOWN'
            params = indicator_def.get('params', {})
            
            # Trova il file
            indicator_file = self._find_indicator_file(indicators_dir, symbol, 
                                                    indicator_name, params)
            
            if not indicator_file:
                logger.warning(f"No file found for {indicator_name}")
                continue
            
            try:
                indicator_df = pd.read_parquet(indicator_file)
                
                # CERCA LA COLONNA GIUSTA (logica prioritaria)
                actual_column_name = None
                
                # 1. Prova 'value' (sempre presente)
                if 'value' in indicator_df.columns:
                    actual_column_name = 'value'
                
                # 2. Prova la colonna dalla config (se diversa da 'value')
                elif config_column_name in indicator_df.columns:
                    actual_column_name = config_column_name
                
                # 3. Fallback: prima colonna numerica
                else:
                    numeric_cols = indicator_df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        actual_column_name = numeric_cols[0]
                
                if not actual_column_name:
                    logger.warning(f"No data column found in {indicator_file}")
                    continue
                
                logger.info(f"Using column '{actual_column_name}' for {indicator_name}")
                
                # ALLINEAMENTO TEMPORALE
                if 'timestamp' in journal_df.columns and 'timestamp' in indicator_df.columns:
                    # Converti timestamps
                    journal_timestamps = pd.to_datetime(journal_df['timestamp'])
                    indicator_df['timestamp'] = pd.to_datetime(indicator_df['timestamp'])
                    
                    # Set index e reindex
                    indicator_df = indicator_df.set_index('timestamp')
                    aligned_series = indicator_df[actual_column_name].reindex(journal_timestamps)
                    
                    # Fill NaN (dovrebbero essere pochi)
                    nan_before = aligned_series.isna().sum()
                    if nan_before > 0:
                        logger.debug(f"Filling {nan_before} NaN values for {indicator_name}")
                        aligned_series = aligned_series.ffill().bfill()
                    
                else:
                    # Allineamento per indice
                    aligned_series = indicator_df[actual_column_name].reset_index(drop=True)
                    if len(aligned_series) != len(journal_df):
                        # Trim o pad
                        if len(aligned_series) > len(journal_df):
                            aligned_series = aligned_series.iloc[:len(journal_df)]
                        else:
                            padding = pd.Series([aligned_series.iloc[-1]] * 
                                            (len(journal_df) - len(aligned_series)))
                            aligned_series = pd.concat([aligned_series, padding], 
                                                    ignore_index=True)
                
                # Salva con il label della config (per plottaggio)
                indicator_data[expected_label] = aligned_series
                
            except Exception as e:
                logger.error(f"Error loading {indicator_name}: {e}")
        
        return indicator_data                               




    # def _plot_indicator(self, ax, journal_df, indicator_data, 
    #                indicator_config, indicator_idx):
    #     """
    #     Plot a single indicator on its axis.
    #     """
    #     column_name = indicator_config['column']
        
    #     if column_name not in indicator_data:
    #         logger.warning(f"Indicator data not found for column: {column_name}")
    #         ax.text(0.5, 0.5, f"{column_name} - Data not available",
    #                 ha='center', va='center', transform=ax.transAxes)
    #         return
        
    #     indicator_series = indicator_data[column_name]
        
    #     # Determina l'asse x (timestamp o index)
    #     if 'timestamp' in journal_df.columns:
    #         x_axis = pd.to_datetime(journal_df['timestamp'])
    #         ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    #     else:
    #         x_axis = journal_df.index
        
    #     # Plot dell'indicatore
    #     label = indicator_config.get('label', column_name)
    #     color = indicator_config.get('color', f'C{indicator_idx}')
    #     linewidth = indicator_config.get('linewidth', 1.5)
    #     alpha = indicator_config.get('alpha', 0.7)
        
    #     ax.plot(x_axis, indicator_series, 
    #             color=color, linewidth=linewidth, alpha=alpha,
    #             label=label)
        
    #     ax.set_title(f"Indicator: {label}", fontsize=11, fontweight='bold')
    #     ax.set_ylabel('Value', fontsize=10)
    #     ax.legend(loc='upper left')
    #     ax.grid(True, alpha=0.3)
        
    #     # Formatta asse x solo per l'ultimo grafico
    #     ax.tick_params(labelbottom=False) 


    # def _plot_price_chart(self, ax, journal_df, trades):
    #     """
    #     Plot price chart with entry/exit signals.
    #     """
    #     # Determina l'asse x
    #     if 'timestamp' in journal_df.columns:
    #         journal_df['timestamp'] = pd.to_datetime(journal_df['timestamp'])
    #         x_axis = journal_df['timestamp']
    #     else:
    #         x_axis = journal_df.index
        
    #     # Plot price
    #     ax.plot(x_axis, journal_df['price'], label='Price', 
    #             color='black', linewidth=1, alpha=0.7)
        
    #     # Convert trades to DataFrame if needed
    #     trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
    #     if not trades_df.empty:
    #         # Plot entry and exit points
    #         entry_points = []
    #         exit_points = []
            
    #         for _, trade in trades_df.iterrows():
    #             # Entry point
    #             if 'entry_time' in trade and 'entry_price' in trade:
    #                 entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
    #                 entry_points.append((entry_time, trade['entry_price']))
                
    #             # Exit point
    #             if 'exit_time' in trade and 'exit_price' in trade:
    #                 exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
    #                 exit_points.append((exit_time, trade['exit_price']))
            
    #         # Plot markers
    #         if entry_points:
    #             entry_times, entry_prices = zip(*entry_points)
    #             ax.scatter(entry_times, entry_prices, color='green', 
    #                     marker='^', s=100, label='Entry', zorder=5)
            
    #         if exit_points:
    #             exit_times, exit_prices = zip(*exit_points)
    #             ax.scatter(exit_times, exit_prices, color='red', 
    #                     marker='v', s=100, label='Exit', zorder=5)
            
    #         # Connect entry-exit pairs
    #         for _, trade in trades_df.iterrows():
    #             if all(k in trade for k in ['entry_time', 'entry_price', 'exit_time', 'exit_price']):
    #                 entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
    #                 exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
                    
    #                 # Color based on P&L
    #                 if 'net_pnl' in trade and trade['net_pnl'] > 0:
    #                     line_color = 'green'
    #                 else:
    #                     line_color = 'red'
                    
    #                 ax.plot([entry_time, exit_time], 
    #                     [trade['entry_price'], trade['exit_price']],
    #                     color=line_color, alpha=0.3, linewidth=1)
        
    #     ax.set_title('Price Chart with Entry/Exit Signals', fontsize=14, fontweight='bold')
    #     ax.set_ylabel('Price ($)', fontsize=12)
    #     ax.legend(loc='best')
    #     ax.grid(True, alpha=0.3)
        
    #     # Format x-axis if datetime
    #     if 'timestamp' in journal_df.columns:
    #         ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    #         plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    #     else:
    #         ax.tick_params(labelbottom=False)  # Hide x-labels for non-bottom plots

    def _plot_position_chart(self, ax, journal_df, trades):
        """
        Plot position status.
        """
        if 'timestamp' in journal_df.columns:
            x_axis = pd.to_datetime(journal_df['timestamp'])
        else:
            x_axis = journal_df.index
        
        # Plot position indicator
        if 'in_position' in journal_df.columns:
            position_signal = journal_df['in_position'].astype(float)
            
            ax.fill_between(x_axis, 0, position_signal, 
                        where=position_signal > 0, 
                        color='blue', alpha=0.3, label='In Position')
            ax.plot(x_axis, position_signal, color='blue', linewidth=1)
        
        # Add trade markers if available
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        if not trades_df.empty:
            entry_times = []
            exit_times = []
            
            for _, trade in trades_df.iterrows():
                if 'entry_time' in trade:
                    entry_time = pd.to_datetime(trade['entry_time']) if isinstance(trade['entry_time'], str) else trade['entry_time']
                    entry_times.append(entry_time)
                
                if 'exit_time' in trade:
                    exit_time = pd.to_datetime(trade['exit_time']) if isinstance(trade['exit_time'], str) else trade['exit_time']
                    exit_times.append(exit_time)
            
            if entry_times:
                ax.scatter(entry_times, [1] * len(entry_times), 
                        color='green', marker='^', s=50, zorder=5, label='Entry')
            
            if exit_times:
                ax.scatter(exit_times, [0] * len(exit_times), 
                        color='red', marker='v', s=50, zorder=5, label='Exit')
        
        ax.set_title('Position Status', fontsize=12)
        ax.set_xlabel('Time', fontsize=10)
        ax.set_ylabel('Position', fontsize=10)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['Out', 'In'])
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis
        if 'timestamp' in journal_df.columns:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)        
    

    def _find_indicator_file(self, indicators_dir: Path, symbol: str, 
                        indicator_name: str, params: Dict) -> Optional[Path]:
        """
        Find the correct indicator Parquet file based on parameters.
        """
        indicator_dir = indicators_dir / symbol
        if not indicator_dir.exists():
            logger.warning(f"Indicator directory does not exist: {indicator_dir}")
            return None
        
        logger.info(f"Searching in: {indicator_dir}")
        
        # Crea un pattern basato sui parametri
        # Es: sma_period200_1m_*.parquet
        param_str = "_".join([f"{k}{v}" for k, v in sorted(params.items())])
        
        # Pattern 1: Con parametri specifici
        if param_str:
            pattern = f"{indicator_name}_{param_str}_*.parquet"
            logger.info(f"Trying pattern 1: {pattern}")
            matching_files = list(indicator_dir.glob(pattern))
            
            if matching_files:
                logger.info(f"Found {len(matching_files)} files with pattern 1")
                # Prendi il file più recente (per timestamp o modifica)
                return max(matching_files, key=lambda x: x.stat().st_mtime)
        
        # Pattern 2: Con timeframe (dalla config)
        if 'tf' in params:
            pattern = f"{indicator_name}_*{params['tf']}*.parquet"
            logger.info(f"Trying pattern 2: {pattern}")
            matching_files = list(indicator_dir.glob(pattern))
            
            if matching_files:
                logger.info(f"Found {len(matching_files)} files with pattern 2")
                return max(matching_files, key=lambda x: x.stat().st_mtime)
        
        # Pattern 3: Qualsiasi file con il nome dell'indicatore
        pattern = f"{indicator_name}_*.parquet"
        logger.info(f"Trying pattern 3: {pattern}")
        matching_files = list(indicator_dir.glob(pattern))
        
        if matching_files:
            logger.info(f"Found {len(matching_files)} files with pattern 3")
            return max(matching_files, key=lambda x: x.stat().st_mtime)
        
        logger.warning(f"No files found for indicator: {indicator_name}")
        return None


    def create_all_plots(self, results: Dict[str, Any], run_dir: Path, config: Dict[str, Any]) -> Dict[str, Path]:
        """
        Create all standard plots for a backtest run.
        
        Args:
            results: Results dictionary from BacktestEngine
            run_dir: Directory to save plots
            config: Configuration dictionary (ADDED)
        
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
            
            # 3. Enhanced price with signals plot (NOW WITH CONFIG)
            if results.get('journal') and results.get('trades'):
                price_plot_path = run_dir / 'price_signals.png'
                plot_paths['price'] = self.plot_price_with_signals(
                    results['journal'], 
                    results['trades'], 
                    config,  # PASS CONFIG HERE
                    price_plot_path
                )
            
            logger.info(f"Created {len(plot_paths)} plots in {run_dir}")
            
        except Exception as e:
            logger.error(f"Error creating plots: {e}")
        
        return plot_paths
