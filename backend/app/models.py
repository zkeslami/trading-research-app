"""Database models for the trading research application."""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Text, DECIMAL, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    reports: Mapped[list["Report"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    positions: Mapped[list["Position"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Report(Base):
    """Research report model."""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Request parameters
    asset_classes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array
    budget: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=500.00)
    risk_preference: Mapped[str] = mapped_column(String(20), default="moderate")  # conservative, moderate, aggressive

    # Results
    top_10_picks: Mapped[str] = mapped_column(Text, nullable=True)  # JSON with picks
    full_analysis: Mapped[str] = mapped_column(Text, nullable=True)  # Markdown report
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reports")
    positions: Mapped[list["Position"]] = relationship(back_populates="report")


class Position(Base):
    """Confirmed trade/position model."""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reports.id"), nullable=True)

    # Position details
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)  # stock, etf, crypto, bond, mutual_fund
    quantity: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    buy_price: Mapped[Decimal] = mapped_column(DECIMAL(18, 8), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, closed
    sell_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(18, 8), nullable=True)
    sell_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="positions")
    report: Mapped[Optional["Report"]] = relationship(back_populates="positions")

    @property
    def cost_basis(self) -> Decimal:
        """Calculate total cost basis."""
        return self.quantity * self.buy_price


class Snapshot(Base):
    """Portfolio snapshot for tracking trends over time."""
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Portfolio values
    total_value: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    total_cost_basis: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(DECIMAL(18, 2), nullable=False)
    pnl_percent: Mapped[Decimal] = mapped_column(DECIMAL(8, 4), nullable=False)

    # Detailed breakdown
    positions_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON snapshot of all positions
    metrics_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Sharpe, drawdown, etc.

    # Relationships
    user: Mapped["User"] = relationship(back_populates="snapshots")
