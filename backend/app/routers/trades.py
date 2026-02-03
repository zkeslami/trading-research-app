"""Trade tracking endpoints."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Position, User
from app.routers.auth import get_current_user
from app.services.portfolio import portfolio_service

router = APIRouter(prefix="/trades", tags=["trades"])


# Pydantic schemas
class PositionCreate(BaseModel):
    ticker: str
    asset_type: str  # stock, etf, crypto, bond, mutual_fund
    quantity: float
    buy_price: float
    purchase_date: date
    report_id: Optional[int] = None
    notes: Optional[str] = None


class PositionClose(BaseModel):
    sell_price: float
    sell_date: Optional[date] = None


class PositionResponse(BaseModel):
    id: int
    ticker: str
    asset_type: str
    quantity: float
    buy_price: float
    purchase_date: date
    status: str
    sell_price: Optional[float] = None
    sell_date: Optional[date] = None
    notes: Optional[str] = None
    report_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PositionWithValue(BaseModel):
    id: int
    ticker: str
    asset_type: str
    quantity: float
    buy_price: float
    purchase_date: str
    current_price: float
    cost_basis: float
    current_value: float
    pnl: float
    pnl_percent: float
    status: str
    report_id: Optional[int] = None
    notes: Optional[str] = None


# Endpoints
@router.post("/confirm", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def confirm_trade(
    position_data: PositionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Log a confirmed trade/purchase."""
    # Validate asset type
    valid_asset_types = ["stock", "etf", "crypto", "bond", "mutual_fund"]
    if position_data.asset_type not in valid_asset_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid asset type. Must be one of: {', '.join(valid_asset_types)}",
        )

    position = Position(
        user_id=current_user.id,
        ticker=position_data.ticker.upper(),
        asset_type=position_data.asset_type,
        quantity=Decimal(str(position_data.quantity)),
        buy_price=Decimal(str(position_data.buy_price)),
        purchase_date=position_data.purchase_date,
        report_id=position_data.report_id,
        notes=position_data.notes,
        status="active",
    )

    db.add(position)
    await db.commit()
    await db.refresh(position)

    return position


@router.get("/positions", response_model=list[PositionWithValue])
async def get_positions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str = Query("active", description="Filter by status: active, closed, all"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
):
    """Get all positions with current values."""
    if status == "all":
        positions = await portfolio_service.get_positions_with_current_values(
            db, current_user.id, "active"
        )
        closed = await portfolio_service.get_positions_with_current_values(
            db, current_user.id, "closed"
        )
        positions.extend(closed)
    else:
        positions = await portfolio_service.get_positions_with_current_values(
            db, current_user.id, status
        )

    # Filter by asset type if specified
    if asset_type:
        positions = [p for p in positions if p["asset_type"] == asset_type]

    return positions


@router.get("/positions/{position_id}", response_model=PositionWithValue)
async def get_position(
    position_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific position with current value."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )

    # Get position with current value
    positions = await portfolio_service.get_positions_with_current_values(
        db, current_user.id, position.status
    )

    pos_data = next((p for p in positions if p["id"] == position_id), None)
    if not pos_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )

    return pos_data


@router.put("/positions/{position_id}/close", response_model=PositionResponse)
async def close_position(
    position_id: int,
    close_data: PositionClose,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Close a position (mark as sold)."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )

    if position.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is already closed",
        )

    position.status = "closed"
    position.sell_price = Decimal(str(close_data.sell_price))
    position.sell_date = close_data.sell_date or date.today()

    await db.commit()
    await db.refresh(position)

    return position


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a position."""
    result = await db.execute(
        select(Position).where(
            Position.id == position_id,
            Position.user_id == current_user.id
        )
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )

    await db.delete(position)
    await db.commit()


@router.get("/history")
async def get_trade_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get trade history (closed positions)."""
    result = await db.execute(
        select(Position)
        .where(
            Position.user_id == current_user.id,
            Position.status == "closed"
        )
        .order_by(Position.sell_date.desc())
        .offset(offset)
        .limit(limit)
    )
    positions = result.scalars().all()

    history = []
    for pos in positions:
        cost_basis = float(pos.quantity * pos.buy_price)
        sale_value = float(pos.quantity * pos.sell_price) if pos.sell_price else cost_basis
        pnl = sale_value - cost_basis
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0

        history.append({
            "id": pos.id,
            "ticker": pos.ticker,
            "asset_type": pos.asset_type,
            "quantity": float(pos.quantity),
            "buy_price": float(pos.buy_price),
            "sell_price": float(pos.sell_price) if pos.sell_price else None,
            "purchase_date": pos.purchase_date.isoformat(),
            "sell_date": pos.sell_date.isoformat() if pos.sell_date else None,
            "cost_basis": cost_basis,
            "sale_value": sale_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "holding_period_days": (pos.sell_date - pos.purchase_date).days if pos.sell_date else None,
        })

    return history


@router.get("/summary")
async def get_trade_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get summary of all trades."""
    # Get all positions
    result = await db.execute(
        select(Position).where(Position.user_id == current_user.id)
    )
    positions = result.scalars().all()

    active_positions = [p for p in positions if p.status == "active"]
    closed_positions = [p for p in positions if p.status == "closed"]

    # Calculate closed position stats
    total_realized_pnl = 0
    winning_trades = 0
    losing_trades = 0

    for pos in closed_positions:
        if pos.sell_price:
            cost = float(pos.quantity * pos.buy_price)
            sale = float(pos.quantity * pos.sell_price)
            pnl = sale - cost
            total_realized_pnl += pnl

            if pnl > 0:
                winning_trades += 1
            elif pnl < 0:
                losing_trades += 1

    win_rate = (winning_trades / len(closed_positions) * 100) if closed_positions else 0

    return {
        "active_positions_count": len(active_positions),
        "closed_positions_count": len(closed_positions),
        "total_trades": len(positions),
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_realized_pnl": total_realized_pnl,
    }
