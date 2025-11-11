"""Data export system for sharing and analysis"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from src.analytics.trade_db import TradeDB
from src.analytics.performance import PerformanceAnalytics
from src.utils.logger import setup_logger


class DataExporter:
    """Export trading data for analysis and sharing"""
    
    def __init__(self, trade_db: TradeDB):
        """
        Initialize data exporter.
        
        Args:
            trade_db: TradeDB instance
        """
        self.trade_db = trade_db
        self.analytics = PerformanceAnalytics()
        self.logger = setup_logger(f"{__name__}.DataExporter")
    
    def export_json(
        self,
        output_path: str,
        anonymize: bool = False,
        symbol: Optional[str] = None
    ) -> str:
        """
        Export comprehensive JSON report.
        
        Args:
            output_path: Output file path
            anonymize: Whether to remove personal identifiers
            symbol: Filter by symbol (optional)
            
        Returns:
            Path to exported file
        """
        # Get data
        trades = self.trade_db.get_trades(symbol=symbol)
        signals = self.trade_db.get_signals(symbol=symbol)
        risk_events = self.trade_db.get_risk_events()
        
        # Calculate metrics
        metrics = self.analytics.calculate_metrics(trades)
        
        # Build report
        report = {
            'export_date': datetime.utcnow().isoformat(),
            'summary': {
                'total_trades': len(trades),
                'total_signals': len(signals),
                'total_risk_events': len(risk_events),
                'performance_metrics': metrics
            },
            'trades': trades,
            'signals': signals,
            'risk_events': risk_events,
            'analysis': {
                'by_exchange': self.analytics.analyze_by_exchange(trades),
                'by_symbol': self.analytics.analyze_by_symbol(trades)
            }
        }
        
        if anonymize:
            report = self._anonymize_data(report)
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Exported JSON report to {output_file}")
        return str(output_file)
    
    def export_csv(self, output_dir: str, symbol: Optional[str] = None) -> Dict[str, str]:
        """
        Export CSV files for easy analysis.
        
        Args:
            output_dir: Output directory
            symbol: Filter by symbol (optional)
            
        Returns:
            Dictionary with file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        files = {}
        
        # Export trades
        trades = self.trade_db.get_trades(symbol=symbol)
        if trades:
            trades_file = output_path / "trades.csv"
            with open(trades_file, 'w', newline='') as f:
                if trades:
                    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                    writer.writeheader()
                    writer.writerows(trades)
            files['trades'] = str(trades_file)
        
        # Export signals
        signals = self.trade_db.get_signals(symbol=symbol)
        if signals:
            signals_file = output_path / "signals.csv"
            with open(signals_file, 'w', newline='') as f:
                if signals:
                    writer = csv.DictWriter(f, fieldnames=signals[0].keys())
                    writer.writeheader()
                    writer.writerows(signals)
            files['signals'] = str(signals_file)
        
        # Export performance summary
        metrics = self.analytics.calculate_metrics(trades)
        performance_file = output_path / "performance.csv"
        with open(performance_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=metrics.keys())
            writer.writeheader()
            writer.writerow(metrics)
        files['performance'] = str(performance_file)
        
        self.logger.info(f"Exported CSV files to {output_path}")
        return files
    
    def export_summary_report(self, output_path: str, symbol: Optional[str] = None) -> str:
        """
        Export human-readable summary report.
        
        Args:
            output_path: Output file path
            symbol: Filter by symbol (optional)
            
        Returns:
            Path to exported file
        """
        trades = self.trade_db.get_trades(symbol=symbol)
        metrics = self.analytics.calculate_metrics(trades)
        
        report_lines = [
            "# Trading Bot Performance Report",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Summary",
            f"- Total Trades: {metrics['total_trades']}",
            f"- Winning Trades: {metrics['winning_trades']}",
            f"- Losing Trades: {metrics['losing_trades']}",
            f"- Win Rate: {metrics['win_rate']:.2%}",
            f"- Total P&L: {metrics['total_pnl']:.2f}",
            f"- Average Win: {metrics['average_win']:.2f}",
            f"- Average Loss: {metrics['average_loss']:.2f}",
            f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}",
            "",
            "## Performance by Exchange",
        ]
        
        exchange_stats = self.analytics.analyze_by_exchange(trades)
        for exchange, stats in exchange_stats.items():
            report_lines.append(f"- {exchange}: {stats['trades']} trades, P&L: {stats['pnl']:.2f}")
        
        report_lines.extend([
            "",
            "## Performance by Symbol",
        ])
        
        symbol_stats = self.analytics.analyze_by_symbol(trades)
        for symbol_name, stats in symbol_stats.items():
            report_lines.append(f"- {symbol_name}: {stats['trades']} trades, P&L: {stats['pnl']:.2f}")
        
        report_text = "\n".join(report_lines)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(report_text)
        
        self.logger.info(f"Exported summary report to {output_file}")
        return str(output_file)
    
    def _anonymize_data(self, data: Dict) -> Dict:
        """Remove personal identifiers from data"""
        anonymized = data.copy()
        
        # Remove exchange-specific identifiers
        if 'trades' in anonymized:
            for trade in anonymized['trades']:
                if 'exchange_order_id' in trade:
                    del trade['exchange_order_id']
        
        return anonymized

