"""Portfolio calculation and analytics service."""
import json
from datetime import datetime
from decimal import Decimal
from typing import Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Position, Snapshot, User
from app.services.data_pipeline import data_pipeline


class PortfolioMetrics:
    """Container for portfolio metrics."""

    def __init__(
        self,
        total_value: float,
        total_cost_basis: float,
        total_pnl: float,
        pnl_percent: float,
        positions_count: int,
        sharpe_ratio: Optional[float] = None,
        sortino_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        volatility: Optional[float] = None,
        beta: Optional[float] = None,
        alpha: Optional[float] = None,
        win_rate: Optional[float] = None,
    ):
        self.total_value = total_value
        self.total_cost_basis = total_cost_basis
        self.total_pnl = total_pnl
        self.pnl_percent = pnl_percent
        self.positions_count = positions_count
        self.sharpe_ratio = sharpe_ratio
        self.sortino_ratio = sortino_ratio
        self.max_drawdown = max_drawdown
        self.volatility = volatility
        self.beta = beta
        self.alpha = alpha
        self.win_rate = win_rate

    def to_dict(self) -> dict:
        return {
            "total_value": self.total_value,
            "total_cost_basis": self.total_cost_basis,
            "total_pnl": self.total_pnl,
            "pnl_percent": self.pnl_percent,
            "positions_count": self.positions_count,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
            "beta": self.beta,
            "alpha": self.alpha,
            "win_rate": self.win_rate,
        }


class PortfolioService:
    """Service for portfolio calculations and analytics."""

    @staticmethod
    async def get_portfolio_summary(
        db: AsyncSession,
        user_id: int,
    ) -> PortfolioMetrics:
        """Get current portfolio summary with all metrics."""
        # Get active positions
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.status == "active"
            )
        )
        positions = result.scalars().all()

        if not positions:
            return PortfolioMetrics(
                total_value=0,
                total_cost_basis=0,
                total_pnl=0,
                pnl_percent=0,
                positions_count=0,
            )

        # Get current prices for all tickers
        tickers = list(set(p.ticker for p in positions))
        prices = await data_pipeline.get_multiple_prices(tickers)

        # Calculate portfolio value
        total_value = Decimal("0")
        total_cost_basis = Decimal("0")
        positions_data = []

        for pos in positions:
            cost_basis = pos.quantity * pos.buy_price
            total_cost_basis += cost_basis

            price_data = prices.get(pos.ticker)
            if price_data:
                current_value = pos.quantity * Decimal(str(price_data.current_price))
                total_value += current_value
                positions_data.append({
                    "ticker": pos.ticker,
                    "cost_basis": float(cost_basis),
                    "current_value": float(current_value),
                    "pnl": float(current_value - cost_basis),
                })
            else:
                # Use cost basis if price not available
                total_value += cost_basis
                positions_data.append({
                    "ticker": pos.ticker,
                    "cost_basis": float(cost_basis),
                    "current_value": float(cost_basis),
                    "pnl": 0,
                })

        total_pnl = total_value - total_cost_basis
        pnl_percent = (float(total_pnl) / float(total_cost_basis) * 100) if total_cost_basis > 0 else 0

        # Calculate win rate from positions
        winning_positions = sum(1 for p in positions_data if p["pnl"] > 0)
        win_rate = winning_positions / len(positions_data) if positions_data else 0

        return PortfolioMetrics(
            total_value=float(total_value),
            total_cost_basis=float(total_cost_basis),
            total_pnl=float(total_pnl),
            pnl_percent=pnl_percent,
            positions_count=len(positions),
            win_rate=win_rate,
        )

    @staticmethod
    async def get_positions_with_current_values(
        db: AsyncSession,
        user_id: int,
        status: str = "active",
    ) -> list[dict]:
        """Get positions with current market values."""
        result = await db.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.status == status
            )
        )
        positions = result.scalars().all()

        if not positions:
            return []

        # Get current prices
        tickers = list(set(p.ticker for p in positions))
        prices = await data_pipeline.get_multiple_prices(tickers)

        positions_data = []
        for pos in positions:
            cost_basis = float(pos.quantity * pos.buy_price)
            price_data = prices.get(pos.ticker)

            if price_data:
                current_price = price_data.current_price
                current_value = float(pos.quantity) * current_price
                pnl = current_value - cost_basis
                pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            else:
                current_price = float(pos.buy_price)
                current_value = cost_basis
                pnl = 0
                pnl_percent = 0

            positions_data.append({
                "id": pos.id,
                "ticker": pos.ticker,
                "asset_type": pos.asset_type,
                "quantity": float(pos.quantity),
                "buy_price": float(pos.buy_price),
                "purchase_date": pos.purchase_date.isoformat(),
                "current_price": current_price,
                "cost_basis": cost_basis,
                "current_value": current_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "status": pos.status,
                "report_id": pos.report_id,
                "notes": pos.notes,
            })

        return positions_data

    @staticmethod
    async def get_allocation_breakdown(
        db: AsyncSession,
        user_id: int,
    ) -> dict:
        """Get portfolio allocation by asset type and sector."""
        positions_data = await PortfolioService.get_positions_with_current_values(
            db, user_id, "active"
        )

        if not positions_data:
            return {"by_asset_type": {}, "by_ticker": {}}

        total_value = sum(p["current_value"] for p in positions_data)

        # Group by asset type
        by_asset_type = {}
        for pos in positions_data:
            asset_type = pos["asset_type"]
            if asset_type not in by_asset_type:
                by_asset_type[asset_type] = 0
            by_asset_type[asset_type] += pos["current_value"]

        # Convert to percentages
        by_asset_type = {
            k: {"value": v, "percent": v / total_value * 100 if total_value > 0 else 0}
            for k, v in by_asset_type.items()
        }

        # Group by ticker
        by_ticker = {}
        for pos in positions_data:
            ticker = pos["ticker"]
            if ticker not in by_ticker:
                by_ticker[ticker] = 0
            by_ticker[ticker] += pos["current_value"]

        by_ticker = {
            k: {"value": v, "percent": v / total_value * 100 if total_value > 0 else 0}
            for k, v in by_ticker.items()
        }

        return {
            "by_asset_type": by_asset_type,
            "by_ticker": by_ticker,
            "total_value": total_value,
        }

    @staticmethod
    async def create_snapshot(
        db: AsyncSession,
        user_id: int,
    ) -> Snapshot:
        """Create a portfolio snapshot for tracking trends."""
        metrics = await PortfolioService.get_portfolio_summary(db, user_id)
        positions_data = await PortfolioService.get_positions_with_current_values(
            db, user_id, "active"
        )

        snapshot = Snapshot(
            user_id=user_id,
            total_value=Decimal(str(metrics.total_value)),
            total_cost_basis=Decimal(str(metrics.total_cost_basis)),
            total_pnl=Decimal(str(metrics.total_pnl)),
            pnl_percent=Decimal(str(metrics.pnl_percent)),
            positions_json=json.dumps(positions_data),
            metrics_json=json.dumps(metrics.to_dict()),
        )

        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

        return snapshot

    @staticmethod
    async def get_performance_history(
        db: AsyncSession,
        user_id: int,
        days: int = 30,
    ) -> list[dict]:
        """Get portfolio performance history from snapshots."""
        result = await db.execute(
            select(Snapshot)
            .where(Snapshot.user_id == user_id)
            .order_by(Snapshot.timestamp.desc())
            .limit(days)
        )
        snapshots = result.scalars().all()

        return [
            {
                "timestamp": s.timestamp.isoformat(),
                "total_value": float(s.total_value),
                "total_pnl": float(s.total_pnl),
                "pnl_percent": float(s.pnl_percent),
            }
            for s in reversed(snapshots)
        ]

    @staticmethod
    def calculate_risk_metrics(returns: list[float]) -> dict:
        """Calculate risk metrics from returns series."""
        if len(returns) < 2:
            return {}

        returns_array = np.array(returns)
        risk_free_rate = 0.05 / 252  # Daily risk-free rate

        # Sharpe Ratio
        excess_returns = returns_array - risk_free_rate
        sharpe = (np.mean(excess_returns) / np.std(returns_array) * np.sqrt(252)) if np.std(returns_array) > 0 else 0

        # Sortino Ratio (only downside volatility)
        downside_returns = returns_array[returns_array < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else np.std(returns_array)
        sortino = (np.mean(excess_returns) / downside_std * np.sqrt(252)) if downside_std > 0 else 0

        # Max Drawdown
        cumulative = np.cumprod(1 + returns_array)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_drawdown = float(np.min(drawdown))

        # Volatility (annualized)
        volatility = float(np.std(returns_array) * np.sqrt(252))

        return {
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "max_drawdown": max_drawdown,
            "volatility": volatility,
        }


# Singleton instance
portfolio_service = PortfolioService()
