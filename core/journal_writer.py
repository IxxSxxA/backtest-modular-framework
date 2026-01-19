# core/journal_writer.py

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from reports.plotter import BacktestPlotter
    PLOTTING_AVAILABLE = True
except ImportError:
    logger.warning("Plotting module not available. Install matplotlib for visualizations.")
    PLOTTING_AVAILABLE = False


class JournalWriter:
    """
    Handles writing backtest results to files.
    Phase 2: Parquet format for better performance and compression.
    """
    
    def __init__(self, config: Dict[str, Any]):
            """
            Initialize journal writer.
            
            Args:
                config: Configuration dictionary
            """
            # Prendi directory da config o usa default
            if 'journal' in config and 'save_dir' in config['journal']:
                self.output_dir = Path(config['journal']['save_dir'])
            else:
                self.output_dir = Path("results")  # Fallback
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"JournalWriter initialized. Output directory: {self.output_dir}")
    
    # journal_writer.py, metodo save_backtest_results()

    def save_backtest_results(self, results: Dict[str, Any], config: Dict[str, Any], 
                            strategy_name: str = None) -> Dict[str, Path]:
        # Create run directory
        run_dir = self._create_run_directory(config, strategy_name)
        
        file_paths = {}
        
        # 1. Save metrics summary
        file_paths['metrics'] = self._save_metrics(results, run_dir)
        
        # 2. Save trades
        if results.get('trades'):
            file_paths['trades'] = self._save_trades_parquet(results['trades'], run_dir)
        
        # 3. Save journal
        if results.get('journal'):
            file_paths['journal'] = self._save_journal_parquet(results['journal'], run_dir)
        
        # 4. Save equity curve
        if results.get('equity_curve'):
            file_paths['equity'] = self._save_equity_parquet(results['equity_curve'], run_dir)
        
        # 5. Save configuration
        file_paths['config'] = self._save_config(config, run_dir)
        
        # ✅ 6. AGGIUNGI QUESTO - Salva DataFrame completo con indicatori
        if 'data' in results:
            data_path = run_dir / 'data_with_indicators.parquet'
            results['data'].to_parquet(data_path)
            file_paths['data'] = data_path
            logger.info(f"Saved data with indicators: {data_path}")
        
        # 7. Save summary text
        file_paths['summary'] = self._save_summary_text(results, run_dir)
        
        # 8. Create plots
        if PLOTTING_AVAILABLE:
            try:
                plotter = BacktestPlotter()
                # ✅ PASSA ANCHE run_dir al plotter
                plot_paths = plotter.create_all_plots(results, run_dir, config)
                file_paths.update(plot_paths)
                logger.info(f"Created {len(plot_paths)} plots")
            except Exception as e:
                logger.error(f"Failed to create plots: {e}")
        
        logger.info(f"Results saved to: {run_dir}")
        return file_paths
    
    def _create_run_directory(
        self, 
        config: Dict[str, Any], 
        strategy_name: str = None
    ) -> Path:
        """
        Create directory for this backtest run.
        
        Args:
            config: Configuration dictionary
            strategy_name: Optional strategy name
            
        Returns:
            Path to created directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if strategy_name:
            base_name = strategy_name
        else:
            # Extract info from config
            symbol = config['data']['symbols'][0] if config['data']['symbols'] else 'UNKNOWN'
            entry_name = config['strategy']['entry']['name']
            exit_name = config['strategy']['exit']['name']
            base_name = f"{symbol}_{entry_name}_{exit_name}"
        
        # Clean name for filesystem
        clean_name = base_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        dir_name = f"{clean_name}_{timestamp}"
        
        run_dir = self.output_dir / dir_name
        run_dir.mkdir(parents=True, exist_ok=True)
        
        return run_dir
    
    def _save_metrics(self, results: Dict[str, Any], run_dir: Path) -> Path:
        """
        Save metrics to JSON file.
        
        Args:
            results: Results dictionary
            run_dir: Run directory
            
        Returns:
            Path to saved file
        """
        # Extract metrics (exclude large data structures)
        metrics = {
            k: v for k, v in results.items() 
            if k not in ['trades', 'journal', 'equity_curve']
        }
        
        file_path = run_dir / 'metrics.json'
        
        with open(file_path, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        logger.debug(f"Metrics saved to: {file_path}")
        return file_path
    
    def _save_trades_parquet(self, trades: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save trades to Parquet file (primary format).
        
        Args:
            trades: List of trade dictionaries
            run_dir: Run directory
            
        Returns:
            Path to saved Parquet file
        """
        if not trades:
            logger.warning("No trades to save")
            return None
        
        file_path = run_dir / 'trades.parquet'
        
        try:
            # Convert to DataFrame
            df = self._prepare_trades_dataframe(trades)
            
            # Save to Parquet
            df.to_parquet(file_path, index=False)
            
            # Also save as CSV for easy inspection
            csv_path = self._save_trades_csv(trades, run_dir)
            
            original_size = df.memory_usage(deep=True).sum() / 1024
            file_size = file_path.stat().st_size / 1024
            compression_ratio = original_size / file_size if file_size > 0 else 0
            
            logger.info(f"Trades saved to: {file_path} ({len(trades)} trades, "
                       f"compressed: {file_size:.1f} KB, ratio: {compression_ratio:.1f}x)")
            logger.info(f"Also saved as CSV: {csv_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving trades to Parquet: {e}")
            # Fallback to CSV only
            logger.info("Falling back to CSV format only")
            return self._save_trades_csv(trades, run_dir)
    
    def _save_trades_csv(self, trades: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save trades to CSV file (human-readable format).
        
        Args:
            trades: List of trade dictionaries
            run_dir: Run directory
            
        Returns:
            Path to saved CSV file
        """
        import csv
        
        if not trades:
            return None
        
        file_path = run_dir / 'trades.csv'
        
        try:
            # Convert to DataFrame first for consistency
            df = self._prepare_trades_dataframe(trades)
            
            # Save to CSV
            df.to_csv(file_path, index=False, float_format='%.6f')
            
            logger.info(f"Trades CSV saved to: {file_path} ({len(trades)} trades, {len(df.columns)} columns)")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving trades to CSV: {e}")
            
            # Ultra-fallback: manual CSV writing
            try:
                with open(file_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                    writer.writeheader()
                    writer.writerows(trades)
                
                logger.info(f"Trades CSV (manual) saved to: {file_path}")
                return file_path
                
            except Exception as e2:
                logger.error(f"Even manual CSV save failed: {e2}")
                return None
    
    def _prepare_trades_dataframe(self, trades: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Prepare trades data for saving (common for Parquet and CSV).
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            DataFrame with formatted trade data
        """
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        # Convert timestamp columns to datetime
        time_columns = [col for col in df.columns if 'time' in col.lower()]
        for col in time_columns:
            if col in df.columns and df[col].notna().any():
                df[col] = pd.to_datetime(df[col])
        
        # Ensure consistent column order (optional but nice)
        preferred_order = [
            'entry_time', 'exit_time', 'entry_price', 'exit_price',
            'position_size', 'position_value', 'capital_before',
            'capital_after_entry', 'capital_after',
            'gross_pnl', 'net_pnl', 'pnl_percent', 'net_pnl_percent',
            'commission_entry', 'commission_exit',
            'bars_held', 'exit_reason', 'entry_index', 'exit_index'
        ]
        
        # Reorder columns, keeping any extra columns at the end
        existing_cols = df.columns.tolist()
        ordered_cols = [col for col in preferred_order if col in existing_cols]
        extra_cols = [col for col in existing_cols if col not in ordered_cols]
        
        df = df[ordered_cols + extra_cols]
        
        return df
    
    
    
    def _save_journal_parquet(self, journal: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save journal to Parquet file (primary format).
        
        Args:
            journal: List of journal entries
            run_dir: Run directory
            
        Returns:
            Path to saved Parquet file
        """
        if not journal:
            logger.warning("No journal entries to save")
            return None
        
        file_path = run_dir / 'journal.parquet'
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(journal)
            
            # Convert timestamp column to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Optimize data types for compression
            float_cols = df.select_dtypes(include=['float64']).columns
            for col in float_cols:
                if df[col].notna().any():
                    df[col] = df[col].astype('float32')
            
            # Save to Parquet with compression
            df.to_parquet(file_path, index=False, compression='snappy')
            
            # Also save as CSV for easy inspection (sample only for large journals)
            if len(journal) <= 100000:  # Only save CSV if not too large
                csv_path = self._save_journal_csv(journal, run_dir)
                logger.info(f"Also saved journal as CSV: {csv_path}")
            else:
                logger.info(f"Journal too large ({len(journal)} rows), skipping CSV for performance")
            
            original_size = df.memory_usage(deep=True).sum() / 1024
            file_size = file_path.stat().st_size / 1024
            compression_ratio = original_size / file_size if file_size > 0 else 0
            
            logger.info(f"Journal saved to: {file_path} ({len(journal)} entries, "
                       f"compressed: {file_size:.1f} KB, ratio: {compression_ratio:.1f}x)")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving journal to Parquet: {e}")
            # Fallback to CSV only
            logger.info("Falling back to CSV format only")
            return self._save_journal_csv(journal, run_dir)

    
    def _save_journal_csv(self, journal: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save journal to CSV file (human-readable format).
        
        Args:
            journal: List of journal entries
            run_dir: Run directory
            
        Returns:
            Path to saved CSV file
        """
        import csv
        
        if not journal:
            return None
        
        file_path = run_dir / 'journal.csv'
        
        try:
            # Convert to DataFrame first for better handling
            df = pd.DataFrame(journal)
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Save to CSV with optimized float formatting
            df.to_csv(file_path, index=False, float_format='%.6f')
            
            logger.info(f"Journal CSV saved to: {file_path} ({len(journal)} entries, {len(df.columns)} columns)")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving journal to CSV (DataFrame method): {e}")
            
            # Fallback to manual CSV writing
            try:
                # First, collect ALL possible fieldnames from all entries
                all_fieldnames = set()
                for entry in journal:
                    all_fieldnames.update(entry.keys())
                
                # Convert to list and sort for consistency
                fieldnames = sorted(all_fieldnames)
                
                with open(file_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Write each row, filling missing fields with None
                    for entry in journal:
                        complete_row = {field: entry.get(field, None) for field in fieldnames}
                        writer.writerow(complete_row)
                
                logger.info(f"Journal CSV (manual) saved to: {file_path} ({len(journal)} entries, {len(fieldnames)} columns)")
                return file_path
                
            except Exception as e2:
                logger.error(f"Even manual CSV save failed: {e2}")
                return None
    
    def _save_equity_parquet(self, equity_curve: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save equity curve to Parquet file (primary format).
        
        Args:
            equity_curve: List of equity values
            run_dir: Run directory
            
        Returns:
            Path to saved Parquet file
        """
        if not equity_curve:
            logger.warning("No equity curve to save")
            return None
        
        file_path = run_dir / 'equity_curve.parquet'
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(equity_curve)
            
            # Save to Parquet
            df.to_parquet(file_path, index=False, compression='snappy')
            
            # Also save as CSV for easy inspection
            csv_path = self._save_equity_csv(equity_curve, run_dir)
            
            logger.debug(f"Equity curve saved to: {file_path}")
            logger.debug(f"Also saved as CSV: {csv_path}")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving equity curve to Parquet: {e}")
            # Fallback to CSV only
            logger.info("Falling back to CSV format only")
            return self._save_equity_csv(equity_curve, run_dir)
    
    def _save_equity_csv(self, equity_curve: List[Dict[str, Any]], run_dir: Path) -> Path:
        """
        Save equity curve to CSV file (fallback method).
        
        Args:
            equity_curve: List of equity values
            run_dir: Run directory
            
        Returns:
            Path to saved file
        """
        import csv
        
        file_path = run_dir / 'equity_curve.csv'
        
        with open(file_path, 'w', newline='') as f:
            if equity_curve:
                writer = csv.DictWriter(f, fieldnames=equity_curve[0].keys())
                writer.writeheader()
                writer.writerows(equity_curve)
        
        logger.debug(f"Equity curve saved to CSV: {file_path}")
        return file_path
    
    def _save_config(self, config: Dict[str, Any], run_dir: Path) -> Path:
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration dictionary
            run_dir: Run directory
            
        Returns:
            Path to saved file
        """
        import yaml
        
        file_path = run_dir / 'config.yaml'
        
        with open(file_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.debug(f"Configuration saved to: {file_path}")
        return file_path
    
    def _save_summary_text(self, results: Dict[str, Any], run_dir: Path) -> Path:
        """
        Save human-readable summary to text file with detailed metrics.
        FIXED: Uses correct keys from engine results
        """
        file_path = run_dir / 'summary.txt'
        
        with open(file_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("BACKTEST SUMMARY - Detailed Performance Report\n")
            f.write("=" * 80 + "\n\n")
            
            if 'message' in results:
                f.write(f"{results['message']}\n\n")
                return file_path
            
            # === DATA VALIDATION SECTION ===
            f.write("🧪 DATA VALIDATION FROM ENGINE:\n")
            f.write("-" * 60 + "\n")
            
            # Get correct keys from engine results
            initial_capital = results.get('initial_capital', 0)
            final_total_equity = results.get('final_total_equity', 0)
            final_available_balance = results.get('final_available_balance', 0)
            total_return_pct = results.get('total_return_percent', 0)
            total_net_pnl = results.get('total_net_pnl', 0)
            total_gross_pnl = results.get('total_gross_pnl', 0)
            total_commission = results.get('total_commission', 0)
            
            # Verify data integrity
            f.write(f"initial_capital:           ${initial_capital:,.2f}\n")
            f.write(f"final_total_equity:        ${final_total_equity:,.2f}\n")
            f.write(f"final_available_balance:   ${final_available_balance:,.2f}\n")
            f.write(f"total_return_percent:      {total_return_pct:+.2f}%\n")
            f.write(f"total_net_pnl:             ${total_net_pnl:+.2f}\n")
            f.write(f"total_gross_pnl:           ${total_gross_pnl:+.2f}\n")
            f.write(f"total_commission:          ${total_commission:,.2f}\n")
            
            # Check for data inconsistencies
            if final_total_equity <= 0:
                f.write(f"⚠️  WARNING: Total equity at or below zero!\n")
            if abs(final_total_equity - final_available_balance) > 0.01:
                f.write(f"⚠️  NOTE: Position may still be open (equity ≠ balance)\n")
            
            f.write("\n")
            
            # === CORE PERFORMANCE METRICS ===
            f.write("📈 CORE PERFORMANCE METRICS:\n")
            f.write("-" * 60 + "\n")
            
            f.write(f"Initial Capital:          ${initial_capital:,.2f}\n")
            f.write(f"Final Total Equity:       ${final_total_equity:,.2f}\n")
            f.write(f"Final Available Balance:  ${final_available_balance:,.2f}\n")
            f.write(f"Total Return:             {total_return_pct:+.2f}%\n")
            f.write("\n")
            f.write(f"Gross P&L (pre-costs):    ${total_gross_pnl:+.2f}\n")
            f.write(f"Total Costs:              ${total_commission:,.2f}\n")
            f.write(f"Net P&L (after costs):    ${total_net_pnl:+.2f}\n")
            f.write("\n")
            
            # Cost impact analysis
            if total_gross_pnl != 0:
                cost_impact_pct = (abs(total_commission) / abs(total_gross_pnl)) * 100 if total_gross_pnl != 0 else 0
                f.write(f"Cost Impact:              {cost_impact_pct:.1f}% of gross P&L\n")
            
            # Break-even analysis
            if total_gross_pnl > 0 and total_net_pnl < 0:
                f.write(f"⚠️  Strategy profitable before costs, but costs cause net loss\n")
            f.write("\n")
            
            # === RISK & DRAWDOWN METRICS ===
            f.write("📊 RISK & DRAWDOWN METRICS:\n")
            f.write("-" * 60 + "\n")
            
            max_drawdown = results.get('max_drawdown_percent', 0)
            sharpe_ratio = results.get('sharpe_ratio', 0)
            sortino_ratio = results.get('sortino_ratio', 0)
            
            f.write(f"Maximum Drawdown:         {max_drawdown:.2f}%\n")
            f.write(f"Sharpe Ratio:             {sharpe_ratio:.2f}\n")
            f.write(f"Sortino Ratio:            {sortino_ratio:.2f}\n")
            
            # Drawdown severity classification
            if max_drawdown < 10:
                f.write(f"Drawdown Level:          Low (<10%)\n")
            elif max_drawdown < 20:
                f.write(f"Drawdown Level:          Moderate (10-20%)\n")
            elif max_drawdown < 30:
                f.write(f"Drawdown Level:          High (20-30%)\n")
            else:
                f.write(f"Drawdown Level:          ⚠️  Extreme (>30%)\n")
            f.write("\n")
            
            # === TRADE STATISTICS ===
            f.write("🎯 TRADE STATISTICS:\n")
            f.write("-" * 60 + "\n")
            
            total_trades = results.get('total_trades', 0)
            winning_trades = results.get('winning_trades', 0)
            losing_trades = results.get('losing_trades', 0)
            win_rate = results.get('win_rate', 0)
            profit_factor = results.get('profit_factor', 0)
            avg_net_pnl = results.get('avg_net_pnl', 0)
            avg_bars_held = results.get('avg_bars_held', 0)
            
            f.write(f"Total Trades:             {total_trades}\n")
            f.write(f"Winning Trades:           {winning_trades} ({win_rate:.1f}%)\n")
            f.write(f"Losing Trades:            {losing_trades} ({100 - win_rate:.1f}%)\n")
            f.write(f"Profit Factor:            {profit_factor:.2f}\n")
            f.write(f"Average P&L per Trade:    ${avg_net_pnl:+.2f}\n")
            f.write(f"Average Bars Held:        {avg_bars_held:.1f}\n")
            
            # Win/Loss analysis
            if total_trades > 0:
                avg_win = sum(t['net_pnl'] for t in results.get('trades', []) if t['net_pnl'] > 0) / max(winning_trades, 1)
                avg_loss = sum(t['net_pnl'] for t in results.get('trades', []) if t['net_pnl'] < 0) / max(losing_trades, 1)
                f.write(f"Average Win:              ${avg_win:+.2f}\n")
                f.write(f"Average Loss:             ${avg_loss:+.2f}\n")
                
                # Risk/Reward ratio
                if avg_loss != 0:
                    risk_reward = abs(avg_win / avg_loss)
                    f.write(f"Risk/Reward Ratio:        {risk_reward:.2f}\n")
            
            # Trade frequency
            if 'journal' in results and len(results['journal']) > 0:
                first_trade = results['journal'][0]['timestamp'] if results['journal'] else None
                last_trade = results['journal'][-1]['timestamp'] if results['journal'] else None
                
                if first_trade and last_trade:
                    from datetime import datetime
                    if isinstance(first_trade, str):
                        first_trade = datetime.fromisoformat(first_trade.replace('Z', '+00:00'))
                        last_trade = datetime.fromisoformat(last_trade.replace('Z', '+00:00'))
                    
                    days_bt = (last_trade - first_trade).days + 1
                    trades_per_day = total_trades / max(days_bt, 1)
                    f.write(f"Trading Period:           {days_bt} days\n")
                    f.write(f"Trades per Day:           {trades_per_day:.1f}\n")
            f.write("\n")
            
            # === RISK MANAGEMENT ===
            f.write("⚖️  RISK MANAGEMENT:\n")
            f.write("-" * 60 + "\n")
            
            risk_manager = results.get('risk_manager', 'None')
            f.write(f"Risk Manager:             {risk_manager}\n")
            
            # Risk per trade stats
            if results.get('trades'):
                trades = results['trades']
                if len(trades) > 0:
                    # Calculate average risk per trade
                    risk_amounts = []
                    for trade in trades:
                        if 'total_equity_before' in trade:
                            position_value = trade.get('position_value', 0)
                            equity_before = trade.get('total_equity_before', initial_capital)
                            if equity_before > 0:
                                risk_pct = (position_value / equity_before) * 100
                                risk_amounts.append(risk_pct)
                    
                    if risk_amounts:
                        avg_risk_pct = sum(risk_amounts) / len(risk_amounts)
                        max_risk_pct = max(risk_amounts)
                        min_risk_pct = min(risk_amounts)
                        
                        f.write(f"Avg Risk per Trade:       {avg_risk_pct:.1f}%\n")
                        f.write(f"Max Risk per Trade:       {max_risk_pct:.1f}%\n")
                        f.write(f"Min Risk per Trade:       {min_risk_pct:.1f}%\n")
            
            # Commission impact per trade
            if total_trades > 0:
                avg_commission = total_commission / total_trades
                f.write(f"Avg Commission per Trade: ${avg_commission:.2f}\n")
            f.write("\n")
            
            # === RECENT TRADES ===
            trades = results.get('trades', [])
            if trades:
                f.write("🔍 RECENT TRADES (Last 10):\n")
                f.write("-" * 60 + "\n")
                
                for i, trade in enumerate(trades[-10:], 1):
                    symbol = "✅" if trade.get('net_pnl', 0) > 0 else "❌"
                    
                    # Basic trade info
                    f.write(f"{i:2d}. {symbol} Entry: ${trade.get('entry_price', 0):.2f} → ")
                    f.write(f"Exit: ${trade.get('exit_price', 0):.2f}\n")
                    
                    # P&L details
                    f.write(f"     P&L: ${trade.get('net_pnl', 0):+.2f} ")
                    f.write(f"({trade.get('net_pnl_percent', 0):+.2f}%) | ")
                    
                    # Position size
                    if 'position_size' in trade:
                        f.write(f"Size: {trade.get('position_size', 0):.4f} | ")
                    
                    # Bars held and reason
                    f.write(f"Held: {trade.get('bars_held', 0)} bars | ")
                    f.write(f"Reason: {trade.get('exit_reason', 'N/A')}\n")
                    
                    # Commission info if available
                    if 'commission_entry' in trade and 'commission_exit' in trade:
                        total_trade_comm = trade.get('commission_entry', 0) + trade.get('commission_exit', 0)
                        f.write(f"     Costs: ${total_trade_comm:.2f} ")
                        
                        # Gross vs Net
                        if 'gross_pnl' in trade:
                            gross = trade.get('gross_pnl', 0)
                            net = trade.get('net_pnl', 0)
                            cost_pct = (abs(total_trade_comm) / abs(gross)) * 100 if gross != 0 else 0
                            f.write(f"(Cost Impact: {cost_pct:.1f}% of gross P&L)\n")
                        else:
                            f.write("\n")
                    
                    f.write("\n")
            
            # === VERIFICATION CALCULATIONS ===
            f.write("🧮 VERIFICATION CALCULATIONS:\n")
            f.write("-" * 60 + "\n")
            
            # Check consistency - using FINAL_TOTAL_EQUITY now
            calculated_return = ((final_total_equity / initial_capital) - 1) * 100
            f.write(f"Calculated Return:       {calculated_return:+.2f}% ")
            if abs(calculated_return - total_return_pct) < 0.01:
                f.write("✓ (Matches reported return)\n")
            else:
                f.write(f"⚠️  (Diff: {calculated_return - total_return_pct:.2f}%)\n")
            
            # Check P&L consistency
            calculated_net_pnl = final_total_equity - initial_capital
            f.write(f"Calculated Net P&L:      ${calculated_net_pnl:+.2f} ")
            if abs(calculated_net_pnl - total_net_pnl) < 0.01:
                f.write("✓ (Matches reported P&L)\n")
            else:
                f.write(f"⚠️  (Diff: ${calculated_net_pnl - total_net_pnl:.2f})\n")
            
            # Check commission consistency
            if total_gross_pnl != 0:
                calculated_gross = total_net_pnl + total_commission
                f.write(f"Calculated Gross P&L:    ${calculated_gross:+.2f} ")
                if abs(calculated_gross - total_gross_pnl) < 0.01:
                    f.write("✓ (Matches reported gross)\n")
                else:
                    f.write(f"⚠️  (Diff: ${calculated_gross - total_gross_pnl:.2f})\n")
            
            # === SUMMARY & RECOMMENDATIONS ===
            f.write("\n💡 EXECUTIVE SUMMARY:\n")
            f.write("-" * 60 + "\n")
            
            # Profitability verdict
            if total_return_pct > 0:
                f.write("🎉 STRATEGY PROFITABLE\n")
                if total_return_pct > 50:
                    f.write("   Exceptional returns (>50%)\n")
                elif total_return_pct > 20:
                    f.write("   Strong returns (20-50%)\n")
                elif total_return_pct > 5:
                    f.write("   Moderate returns (5-20%)\n")
                else:
                    f.write("   Marginal returns (<5%)\n")
            else:
                f.write("😔 STRATEGY UNPROFITABLE\n")
                if total_return_pct < -30:
                    f.write("   Significant loss (>30%)\n")
                elif total_return_pct < -10:
                    f.write("   Moderate loss (10-30%)\n")
                else:
                    f.write("   Marginal loss (<10%)\n")
            
            # Risk assessment
            if max_drawdown > 30:
                f.write("⚠️  EXTREME RISK: Drawdown >30%\n")
            elif max_drawdown > 20:
                f.write("⚠️  HIGH RISK: Drawdown 20-30%\n")
            elif max_drawdown > 10:
                f.write("⚠️  MODERATE RISK: Drawdown 10-20%\n")
            else:
                f.write("✅ ACCEPTABLE RISK: Drawdown <10%\n")
            
            # Cost efficiency assessment
            if total_commission > 0 and total_gross_pnl > 0:
                cost_efficiency = (total_net_pnl / total_gross_pnl) * 100
                f.write(f"📊 COST EFFICIENCY: {cost_efficiency:.1f}% of gross retained as net\n")
                
                if cost_efficiency < 50:
                    f.write("   ⚠️  High cost impact (>50% of gross lost to costs)\n")
                elif cost_efficiency < 80:
                    f.write("   ⚠️  Moderate cost impact (20-50% lost to costs)\n")
                else:
                    f.write("   ✅ Good cost efficiency (>80% retained)\n")
            
            # Trading frequency assessment
            if 'trades_per_day' in locals():
                if trades_per_day > 10:
                    f.write("⚡ HIGH FREQUENCY: >10 trades/day\n")
                elif trades_per_day > 5:
                    f.write("📈 ACTIVE TRADING: 5-10 trades/day\n")
                elif trades_per_day > 1:
                    f.write("📊 MODERATE TRADING: 1-5 trades/day\n")
                else:
                    f.write("🐢 LOW FREQUENCY: <1 trade/day\n")
            
            # Final recommendation
            f.write("\n🎯 RECOMMENDATIONS:\n")
            f.write("-" * 60 + "\n")
            
            if total_return_pct > 0 and max_drawdown < 20:
                f.write("✅ STRATEGY PASSES: Consider for live trading with current parameters\n")
            elif total_return_pct > 0 and max_drawdown >= 20:
                f.write("⚠️  CAUTION: Profitable but high drawdown. Consider reducing risk\n")
            elif total_return_pct <= 0 and max_drawdown > 30:
                f.write("❌ REJECT: Unprofitable with extreme drawdown\n")
            elif total_return_pct <= 0:
                f.write("🔧 NEEDS IMPROVEMENT: Consider adjusting strategy parameters\n")
            
            # File format note
            f.write("\n📁 DATA FORMAT:\n")
            f.write("-" * 60 + "\n")
            f.write("Results saved in Parquet format for optimal performance.\n")
            f.write("Use pandas to read: pd.read_parquet('filename.parquet')\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
        logger.debug(f"Detailed summary saved to: {file_path}")
        return file_path
    
    def read_parquet_file(self, file_path: Path) -> pd.DataFrame:
        """
        Utility method to read Parquet files created by JournalWriter.
        
        Args:
            file_path: Path to Parquet file
            
        Returns:
            DataFrame with the data
        """
        try:
            df = pd.read_parquet(file_path)
            logger.info(f"Read {len(df)} rows from {file_path}")
            return df
        except Exception as e:
            logger.error(f"Error reading Parquet file {file_path}: {e}")
            raise
