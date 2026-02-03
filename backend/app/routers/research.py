"""Research generation endpoints."""
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Report, User
from app.routers.auth import get_current_user
from app.agents.router import create_agent_router
from app.config import settings

router = APIRouter(prefix="/research", tags=["research"])


# Pydantic schemas
class ResearchRequest(BaseModel):
    asset_classes: list[str]  # stocks, etfs, crypto, bonds, mutual_funds
    budget: float = 500.0
    risk_preference: str = "moderate"  # conservative, moderate, aggressive
    specific_tickers: Optional[list[str]] = None


class ReportResponse(BaseModel):
    id: int
    created_at: datetime
    asset_classes: str
    budget: float
    risk_preference: str
    status: str
    top_10_picks: Optional[str] = None
    full_analysis: Optional[str] = None

    class Config:
        from_attributes = True


class PickSummary(BaseModel):
    rank: int
    ticker: str
    current_price: float
    expected_1y_yield: float
    confidence: float
    risk_level: str
    allocation_percent: float
    allocation_amount: float
    rationale: str


class ReportDetail(BaseModel):
    id: int
    created_at: datetime
    asset_classes: list[str]
    budget: float
    risk_preference: str
    status: str
    picks: list[PickSummary]
    full_report: str


async def run_research_task(
    report_id: int,
    asset_classes: list[str],
    budget: float,
    risk_preference: str,
    specific_tickers: Optional[list[str]],
    db: AsyncSession,
):
    """Background task to run research pipeline."""
    try:
        # Update status to processing
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            return

        report.status = "processing"
        await db.commit()

        # Create agent router and run research
        agent_router = create_agent_router(
            llm_provider=settings.LLM_PROVIDER,
            api_key=settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY,
        )

        research_result = await agent_router.run_research(
            asset_classes=asset_classes,
            budget=budget,
            risk_preference=risk_preference,
            specific_tickers=specific_tickers,
        )

        # Update report with results
        report.top_10_picks = json.dumps(research_result.get("ranked_picks", []))
        report.full_analysis = research_result.get("full_report", "")
        report.status = "completed"
        await db.commit()

    except Exception as e:
        # Mark as failed
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report:
            report.status = "failed"
            report.full_analysis = f"Research failed: {str(e)}"
            await db.commit()


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a new research report."""
    # Validate asset classes
    valid_classes = ["stocks", "etfs", "crypto", "bonds", "mutual_funds"]
    for ac in request.asset_classes:
        if ac.lower() not in valid_classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid asset class '{ac}'. Must be one of: {', '.join(valid_classes)}",
            )

    # Validate risk preference
    if request.risk_preference not in ["conservative", "moderate", "aggressive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk preference must be: conservative, moderate, or aggressive",
        )

    # Create report record
    report = Report(
        user_id=current_user.id,
        asset_classes=json.dumps(request.asset_classes),
        budget=Decimal(str(request.budget)),
        risk_preference=request.risk_preference,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Start research in background
    background_tasks.add_task(
        run_research_task,
        report.id,
        request.asset_classes,
        request.budget,
        request.risk_preference,
        request.specific_tickers,
        db,
    )

    return report


@router.post("/generate-sync", response_model=ReportDetail)
async def generate_research_sync(
    request: ResearchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a research report synchronously (blocking)."""
    # Validate inputs
    valid_classes = ["stocks", "etfs", "crypto", "bonds", "mutual_funds"]
    for ac in request.asset_classes:
        if ac.lower() not in valid_classes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid asset class '{ac}'. Must be one of: {', '.join(valid_classes)}",
            )

    if request.risk_preference not in ["conservative", "moderate", "aggressive"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Risk preference must be: conservative, moderate, or aggressive",
        )

    # Create agent router and run research
    agent_router = create_agent_router(
        llm_provider=settings.LLM_PROVIDER,
        api_key=settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY,
    )

    research_result = await agent_router.run_research(
        asset_classes=request.asset_classes,
        budget=request.budget,
        risk_preference=request.risk_preference,
        specific_tickers=request.specific_tickers,
    )

    # Save report
    report = Report(
        user_id=current_user.id,
        asset_classes=json.dumps(request.asset_classes),
        budget=Decimal(str(request.budget)),
        risk_preference=request.risk_preference,
        status="completed",
        top_10_picks=json.dumps(research_result.get("ranked_picks", [])),
        full_analysis=research_result.get("full_report", ""),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Parse picks for response
    picks = research_result.get("ranked_picks", [])

    return ReportDetail(
        id=report.id,
        created_at=report.created_at,
        asset_classes=request.asset_classes,
        budget=request.budget,
        risk_preference=request.risk_preference,
        status="completed",
        picks=[PickSummary(**p) for p in picks],
        full_report=research_result.get("full_report", ""),
    )


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List user's research reports."""
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    reports = result.scalars().all()
    return reports


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific research report."""
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Parse data
    asset_classes = json.loads(report.asset_classes) if report.asset_classes else []
    picks_data = json.loads(report.top_10_picks) if report.top_10_picks else []

    picks = []
    for p in picks_data:
        picks.append(PickSummary(
            rank=p.get("rank", 0),
            ticker=p.get("ticker", ""),
            current_price=p.get("current_price", 0),
            expected_1y_yield=p.get("expected_1y_yield", 0),
            confidence=p.get("confidence", 0),
            risk_level=p.get("risk_level", "medium"),
            allocation_percent=p.get("allocation_percent", 0),
            allocation_amount=p.get("allocation_amount", 0),
            rationale=p.get("rationale", ""),
        ))

    return ReportDetail(
        id=report.id,
        created_at=report.created_at,
        asset_classes=asset_classes,
        budget=float(report.budget),
        risk_preference=report.risk_preference,
        status=report.status,
        picks=picks,
        full_report=report.full_analysis or "",
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a research report."""
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == current_user.id
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.delete(report)
    await db.commit()


@router.get("/strategies")
async def list_strategies():
    """List available trading strategies."""
    from app.services.backtest import BacktestService

    return {
        "strategies": [
            {"id": k, "name": k.replace("_", " ").title(), "description": v}
            for k, v in BacktestService.STRATEGIES.items()
        ]
    }
