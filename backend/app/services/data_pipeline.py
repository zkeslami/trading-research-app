"""Data pipeline service for fetching market data."""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import yfinance as yf
import pandas as pd
import numpy as np
from pydantic import BaseModel


class PriceData(BaseModel):
    """Price data response model."""
    ticker: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    timestamp: datetime


class HistoricalData(BaseModel):
    """Historical data response model."""
    ticker: str
    dates: list[str]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    volume: list[int]


class DataPipelineService:
    """Service for fetching market data from various sources."""

    # Common Robinhood-tradable assets for filtering
    ROBINHOOD_CRYPTO = ["BTC", "ETH", "DOGE", "SOL", "LTC", "AVAX", "LINK", "SHIB", "XLM", "ETC"]

    # Major ETFs available on Robinhood
    MAJOR_ETFS = ["SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VEA", "VWO", "BND", "GLD", "SLV", "USO"]

    @staticmethod
    async def get_current_price(ticker: str) -> Optional[PriceData]:
        """Get current price and basic info for a ticker."""
        try:
            # Run yfinance in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: DataPipelineService._fetch_ticker_info(ticker)
            )
            return data
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return None

    @staticmethod
    def _fetch_ticker_info(ticker: str) -> Optional[PriceData]:
        """Synchronous function to fetch ticker info."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get fast info for current price
            fast_info = stock.fast_info

            return PriceData(
                ticker=ticker,
                current_price=fast_info.get("lastPrice", info.get("currentPrice", 0)),
                open_price=info.get("open", 0),
                high_price=info.get("dayHigh", 0),
                low_price=info.get("dayLow", 0),
                volume=info.get("volume", 0),
                market_cap=info.get("marketCap"),
                pe_ratio=info.get("trailingPE"),
                dividend_yield=info.get("dividendYield"),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
                fifty_two_week_low=info.get("fiftyTwoWeekLow"),
                timestamp=datetime.utcnow(),
            )
        except Exception:
            return None

    @staticmethod
    async def get_historical_data(
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        """Get historical price data for a ticker."""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: DataPipelineService._fetch_historical(ticker, period, interval)
            )
            return data
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            return None

    @staticmethod
    def _fetch_historical(ticker: str, period: str, interval: str) -> Optional[HistoricalData]:
        """Synchronous function to fetch historical data."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            if hist.empty:
                return None

            return HistoricalData(
                ticker=ticker,
                dates=[d.strftime("%Y-%m-%d") for d in hist.index],
                open=hist["Open"].tolist(),
                high=hist["High"].tolist(),
                low=hist["Low"].tolist(),
                close=hist["Close"].tolist(),
                volume=hist["Volume"].astype(int).tolist(),
            )
        except Exception:
            return None

    @staticmethod
    async def get_multiple_prices(tickers: list[str]) -> dict[str, Optional[PriceData]]:
        """Get current prices for multiple tickers concurrently."""
        tasks = [DataPipelineService.get_current_price(t) for t in tickers]
        results = await asyncio.gather(*tasks)
        return dict(zip(tickers, results))

    @staticmethod
    async def search_tickers(query: str, asset_type: str = "all") -> list[dict]:
        """Search for tickers matching a query."""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: DataPipelineService._search_tickers_sync(query, asset_type)
            )
            return results
        except Exception as e:
            print(f"Error searching tickers: {e}")
            return []

    @staticmethod
    def _search_tickers_sync(query: str, asset_type: str) -> list[dict]:
        """Synchronous ticker search."""
        try:
            # Use yfinance's search functionality
            results = []

            # Try direct lookup first
            try:
                ticker = yf.Ticker(query.upper())
                info = ticker.info
                if info.get("symbol"):
                    results.append({
                        "symbol": info.get("symbol"),
                        "name": info.get("longName", info.get("shortName", "")),
                        "type": info.get("quoteType", "UNKNOWN"),
                        "exchange": info.get("exchange", ""),
                    })
            except Exception:
                pass

            return results
        except Exception:
            return []

    @staticmethod
    def calculate_returns(prices: list[float]) -> dict:
        """Calculate various return metrics from price series."""
        if len(prices) < 2:
            return {}

        prices_array = np.array(prices)
        returns = np.diff(prices_array) / prices_array[:-1]

        return {
            "total_return": (prices[-1] - prices[0]) / prices[0],
            "mean_daily_return": float(np.mean(returns)),
            "volatility": float(np.std(returns) * np.sqrt(252)),  # Annualized
            "max_drawdown": float(DataPipelineService._calculate_max_drawdown(prices_array)),
            "sharpe_ratio": float(DataPipelineService._calculate_sharpe(returns)),
        }

    @staticmethod
    def _calculate_max_drawdown(prices: np.ndarray) -> float:
        """Calculate maximum drawdown from price series."""
        peak = np.maximum.accumulate(prices)
        drawdown = (prices - peak) / peak
        return float(np.min(drawdown))

    @staticmethod
    def _calculate_sharpe(returns: np.ndarray, risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio."""
        if np.std(returns) == 0:
            return 0.0
        excess_returns = returns - (risk_free_rate / 252)
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))

    @staticmethod
    async def get_robinhood_universe(asset_classes: list[str]) -> list[str]:
        """Get list of Robinhood-tradable tickers for specified asset classes."""
        tickers = []

        if "stock" in asset_classes or "stocks" in asset_classes:
            # Top stocks by market cap that are on Robinhood
            tickers.extend([
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
                "UNH", "JNJ", "V", "XOM", "JPM", "MA", "PG", "HD", "CVX", "MRK",
                "ABBV", "LLY", "PEP", "KO", "COST", "AVGO", "TMO", "MCD", "WMT",
                "CSCO", "ACN", "ABT", "DHR", "NEE", "VZ", "ADBE", "NKE", "TXN",
                "PM", "CMCSA", "INTC", "AMD", "QCOM", "UPS", "HON", "LOW", "COP"
            ])

        if "etf" in asset_classes or "etfs" in asset_classes:
            tickers.extend(DataPipelineService.MAJOR_ETFS)

        if "crypto" in asset_classes:
            # Add crypto tickers (with -USD suffix for yfinance)
            tickers.extend([f"{c}-USD" for c in DataPipelineService.ROBINHOOD_CRYPTO])

        return list(set(tickers))


# Singleton instance
data_pipeline = DataPipelineService()
