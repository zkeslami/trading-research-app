"""Backtesting service for strategy validation."""
from datetime import datetime, timedelta
from typing import Optional
import numpy as np
import pandas as pd


class BacktestResult:
    """Container for backtest results."""

    def __init__(
        self,
        ticker: str,
        strategy: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        final_value: float,
        total_return: float,
        annualized_return: float,
        sharpe_ratio: float,
        sortino_ratio: float,
        max_drawdown: float,
        volatility: float,
        win_rate: float,
        total_trades: int,
        equity_curve: list[dict],
    ):
        self.ticker = ticker
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.final_value = final_value
        self.total_return = total_return
        self.annualized_return = annualized_return
        self.sharpe_ratio = sharpe_ratio
        self.sortino_ratio = sortino_ratio
        self.max_drawdown = max_drawdown
        self.volatility = volatility
        self.win_rate = win_rate
        self.total_trades = total_trades
        self.equity_curve = equity_curve

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "strategy": self.strategy,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_capital": self.initial_capital,
            "final_value": self.final_value,
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "equity_curve": self.equity_curve,
        }


class BacktestService:
    """Service for backtesting trading strategies."""

    # Available strategies
    STRATEGIES = {
        "buy_and_hold": "Simple buy and hold strategy",
        "sma_crossover": "SMA crossover (20/50 day)",
        "macd": "MACD signal crossover",
        "rsi_reversal": "RSI overbought/oversold reversal",
        "momentum": "Price momentum strategy",
        "mean_reversion": "Bollinger Bands mean reversion",
    }

    @staticmethod
    def run_backtest(
        prices: pd.DataFrame,
        strategy: str = "buy_and_hold",
        initial_capital: float = 10000.0,
    ) -> BacktestResult:
        """Run a backtest on historical price data."""
        if strategy == "buy_and_hold":
            return BacktestService._buy_and_hold(prices, initial_capital)
        elif strategy == "sma_crossover":
            return BacktestService._sma_crossover(prices, initial_capital)
        elif strategy == "macd":
            return BacktestService._macd_strategy(prices, initial_capital)
        elif strategy == "rsi_reversal":
            return BacktestService._rsi_strategy(prices, initial_capital)
        elif strategy == "momentum":
            return BacktestService._momentum_strategy(prices, initial_capital)
        elif strategy == "mean_reversion":
            return BacktestService._mean_reversion(prices, initial_capital)
        else:
            return BacktestService._buy_and_hold(prices, initial_capital)

    @staticmethod
    def _calculate_metrics(
        equity_curve: np.ndarray,
        returns: np.ndarray,
        trades: list,
        ticker: str,
        strategy: str,
        dates: list,
        initial_capital: float,
    ) -> BacktestResult:
        """Calculate backtest metrics from equity curve and returns."""
        # Total and annualized returns
        total_return = (equity_curve[-1] - initial_capital) / initial_capital
        days = len(returns)
        annualized_return = ((1 + total_return) ** (252 / max(days, 1))) - 1

        # Sharpe ratio
        risk_free_rate = 0.05 / 252
        excess_returns = returns - risk_free_rate
        sharpe = (np.mean(excess_returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(returns)
        sortino = (np.mean(excess_returns) / downside_std * np.sqrt(252)) if downside_std > 0 else 0

        # Max drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        max_drawdown = float(np.min(drawdown))

        # Volatility
        volatility = float(np.std(returns) * np.sqrt(252))

        # Win rate
        winning_trades = sum(1 for t in trades if t.get("pnl", 0) > 0)
        win_rate = winning_trades / len(trades) if trades else 0

        # Build equity curve data
        equity_data = [
            {"date": dates[i], "value": float(equity_curve[i])}
            for i in range(0, len(equity_curve), max(1, len(equity_curve) // 100))
        ]

        return BacktestResult(
            ticker=ticker,
            strategy=strategy,
            start_date=dates[0] if dates else "",
            end_date=dates[-1] if dates else "",
            initial_capital=initial_capital,
            final_value=float(equity_curve[-1]),
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown=max_drawdown,
            volatility=volatility,
            win_rate=win_rate,
            total_trades=len(trades),
            equity_curve=equity_data,
        )

    @staticmethod
    def _buy_and_hold(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """Simple buy and hold strategy."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Buy on first day, hold throughout
        shares = initial_capital / close_prices[0]
        equity_curve = shares * close_prices

        # Calculate daily returns
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        trades = [{"type": "buy", "date": dates[0], "price": close_prices[0], "shares": shares}]

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "buy_and_hold", dates, initial_capital
        )

    @staticmethod
    def _sma_crossover(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """SMA crossover strategy (20/50 day)."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Calculate SMAs
        sma_short = pd.Series(close_prices).rolling(20).mean().values
        sma_long = pd.Series(close_prices).rolling(50).mean().values

        # Generate signals
        position = 0
        cash = initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for i in range(len(close_prices)):
            # Calculate current equity
            equity = cash + shares * close_prices[i]
            equity_curve.append(equity)

            if i < 50:  # Wait for SMAs to warm up
                continue

            # Buy signal: short SMA crosses above long SMA
            if sma_short[i] > sma_long[i] and sma_short[i-1] <= sma_long[i-1] and position == 0:
                shares = cash / close_prices[i]
                cash = 0
                position = 1
                trades.append({"type": "buy", "date": dates[i], "price": close_prices[i], "shares": shares})

            # Sell signal: short SMA crosses below long SMA
            elif sma_short[i] < sma_long[i] and sma_short[i-1] >= sma_long[i-1] and position == 1:
                cash = shares * close_prices[i]
                pnl = cash - initial_capital if len(trades) > 0 else 0
                trades.append({"type": "sell", "date": dates[i], "price": close_prices[i], "pnl": pnl})
                shares = 0
                position = 0

        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "sma_crossover", dates, initial_capital
        )

    @staticmethod
    def _macd_strategy(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """MACD signal crossover strategy."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Calculate MACD
        exp12 = pd.Series(close_prices).ewm(span=12).mean()
        exp26 = pd.Series(close_prices).ewm(span=26).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9).mean()

        macd = macd.values
        signal = signal.values

        # Generate signals
        position = 0
        cash = initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for i in range(len(close_prices)):
            equity = cash + shares * close_prices[i]
            equity_curve.append(equity)

            if i < 35:  # Wait for MACD to warm up
                continue

            # Buy signal: MACD crosses above signal
            if macd[i] > signal[i] and macd[i-1] <= signal[i-1] and position == 0:
                shares = cash / close_prices[i]
                cash = 0
                position = 1
                trades.append({"type": "buy", "date": dates[i], "price": close_prices[i], "shares": shares})

            # Sell signal: MACD crosses below signal
            elif macd[i] < signal[i] and macd[i-1] >= signal[i-1] and position == 1:
                cash = shares * close_prices[i]
                pnl = cash - initial_capital if len(trades) > 0 else 0
                trades.append({"type": "sell", "date": dates[i], "price": close_prices[i], "pnl": pnl})
                shares = 0
                position = 0

        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "macd", dates, initial_capital
        )

    @staticmethod
    def _rsi_strategy(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """RSI overbought/oversold reversal strategy."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Calculate RSI
        delta = pd.Series(close_prices).diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.values

        # Generate signals
        position = 0
        cash = initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for i in range(len(close_prices)):
            equity = cash + shares * close_prices[i]
            equity_curve.append(equity)

            if i < 20:
                continue

            # Buy signal: RSI crosses above 30 (oversold recovery)
            if rsi[i] > 30 and rsi[i-1] <= 30 and position == 0:
                shares = cash / close_prices[i]
                cash = 0
                position = 1
                trades.append({"type": "buy", "date": dates[i], "price": close_prices[i], "shares": shares})

            # Sell signal: RSI crosses above 70 (overbought)
            elif rsi[i] > 70 and position == 1:
                cash = shares * close_prices[i]
                pnl = cash - initial_capital if len(trades) > 0 else 0
                trades.append({"type": "sell", "date": dates[i], "price": close_prices[i], "pnl": pnl})
                shares = 0
                position = 0

        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "rsi_reversal", dates, initial_capital
        )

    @staticmethod
    def _momentum_strategy(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """Price momentum strategy (12-month lookback)."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Calculate momentum (252-day return)
        lookback = min(252, len(close_prices) - 1)
        momentum = pd.Series(close_prices).pct_change(lookback).values

        # Generate signals
        position = 0
        cash = initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for i in range(len(close_prices)):
            equity = cash + shares * close_prices[i]
            equity_curve.append(equity)

            if i < lookback + 1:
                continue

            # Buy signal: positive momentum
            if momentum[i] > 0 and position == 0:
                shares = cash / close_prices[i]
                cash = 0
                position = 1
                trades.append({"type": "buy", "date": dates[i], "price": close_prices[i], "shares": shares})

            # Sell signal: negative momentum
            elif momentum[i] < 0 and position == 1:
                cash = shares * close_prices[i]
                pnl = cash - initial_capital if len(trades) > 0 else 0
                trades.append({"type": "sell", "date": dates[i], "price": close_prices[i], "pnl": pnl})
                shares = 0
                position = 0

        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "momentum", dates, initial_capital
        )

    @staticmethod
    def _mean_reversion(prices: pd.DataFrame, initial_capital: float) -> BacktestResult:
        """Bollinger Bands mean reversion strategy."""
        close_prices = prices["Close"].values
        dates = [d.strftime("%Y-%m-%d") for d in prices.index]

        # Calculate Bollinger Bands
        sma = pd.Series(close_prices).rolling(20).mean()
        std = pd.Series(close_prices).rolling(20).std()
        upper_band = (sma + 2 * std).values
        lower_band = (sma - 2 * std).values
        sma = sma.values

        # Generate signals
        position = 0
        cash = initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for i in range(len(close_prices)):
            equity = cash + shares * close_prices[i]
            equity_curve.append(equity)

            if i < 25:
                continue

            # Buy signal: price touches lower band
            if close_prices[i] <= lower_band[i] and position == 0:
                shares = cash / close_prices[i]
                cash = 0
                position = 1
                trades.append({"type": "buy", "date": dates[i], "price": close_prices[i], "shares": shares})

            # Sell signal: price touches upper band or SMA
            elif close_prices[i] >= sma[i] and position == 1:
                cash = shares * close_prices[i]
                pnl = cash - initial_capital if len(trades) > 0 else 0
                trades.append({"type": "sell", "date": dates[i], "price": close_prices[i], "pnl": pnl})
                shares = 0
                position = 0

        equity_curve = np.array(equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        returns = np.insert(returns, 0, 0)

        return BacktestService._calculate_metrics(
            equity_curve, returns, trades, prices.attrs.get("ticker", "UNKNOWN"),
            "mean_reversion", dates, initial_capital
        )


# Singleton instance
backtest_service = BacktestService()
