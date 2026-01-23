# core/journal_writer.py

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

try:
    from reports.plotter import BacktestPlotter

    PLOTTING_AVAILABLE = True
except ImportError:
    logger.warning("Plotting module not available.")
    PLOTTING_AVAILABLE = False


class JournalWriter:
    """
    Handles writing backtest results to files.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize journal writer.

        Args:
            config: Configuration dictionary
        """
        # ✅ Read from new config structure
        output_config = config.get("output", {})
        journal_config = output_config.get("journal", {})

        # Get save directory with fallback
        save_dir = journal_config.get("save_dir", "data/journals/")
        self.output_dir = Path(save_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Store full config for later use
        self.config = config

        logger.info(f"JournalWriter initialized. Output directory: {self.output_dir}")

    def save_backtest_results(
        self, results: Dict[str, Any], config: Dict[str, Any], strategy_name: str = None
    ) -> Dict[str, Path]:
        """
        Save all backtest results.

        Args:
            results: Results from BacktestEngine
            config: Full configuration
            strategy_name: Optional custom strategy name

        Returns:
            Dict of saved file paths
        """
        # Create run directory
        run_dir = self._create_run_directory(config, strategy_name)

        file_paths = {}

        # 1. Save metrics summary
        file_paths["metrics"] = self._save_metrics(results, run_dir)

        # 2. Save trades
        if results.get("trades"):
            file_paths["trades"] = self._save_trades_parquet(results["trades"], run_dir)

        # 3. Save journal
        if results.get("journal"):
            file_paths["journal"] = self._save_journal_parquet(
                results["journal"], run_dir
            )

        # 4. Save equity curve
        if results.get("equity_curve"):
            file_paths["equity"] = self._save_equity_parquet(
                results["equity_curve"], run_dir
            )

        # 5. Save configuration
        file_paths["config"] = self._save_config(config, run_dir)

        # 6. Save DataFrame with indicators
        if "data" in results:
            data_path = run_dir / "data_with_indicators.parquet"
            results["data"].to_parquet(data_path)
            file_paths["data"] = data_path
            logger.info(f"Saved data with indicators: {data_path}")

        # 7. Save summary text
        file_paths["summary"] = self._save_summary_text(results, run_dir)

        # 8. Create plots
        if PLOTTING_AVAILABLE:
            # ✅ Check if plotting is enabled in config
            plots_config = config.get("output", {}).get("plots", {})

            # Backward compatibility: also check old location
            if "plotting" in config:
                plots_config = config.get("plotting", {})
                logger.debug("Using legacy 'plotting' config location")

            if plots_config.get("enabled", True):
                try:
                    plotter = BacktestPlotter()

                    plot_paths = plotter.create_all_plots(
                        results=results,
                        run_dir=run_dir,
                        config=config,
                        full_data_df=results.get("data"),
                    )

                    file_paths.update(plot_paths)
                    logger.info(f"Created {len(plot_paths)} plots")
                except Exception as e:
                    logger.error(f"Failed to create plots: {e}")
            else:
                logger.info("Plotting disabled in config")

        logger.info(f"Results saved to: {run_dir}")
        return file_paths

    def _create_run_directory(
        self, config: Dict[str, Any], strategy_name: str = None
    ) -> Path:
        """Create directory for this backtest run."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if strategy_name:
            base_name = strategy_name
        else:
            # Extract info from config
            symbol = (
                config["data"]["symbols"][0] if config["data"]["symbols"] else "UNKNOWN"
            )

            # ✅ Get strategy timeframe
            strategy_tf = config.get("strategy", {}).get("timeframe", "1m")

            entry_name = config["strategy"]["entry"]["name"]
            exit_name = config["strategy"]["exit"]["name"]

            base_name = f"{symbol}_{strategy_tf}_{entry_name}_{exit_name}"

        clean_name = base_name.replace("/", "_").replace("\\", "_").replace(":", "_")
        dir_name = f"{clean_name}_{timestamp}"

        run_dir = self.output_dir / dir_name
        run_dir.mkdir(parents=True, exist_ok=True)

        return run_dir

    def _save_metrics(self, results: Dict[str, Any], run_dir: Path) -> Path:
        """Save metrics to JSON file."""
        metrics = {
            k: v
            for k, v in results.items()
            if k not in ["trades", "journal", "equity_curve", "data"]
        }

        file_path = run_dir / "metrics.json"

        with open(file_path, "w") as f:
            json.dump(metrics, f, indent=2, default=str)

        logger.debug(f"Metrics saved to: {file_path}")
        return file_path

    def _save_trades_parquet(self, trades: List[Dict[str, Any]], run_dir: Path) -> Path:
        """Save trades to Parquet file."""
        if not trades:
            logger.warning("No trades to save")
            return None

        file_path = run_dir / "trades.parquet"

        try:
            df = self._prepare_trades_dataframe(trades)
            df.to_parquet(file_path, index=False)

            csv_path = self._save_trades_csv(trades, run_dir)

            logger.info(f"Trades saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error saving trades: {e}")
            return self._save_trades_csv(trades, run_dir)

    def _save_trades_csv(self, trades: List[Dict[str, Any]], run_dir: Path) -> Path:
        """Save trades to CSV file."""
        if not trades:
            return None

        file_path = run_dir / "trades.csv"

        try:
            df = self._prepare_trades_dataframe(trades)
            df.to_csv(file_path, index=False, float_format="%.6f")

            logger.info(f"Trades CSV saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error saving trades CSV: {e}")
            return None

    def _prepare_trades_dataframe(self, trades: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare trades data for saving."""
        df = pd.DataFrame(trades)

        time_columns = [col for col in df.columns if "time" in col.lower()]
        for col in time_columns:
            if col in df.columns and df[col].notna().any():
                df[col] = pd.to_datetime(df[col])

        return df

    def _save_journal_parquet(
        self, journal: List[Dict[str, Any]], run_dir: Path
    ) -> Path:
        """Save journal to Parquet file."""
        if not journal:
            return None

        file_path = run_dir / "journal.parquet"

        try:
            df = pd.DataFrame(journal)

            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            df.to_parquet(file_path, index=False, compression="snappy")

            logger.info(f"Journal saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error saving journal: {e}")
            return None

    def _save_equity_parquet(
        self, equity_curve: List[Dict[str, Any]], run_dir: Path
    ) -> Path:
        """Save equity curve to Parquet."""
        if not equity_curve:
            return None

        file_path = run_dir / "equity_curve.parquet"

        try:
            df = pd.DataFrame(equity_curve)
            df.to_parquet(file_path, index=False, compression="snappy")

            logger.debug(f"Equity curve saved to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Error saving equity curve: {e}")
            return None

    def _save_config(self, config: Dict[str, Any], run_dir: Path) -> Path:
        """Save configuration to YAML file."""
        import yaml

        file_path = run_dir / "config.yaml"

        with open(file_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        logger.debug(f"Configuration saved to: {file_path}")
        return file_path

    def _save_summary_text(self, results: Dict[str, Any], run_dir: Path) -> Path:
        """Save human-readable summary."""
        file_path = run_dir / "summary.txt"

        with open(file_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("BACKTEST SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            if "message" in results:
                f.write(f"{results['message']}\n\n")
                return file_path

            f.write("📈 PERFORMANCE:\n")
            f.write("-" * 60 + "\n")
            f.write(f"Initial Capital:     ${results['initial_capital']:,.2f}\n")
            f.write(f"Final Total Equity:  ${results['final_total_equity']:,.2f}\n")
            f.write(f"Total Return:        {results['total_return_percent']:+.2f}%\n")
            f.write(f"Max Drawdown:        {results['max_drawdown_percent']:.2f}%\n\n")

            f.write("📊 TRADE STATISTICS:\n")
            f.write("-" * 60 + "\n")
            f.write(f"Total Trades:    {results['total_trades']}\n")
            f.write(
                f"Winning Trades:  {results['winning_trades']} ({results['win_rate']:.1f}%)\n"
            )
            f.write(f"Losing Trades:   {results['losing_trades']}\n")
            f.write(f"Profit Factor:   {results['profit_factor']:.2f}\n")
            f.write(f"Avg P&L/Trade:   ${results['avg_net_pnl']:+.2f}\n\n")

            if results["trades"]:
                f.write("🔍 RECENT TRADES:\n")
                f.write("-" * 60 + "\n")
                for i, trade in enumerate(results["trades"][-5:], 1):
                    symbol = "✅" if trade["net_pnl"] > 0 else "❌"
                    f.write(
                        f"{i}. {symbol} Entry: ${trade['entry_price']:.2f} → "
                        f"Exit: ${trade['exit_price']:.2f} "
                        f"({trade['net_pnl_percent']:+.2f}%) - {trade['exit_reason']}\n"
                    )

            f.write("\n" + "=" * 80 + "\n")

        logger.debug(f"Summary saved to: {file_path}")
        return file_path
