"""Quantitative trading strategies ported from je-suis-tm/quant-trading."""
import numpy as np
import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class Signal:
    """Trading signal with metadata."""
    action: str  # "buy", "sell", "hold"
    strength: float  # 0.0 to 1.0
    reason: str
    indicators: dict


class QuantStrategies:
    """Collection of quantitative trading strategies."""

    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return prices.rolling(window=period).mean()

    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram."""
        fast_ema = prices.ewm(span=fast_period, adjust=False).mean()
        slow_ema = prices.ewm(span=slow_period, adjust=False).mean()
        macd = fast_ema - slow_ema
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram

    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        return upper_band, sma, lower_band

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """Calculate Average True Range."""
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()

    @staticmethod
    def calculate_stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(window=d_period).mean()
        return k_line, d_line

    @staticmethod
    def heikin_ashi(
        open_prices: pd.Series,
        high_prices: pd.Series,
        low_prices: pd.Series,
        close_prices: pd.Series
    ) -> pd.DataFrame:
        """Calculate Heikin-Ashi candles."""
        ha_close = (open_prices + high_prices + low_prices + close_prices) / 4

        ha_open = pd.Series(index=open_prices.index, dtype=float)
        ha_open.iloc[0] = (open_prices.iloc[0] + close_prices.iloc[0]) / 2

        for i in range(1, len(open_prices)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2

        ha_high = pd.concat([high_prices, ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([low_prices, ha_open, ha_close], axis=1).min(axis=1)

        return pd.DataFrame({
            "HA_Open": ha_open,
            "HA_High": ha_high,
            "HA_Low": ha_low,
            "HA_Close": ha_close
        })

    @staticmethod
    def sma_crossover_signal(prices: pd.Series, short_period: int = 20, long_period: int = 50) -> Signal:
        """Generate signal based on SMA crossover."""
        sma_short = QuantStrategies.calculate_sma(prices, short_period)
        sma_long = QuantStrategies.calculate_sma(prices, long_period)

        current_short = sma_short.iloc[-1]
        current_long = sma_long.iloc[-1]
        prev_short = sma_short.iloc[-2]
        prev_long = sma_long.iloc[-2]

        indicators = {
            "sma_short": float(current_short),
            "sma_long": float(current_long),
            "current_price": float(prices.iloc[-1]),
        }

        # Bullish crossover
        if current_short > current_long and prev_short <= prev_long:
            return Signal(
                action="buy",
                strength=min(1.0, (current_short - current_long) / current_long * 10),
                reason=f"SMA{short_period} crossed above SMA{long_period}",
                indicators=indicators
            )

        # Bearish crossover
        elif current_short < current_long and prev_short >= prev_long:
            return Signal(
                action="sell",
                strength=min(1.0, (current_long - current_short) / current_long * 10),
                reason=f"SMA{short_period} crossed below SMA{long_period}",
                indicators=indicators
            )

        # Trend strength
        elif current_short > current_long:
            return Signal(
                action="hold",
                strength=0.5,
                reason=f"Uptrend: SMA{short_period} above SMA{long_period}",
                indicators=indicators
            )
        else:
            return Signal(
                action="hold",
                strength=0.5,
                reason=f"Downtrend: SMA{short_period} below SMA{long_period}",
                indicators=indicators
            )

    @staticmethod
    def macd_signal(prices: pd.Series) -> Signal:
        """Generate signal based on MACD."""
        macd, signal, histogram = QuantStrategies.calculate_macd(prices)

        current_macd = macd.iloc[-1]
        current_signal = signal.iloc[-1]
        prev_macd = macd.iloc[-2]
        prev_signal = signal.iloc[-2]
        current_hist = histogram.iloc[-1]

        indicators = {
            "macd": float(current_macd),
            "signal": float(current_signal),
            "histogram": float(current_hist),
        }

        # Bullish crossover
        if current_macd > current_signal and prev_macd <= prev_signal:
            return Signal(
                action="buy",
                strength=min(1.0, abs(current_hist) / prices.iloc[-1] * 100),
                reason="MACD crossed above signal line",
                indicators=indicators
            )

        # Bearish crossover
        elif current_macd < current_signal and prev_macd >= prev_signal:
            return Signal(
                action="sell",
                strength=min(1.0, abs(current_hist) / prices.iloc[-1] * 100),
                reason="MACD crossed below signal line",
                indicators=indicators
            )

        # Histogram divergence
        elif current_hist > 0 and current_hist > histogram.iloc[-2]:
            return Signal(
                action="hold",
                strength=0.6,
                reason="Bullish momentum increasing",
                indicators=indicators
            )
        else:
            return Signal(
                action="hold",
                strength=0.4,
                reason="Bearish momentum or consolidation",
                indicators=indicators
            )

    @staticmethod
    def rsi_signal(prices: pd.Series, oversold: int = 30, overbought: int = 70) -> Signal:
        """Generate signal based on RSI."""
        rsi = QuantStrategies.calculate_rsi(prices)
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        indicators = {
            "rsi": float(current_rsi),
            "oversold_level": oversold,
            "overbought_level": overbought,
        }

        # Oversold recovery
        if current_rsi > oversold and prev_rsi <= oversold:
            return Signal(
                action="buy",
                strength=min(1.0, (oversold - prev_rsi) / oversold + 0.5),
                reason=f"RSI recovered from oversold (below {oversold})",
                indicators=indicators
            )

        # Overbought reversal
        elif current_rsi < overbought and prev_rsi >= overbought:
            return Signal(
                action="sell",
                strength=min(1.0, (prev_rsi - overbought) / (100 - overbought) + 0.5),
                reason=f"RSI fell from overbought (above {overbought})",
                indicators=indicators
            )

        # Currently oversold (potential buy)
        elif current_rsi < oversold:
            return Signal(
                action="hold",
                strength=0.3,
                reason=f"RSI in oversold territory ({current_rsi:.1f})",
                indicators=indicators
            )

        # Currently overbought (potential sell)
        elif current_rsi > overbought:
            return Signal(
                action="hold",
                strength=0.3,
                reason=f"RSI in overbought territory ({current_rsi:.1f})",
                indicators=indicators
            )

        else:
            return Signal(
                action="hold",
                strength=0.5,
                reason=f"RSI neutral at {current_rsi:.1f}",
                indicators=indicators
            )

    @staticmethod
    def bollinger_bands_signal(prices: pd.Series) -> Signal:
        """Generate signal based on Bollinger Bands."""
        upper, middle, lower = QuantStrategies.calculate_bollinger_bands(prices)

        current_price = prices.iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]

        # Position within bands (0 = lower, 1 = upper)
        band_position = (current_price - current_lower) / (current_upper - current_lower)

        indicators = {
            "upper_band": float(current_upper),
            "middle_band": float(current_middle),
            "lower_band": float(current_lower),
            "band_position": float(band_position),
        }

        # Price near or below lower band (mean reversion buy)
        if current_price <= current_lower:
            return Signal(
                action="buy",
                strength=min(1.0, (current_lower - current_price) / current_lower * 10 + 0.7),
                reason="Price at/below lower Bollinger Band - potential mean reversion",
                indicators=indicators
            )

        # Price near or above upper band (mean reversion sell)
        elif current_price >= current_upper:
            return Signal(
                action="sell",
                strength=min(1.0, (current_price - current_upper) / current_upper * 10 + 0.7),
                reason="Price at/above upper Bollinger Band - potential mean reversion",
                indicators=indicators
            )

        # Price between bands
        else:
            if band_position > 0.5:
                return Signal(
                    action="hold",
                    strength=0.5,
                    reason=f"Price in upper half of Bollinger Bands ({band_position:.2f})",
                    indicators=indicators
                )
            else:
                return Signal(
                    action="hold",
                    strength=0.5,
                    reason=f"Price in lower half of Bollinger Bands ({band_position:.2f})",
                    indicators=indicators
                )

    @staticmethod
    def momentum_signal(prices: pd.Series, lookback: int = 252) -> Signal:
        """Generate signal based on price momentum."""
        if len(prices) < lookback + 1:
            lookback = len(prices) - 1

        momentum = (prices.iloc[-1] - prices.iloc[-lookback]) / prices.iloc[-lookback]
        momentum_short = (prices.iloc[-1] - prices.iloc[-20]) / prices.iloc[-20] if len(prices) > 20 else momentum

        indicators = {
            "momentum_long": float(momentum),
            "momentum_short": float(momentum_short),
        }

        # Strong positive momentum
        if momentum > 0.1 and momentum_short > 0:
            return Signal(
                action="buy",
                strength=min(1.0, momentum),
                reason=f"Strong positive momentum ({momentum:.1%} over {lookback} days)",
                indicators=indicators
            )

        # Strong negative momentum
        elif momentum < -0.1 and momentum_short < 0:
            return Signal(
                action="sell",
                strength=min(1.0, abs(momentum)),
                reason=f"Strong negative momentum ({momentum:.1%} over {lookback} days)",
                indicators=indicators
            )

        # Momentum reversal potential
        elif momentum > 0 and momentum_short < 0:
            return Signal(
                action="hold",
                strength=0.4,
                reason="Long-term positive but short-term negative momentum",
                indicators=indicators
            )
        elif momentum < 0 and momentum_short > 0:
            return Signal(
                action="hold",
                strength=0.6,
                reason="Long-term negative but short-term positive momentum",
                indicators=indicators
            )
        else:
            return Signal(
                action="hold",
                strength=0.5,
                reason=f"Neutral momentum ({momentum:.1%})",
                indicators=indicators
            )

    @staticmethod
    def aggregate_signals(signals: list[Signal]) -> Signal:
        """Aggregate multiple signals into a consensus."""
        buy_signals = [s for s in signals if s.action == "buy"]
        sell_signals = [s for s in signals if s.action == "sell"]

        buy_strength = sum(s.strength for s in buy_signals) / len(signals) if buy_signals else 0
        sell_strength = sum(s.strength for s in sell_signals) / len(signals) if sell_signals else 0

        # Combine all indicators
        all_indicators = {}
        for s in signals:
            all_indicators.update(s.indicators)

        reasons = [s.reason for s in signals]

        if buy_strength > sell_strength and buy_strength > 0.3:
            return Signal(
                action="buy",
                strength=buy_strength,
                reason=" | ".join([s.reason for s in buy_signals]),
                indicators=all_indicators
            )
        elif sell_strength > buy_strength and sell_strength > 0.3:
            return Signal(
                action="sell",
                strength=sell_strength,
                reason=" | ".join([s.reason for s in sell_signals]),
                indicators=all_indicators
            )
        else:
            return Signal(
                action="hold",
                strength=0.5,
                reason="Mixed signals - no clear consensus",
                indicators=all_indicators
            )


# Singleton instance
quant_strategies = QuantStrategies()
