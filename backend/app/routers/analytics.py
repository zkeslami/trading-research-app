"""Analytics and metrics endpoints."""
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Snapshot, Position
from app.routers.auth import get_current_user
from app.services.portfolio import portfolio_service
from app.services.data_pipeline import data_pipeline

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/portfolio")
async def get_portfolio_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current portfolio summary with metrics."""
    metrics = await portfolio_service.get_portfolio_summary(db, current_user.id)
    return metrics.to_dict()


@router.get("/allocation")
async def get_allocation_breakdown(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get portfolio allocation breakdown."""
    allocation = await portfolio_service.get_allocation_breakdown(db, current_user.id)
    return allocation


@router.get("/performance")
async def get_performance_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: str = Query("1m", description="Time period: 1w, 1m, 3m, 6m, 1y, max"),
):
    """Get portfolio performance history."""
    # Map period to days
    period_map = {
        "1w": 7,
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
        "max": 3650,
    }
    days = period_map.get(period, 30)

    history = await portfolio_service.get_performance_history(db, current_user.id, days)
    return {
        "period": period,
        "data": history,
    }


@router.post("/snapshot")
async def create_snapshot(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a portfolio snapshot for tracking."""
    snapshot = await portfolio_service.create_snapshot(db, current_user.id)
    return {
        "id": snapshot.id,
        "timestamp": snapshot.timestamp.isoformat(),
        "total_value": float(snapshot.total_value),
        "total_pnl": float(snapshot.total_pnl),
        "pnl_percent": float(snapshot.pnl_percent),
    }


@router.get("/metrics")
async def get_advanced_metrics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get advanced portfolio metrics (Sharpe, Sortino, drawdown, etc.)."""
    # Get performance history for calculations
    history = await portfolio_service.get_performance_history(db, current_user.id, 365)

    if len(history) < 2:
        return {
            "message": "Insufficient data for advanced metrics",
            "min_snapshots_required": 2,
            "current_snapshots": len(history),
        }

    # Calculate returns from history
    values = [h["total_value"] for h in history]
    returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            returns.append((values[i] - values[i-1]) / values[i-1])

    if not returns:
        return {"message": "Unable to calculate returns from history"}

    metrics = portfolio_service.calculate_risk_metrics(returns)

    # Add additional context
    metrics["period_start"] = history[0]["timestamp"] if history else None
    metrics["period_end"] = history[-1]["timestamp"] if history else None
    metrics["data_points"] = len(history)

    return metrics


@router.get("/benchmark")
async def get_benchmark_comparison(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    benchmark: str = Query("SPY", description="Benchmark ticker (SPY, QQQ, etc.)"),
    period: str = Query("1y", description="Time period: 1m, 3m, 6m, 1y"),
):
    """Compare portfolio performance against a benchmark."""
    # Get portfolio history
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 365)

    portfolio_history = await portfolio_service.get_performance_history(
        db, current_user.id, days
    )

    # Get benchmark data
    benchmark_data = await data_pipeline.get_historical_data(benchmark, period=period)

    if not benchmark_data:
        return {
            "error": f"Unable to fetch benchmark data for {benchmark}",
            "portfolio": portfolio_history,
        }

    # Calculate benchmark returns
    if benchmark_data.close:
        first_price = benchmark_data.close[0]
        benchmark_returns = [
            {"date": benchmark_data.dates[i], "return": (p - first_price) / first_price}
            for i, p in enumerate(benchmark_data.close)
        ]
    else:
        benchmark_returns = []

    # Calculate portfolio returns
    if portfolio_history and portfolio_history[0]["total_value"] > 0:
        first_value = portfolio_history[0]["total_value"]
        portfolio_returns = [
            {"date": h["timestamp"], "return": (h["total_value"] - first_value) / first_value}
            for h in portfolio_history
        ]
    else:
        portfolio_returns = []

    return {
        "period": period,
        "benchmark": benchmark,
        "portfolio_returns": portfolio_returns,
        "benchmark_returns": benchmark_returns,
    }


@router.get("/positions/performance")
async def get_positions_performance(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get performance breakdown by position."""
    positions = await portfolio_service.get_positions_with_current_values(
        db, current_user.id, "active"
    )

    # Sort by PnL
    by_pnl = sorted(positions, key=lambda x: x["pnl"], reverse=True)

    # Calculate stats
    total_pnl = sum(p["pnl"] for p in positions)
    winners = [p for p in positions if p["pnl"] > 0]
    losers = [p for p in positions if p["pnl"] < 0]

    return {
        "positions": by_pnl,
        "summary": {
            "total_positions": len(positions),
            "total_pnl": total_pnl,
            "winning_positions": len(winners),
            "losing_positions": len(losers),
            "best_performer": by_pnl[0] if by_pnl else None,
            "worst_performer": by_pnl[-1] if by_pnl else None,
        }
    }


@router.get("/asset-type-breakdown")
async def get_asset_type_breakdown(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get performance breakdown by asset type."""
    positions = await portfolio_service.get_positions_with_current_values(
        db, current_user.id, "active"
    )

    breakdown = {}
    for pos in positions:
        asset_type = pos["asset_type"]
        if asset_type not in breakdown:
            breakdown[asset_type] = {
                "count": 0,
                "total_value": 0,
                "total_cost": 0,
                "total_pnl": 0,
            }

        breakdown[asset_type]["count"] += 1
        breakdown[asset_type]["total_value"] += pos["current_value"]
        breakdown[asset_type]["total_cost"] += pos["cost_basis"]
        breakdown[asset_type]["total_pnl"] += pos["pnl"]

    # Calculate percentages
    total_value = sum(b["total_value"] for b in breakdown.values())
    for asset_type, data in breakdown.items():
        data["percent_of_portfolio"] = (
            (data["total_value"] / total_value * 100) if total_value > 0 else 0
        )
        data["pnl_percent"] = (
            (data["total_pnl"] / data["total_cost"] * 100)
            if data["total_cost"] > 0 else 0
        )

    return breakdown


@router.get("/data/price/{ticker}")
async def get_current_price(ticker: str):
    """Get current price for a ticker."""
    price_data = await data_pipeline.get_current_price(ticker.upper())

    if not price_data:
        return {"error": f"Unable to fetch price for {ticker}"}

    return price_data.model_dump()


@router.get("/data/historical/{ticker}")
async def get_historical_prices(
    ticker: str,
    period: str = Query("1y", description="Period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max"),
    interval: str = Query("1d", description="Interval: 1d, 1wk, 1mo"),
):
    """Get historical prices for a ticker."""
    hist_data = await data_pipeline.get_historical_data(
        ticker.upper(), period=period, interval=interval
    )

    if not hist_data:
        return {"error": f"Unable to fetch historical data for {ticker}"}

    return hist_data.model_dump()
