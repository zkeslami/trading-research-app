"""LangGraph-based agent router for orchestrating research agents."""
import json
from typing import TypedDict, Annotated, Sequence, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


class ResearchState(TypedDict):
    """State shared across all agents in the research pipeline."""
    # Input parameters
    asset_classes: list[str]
    budget: float
    risk_preference: str  # conservative, moderate, aggressive
    specific_tickers: Optional[list[str]]

    # Data collected during research
    universe: list[str]  # Filtered tradable tickers
    price_data: dict  # ticker -> price info
    fundamental_data: dict  # ticker -> fundamental analysis
    technical_data: dict  # ticker -> technical analysis
    sentiment_data: dict  # ticker -> sentiment analysis

    # Agent outputs
    fundamental_analysis: dict
    technical_analysis: dict
    sentiment_analysis: dict
    risk_assessment: dict

    # Final outputs
    ranked_picks: list[dict]
    allocations: dict
    full_report: str
    messages: Sequence[BaseMessage]


class AgentRouter:
    """Orchestrates the research pipeline using LangGraph."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        """Initialize the agent router."""
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        workflow = StateGraph(ResearchState)

        # Add nodes for each agent
        workflow.add_node("filter_universe", self._filter_universe)
        workflow.add_node("gather_data", self._gather_data)
        workflow.add_node("fundamental_analyst", self._fundamental_analysis)
        workflow.add_node("technical_analyst", self._technical_analysis)
        workflow.add_node("sentiment_analyst", self._sentiment_analysis)
        workflow.add_node("risk_manager", self._risk_assessment)
        workflow.add_node("portfolio_optimizer", self._optimize_portfolio)
        workflow.add_node("report_generator", self._generate_report)

        # Define edges (workflow order)
        workflow.set_entry_point("filter_universe")
        workflow.add_edge("filter_universe", "gather_data")
        workflow.add_edge("gather_data", "fundamental_analyst")
        workflow.add_edge("fundamental_analyst", "technical_analyst")
        workflow.add_edge("technical_analyst", "sentiment_analyst")
        workflow.add_edge("sentiment_analyst", "risk_manager")
        workflow.add_edge("risk_manager", "portfolio_optimizer")
        workflow.add_edge("portfolio_optimizer", "report_generator")
        workflow.add_edge("report_generator", END)

        return workflow.compile()

    async def _filter_universe(self, state: ResearchState) -> dict:
        """Filter universe to Robinhood-tradable assets."""
        from app.services.data_pipeline import data_pipeline

        # Get tradable universe based on asset classes
        universe = await data_pipeline.get_robinhood_universe(state["asset_classes"])

        # If specific tickers provided, filter to those
        if state.get("specific_tickers"):
            universe = [t for t in state["specific_tickers"] if t in universe]

        return {"universe": universe[:50]}  # Limit to 50 for performance

    async def _gather_data(self, state: ResearchState) -> dict:
        """Gather price and market data for universe."""
        from app.services.data_pipeline import data_pipeline

        # Get current prices
        price_data = await data_pipeline.get_multiple_prices(state["universe"])

        # Filter out tickers with no data
        valid_tickers = [t for t, p in price_data.items() if p is not None]
        price_data = {t: p.model_dump() if p else None for t, p in price_data.items()}

        return {
            "universe": valid_tickers,
            "price_data": price_data,
        }

    async def _fundamental_analysis(self, state: ResearchState) -> dict:
        """Perform fundamental analysis on universe."""
        analysis = {}

        for ticker in state["universe"]:
            price_info = state["price_data"].get(ticker)
            if not price_info:
                continue

            # Extract fundamental metrics
            pe_ratio = price_info.get("pe_ratio")
            market_cap = price_info.get("market_cap")
            dividend_yield = price_info.get("dividend_yield")

            # Score based on fundamentals
            score = 50  # Base score

            # P/E ratio scoring
            if pe_ratio:
                if pe_ratio < 15:
                    score += 15  # Undervalued
                elif pe_ratio < 25:
                    score += 10  # Fair value
                elif pe_ratio > 50:
                    score -= 10  # Overvalued

            # Market cap stability
            if market_cap:
                if market_cap > 100_000_000_000:  # $100B+
                    score += 10  # Large cap stability
                elif market_cap > 10_000_000_000:  # $10B+
                    score += 5

            # Dividend yield
            if dividend_yield and dividend_yield > 0.02:
                score += 5

            analysis[ticker] = {
                "score": min(100, max(0, score)),
                "pe_ratio": pe_ratio,
                "market_cap": market_cap,
                "dividend_yield": dividend_yield,
                "rationale": self._generate_fundamental_rationale(
                    ticker, pe_ratio, market_cap, dividend_yield, score
                )
            }

        return {"fundamental_analysis": analysis}

    def _generate_fundamental_rationale(
        self,
        ticker: str,
        pe_ratio: Optional[float],
        market_cap: Optional[float],
        dividend_yield: Optional[float],
        score: int
    ) -> str:
        """Generate rationale for fundamental analysis."""
        parts = []

        if pe_ratio:
            if pe_ratio < 15:
                parts.append(f"P/E of {pe_ratio:.1f} suggests undervaluation")
            elif pe_ratio > 50:
                parts.append(f"High P/E of {pe_ratio:.1f} indicates growth expectations")
            else:
                parts.append(f"P/E of {pe_ratio:.1f} is within normal range")

        if market_cap:
            if market_cap > 100_000_000_000:
                parts.append("large-cap stability")
            elif market_cap > 10_000_000_000:
                parts.append("mid-cap growth potential")
            else:
                parts.append("small-cap with higher risk/reward")

        if dividend_yield and dividend_yield > 0:
            parts.append(f"{dividend_yield*100:.1f}% dividend yield")

        return f"{ticker}: " + ("; ".join(parts) if parts else "Limited fundamental data available")

    async def _technical_analysis(self, state: ResearchState) -> dict:
        """Perform technical analysis on universe."""
        from app.services.data_pipeline import data_pipeline
        from app.strategies.quant import quant_strategies
        import pandas as pd

        analysis = {}

        for ticker in state["universe"]:
            try:
                # Get historical data
                hist_data = await data_pipeline.get_historical_data(ticker, period="1y")
                if not hist_data:
                    continue

                # Convert to pandas Series
                prices = pd.Series(hist_data.close, index=pd.to_datetime(hist_data.dates))

                # Get signals from multiple strategies
                signals = []
                signals.append(quant_strategies.sma_crossover_signal(prices))
                signals.append(quant_strategies.macd_signal(prices))
                signals.append(quant_strategies.rsi_signal(prices))
                signals.append(quant_strategies.bollinger_bands_signal(prices))
                signals.append(quant_strategies.momentum_signal(prices))

                # Aggregate signals
                consensus = quant_strategies.aggregate_signals(signals)

                # Calculate return metrics
                returns = data_pipeline.calculate_returns(hist_data.close)

                analysis[ticker] = {
                    "signal": consensus.action,
                    "strength": consensus.strength,
                    "score": int(consensus.strength * 100) if consensus.action == "buy" else int((1 - consensus.strength) * 50),
                    "indicators": consensus.indicators,
                    "rationale": consensus.reason,
                    "historical_return": returns.get("total_return", 0),
                    "volatility": returns.get("volatility", 0),
                    "sharpe_ratio": returns.get("sharpe_ratio", 0),
                }
            except Exception as e:
                analysis[ticker] = {
                    "signal": "hold",
                    "strength": 0.5,
                    "score": 50,
                    "rationale": f"Technical analysis unavailable: {str(e)}",
                }

        return {"technical_analysis": analysis}

    async def _sentiment_analysis(self, state: ResearchState) -> dict:
        """Perform sentiment analysis (simplified without Reddit MCP)."""
        analysis = {}

        for ticker in state["universe"]:
            # Simplified sentiment based on price momentum
            price_info = state["price_data"].get(ticker)
            tech_analysis = state.get("technical_analysis", {}).get(ticker, {})

            if price_info:
                current = price_info.get("current_price", 0)
                high_52w = price_info.get("fifty_two_week_high", current)
                low_52w = price_info.get("fifty_two_week_low", current)

                # Position in 52-week range
                if high_52w and low_52w and high_52w != low_52w:
                    position = (current - low_52w) / (high_52w - low_52w)
                else:
                    position = 0.5

                # Sentiment scoring
                if position > 0.8:
                    sentiment = "bullish"
                    score = 70
                    rationale = f"{ticker} trading near 52-week highs, indicating strong market sentiment"
                elif position < 0.2:
                    sentiment = "bearish"
                    score = 30
                    rationale = f"{ticker} trading near 52-week lows, may indicate value opportunity or continued weakness"
                else:
                    sentiment = "neutral"
                    score = 50
                    rationale = f"{ticker} trading mid-range, sentiment neutral"

                analysis[ticker] = {
                    "sentiment": sentiment,
                    "score": score,
                    "52w_position": position,
                    "rationale": rationale,
                }
            else:
                analysis[ticker] = {
                    "sentiment": "neutral",
                    "score": 50,
                    "rationale": "Insufficient data for sentiment analysis",
                }

        return {"sentiment_analysis": analysis}

    async def _risk_assessment(self, state: ResearchState) -> dict:
        """Assess risk for each ticker and overall portfolio."""
        risk_preference = state.get("risk_preference", "moderate")

        # Risk tolerance thresholds
        risk_thresholds = {
            "conservative": {"max_volatility": 0.2, "min_sharpe": 0.5},
            "moderate": {"max_volatility": 0.4, "min_sharpe": 0.3},
            "aggressive": {"max_volatility": 0.8, "min_sharpe": 0.0},
        }

        thresholds = risk_thresholds.get(risk_preference, risk_thresholds["moderate"])

        assessment = {}
        for ticker in state["universe"]:
            tech = state.get("technical_analysis", {}).get(ticker, {})

            volatility = tech.get("volatility", 0.3)
            sharpe = tech.get("sharpe_ratio", 0)

            # Risk level based on volatility
            if volatility < 0.15:
                risk_level = "low"
            elif volatility < 0.3:
                risk_level = "medium"
            else:
                risk_level = "high"

            # Check if within risk tolerance
            within_tolerance = (
                volatility <= thresholds["max_volatility"] and
                sharpe >= thresholds["min_sharpe"]
            )

            assessment[ticker] = {
                "risk_level": risk_level,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "within_tolerance": within_tolerance,
                "rationale": f"{ticker}: {risk_level} risk (vol: {volatility:.1%}, Sharpe: {sharpe:.2f})"
            }

        return {"risk_assessment": assessment}

    async def _optimize_portfolio(self, state: ResearchState) -> dict:
        """Optimize portfolio allocation and rank picks."""
        budget = state.get("budget", 500)
        risk_preference = state.get("risk_preference", "moderate")

        # Combine scores from all analyses
        combined_scores = {}
        for ticker in state["universe"]:
            fundamental = state.get("fundamental_analysis", {}).get(ticker, {})
            technical = state.get("technical_analysis", {}).get(ticker, {})
            sentiment = state.get("sentiment_analysis", {}).get(ticker, {})
            risk = state.get("risk_assessment", {}).get(ticker, {})

            # Weight scores based on risk preference
            if risk_preference == "conservative":
                weights = {"fundamental": 0.4, "technical": 0.2, "sentiment": 0.1, "risk": 0.3}
            elif risk_preference == "aggressive":
                weights = {"fundamental": 0.2, "technical": 0.4, "sentiment": 0.2, "risk": 0.2}
            else:  # moderate
                weights = {"fundamental": 0.3, "technical": 0.3, "sentiment": 0.15, "risk": 0.25}

            # Calculate weighted score
            f_score = fundamental.get("score", 50)
            t_score = technical.get("score", 50)
            s_score = sentiment.get("score", 50)
            r_score = 100 if risk.get("within_tolerance", True) else 30

            combined = (
                f_score * weights["fundamental"] +
                t_score * weights["technical"] +
                s_score * weights["sentiment"] +
                r_score * weights["risk"]
            )

            combined_scores[ticker] = {
                "combined_score": combined,
                "fundamental_score": f_score,
                "technical_score": t_score,
                "sentiment_score": s_score,
                "risk_score": r_score,
            }

        # Rank and select top 10
        ranked = sorted(
            combined_scores.items(),
            key=lambda x: x[1]["combined_score"],
            reverse=True
        )[:10]

        # Calculate allocations (score-weighted)
        total_score = sum(item[1]["combined_score"] for item in ranked)
        allocations = {}

        ranked_picks = []
        for ticker, scores in ranked:
            allocation_pct = (scores["combined_score"] / total_score * 100) if total_score > 0 else 10
            allocation_amt = budget * (allocation_pct / 100)

            price_info = state["price_data"].get(ticker, {})
            current_price = price_info.get("current_price", 0) if price_info else 0
            tech = state.get("technical_analysis", {}).get(ticker, {})
            risk = state.get("risk_assessment", {}).get(ticker, {})

            # Estimate 1-year yield based on historical return and momentum
            hist_return = tech.get("historical_return", 0)
            signal_strength = tech.get("strength", 0.5)

            # Adjust expected return based on signal
            if tech.get("signal") == "buy":
                expected_yield = hist_return * (1 + signal_strength * 0.5)
            elif tech.get("signal") == "sell":
                expected_yield = hist_return * 0.5
            else:
                expected_yield = hist_return * 0.8

            # Cap expectations
            expected_yield = max(-0.5, min(1.0, expected_yield))

            allocations[ticker] = allocation_pct

            ranked_picks.append({
                "rank": len(ranked_picks) + 1,
                "ticker": ticker,
                "current_price": current_price,
                "expected_1y_yield": expected_yield,
                "confidence": scores["combined_score"] / 100,
                "risk_level": risk.get("risk_level", "medium"),
                "allocation_percent": allocation_pct,
                "allocation_amount": allocation_amt,
                "scores": scores,
                "rationale": self._build_rationale(ticker, state),
            })

        return {
            "ranked_picks": ranked_picks,
            "allocations": allocations,
        }

    def _build_rationale(self, ticker: str, state: ResearchState) -> str:
        """Build combined rationale for a ticker."""
        parts = []

        fundamental = state.get("fundamental_analysis", {}).get(ticker, {})
        if fundamental.get("rationale"):
            parts.append(f"Fundamental: {fundamental['rationale']}")

        technical = state.get("technical_analysis", {}).get(ticker, {})
        if technical.get("rationale"):
            parts.append(f"Technical: {technical['rationale']}")

        sentiment = state.get("sentiment_analysis", {}).get(ticker, {})
        if sentiment.get("rationale"):
            parts.append(f"Sentiment: {sentiment['rationale']}")

        risk = state.get("risk_assessment", {}).get(ticker, {})
        if risk.get("rationale"):
            parts.append(f"Risk: {risk['rationale']}")

        return " | ".join(parts)

    async def _generate_report(self, state: ResearchState) -> dict:
        """Generate the final research report."""
        report_lines = [
            "# Investment Research Report",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Summary",
            f"- **Budget**: ${state.get('budget', 500):,.2f}",
            f"- **Risk Profile**: {state.get('risk_preference', 'moderate').title()}",
            f"- **Asset Classes**: {', '.join(state.get('asset_classes', []))}",
            f"- **Universe Screened**: {len(state.get('universe', []))} assets",
            "",
            "## Top 10 Investment Picks",
            "",
        ]

        for pick in state.get("ranked_picks", []):
            report_lines.extend([
                f"### {pick['rank']}. {pick['ticker']}",
                f"- **Current Price**: ${pick['current_price']:,.2f}",
                f"- **Expected 1Y Yield**: {pick['expected_1y_yield']:.1%}",
                f"- **Confidence Score**: {pick['confidence']:.0%}",
                f"- **Risk Level**: {pick['risk_level'].title()}",
                f"- **Recommended Allocation**: {pick['allocation_percent']:.1f}% (${pick['allocation_amount']:,.2f})",
                f"- **Rationale**: {pick['rationale']}",
                "",
            ])

        report_lines.extend([
            "## Disclaimer",
            "This report is for informational purposes only and does not constitute financial advice. ",
            "All investments carry risk. Past performance does not guarantee future results. ",
            "Please conduct your own research and consult with a financial advisor before making investment decisions.",
            "",
            "---",
            "*Report generated by Trading Research App*",
        ])

        return {"full_report": "\n".join(report_lines)}

    async def run_research(
        self,
        asset_classes: list[str],
        budget: float = 500.0,
        risk_preference: str = "moderate",
        specific_tickers: Optional[list[str]] = None,
    ) -> ResearchState:
        """Run the full research pipeline."""
        initial_state: ResearchState = {
            "asset_classes": asset_classes,
            "budget": budget,
            "risk_preference": risk_preference,
            "specific_tickers": specific_tickers,
            "universe": [],
            "price_data": {},
            "fundamental_data": {},
            "technical_data": {},
            "sentiment_data": {},
            "fundamental_analysis": {},
            "technical_analysis": {},
            "sentiment_analysis": {},
            "risk_assessment": {},
            "ranked_picks": [],
            "allocations": {},
            "full_report": "",
            "messages": [],
        }

        # Run the graph
        result = await self.graph.ainvoke(initial_state)
        return result


# Factory function
def create_agent_router(llm_provider: str = "openai", api_key: Optional[str] = None) -> AgentRouter:
    """Create an agent router instance."""
    return AgentRouter(llm_provider=llm_provider, api_key=api_key)
