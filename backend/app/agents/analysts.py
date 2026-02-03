"""Individual analyst agents for the research pipeline."""
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class AnalystType(Enum):
    """Types of analyst agents."""
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    RISK = "risk"


@dataclass
class AnalystOutput:
    """Output from an analyst agent."""
    ticker: str
    analyst_type: AnalystType
    score: float  # 0-100
    signal: str  # buy, sell, hold
    confidence: float  # 0-1
    rationale: str
    metrics: dict


class FundamentalAnalyst:
    """Analyst focused on fundamental metrics."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key

    def analyze(self, ticker: str, data: dict) -> AnalystOutput:
        """Analyze fundamental metrics for a ticker."""
        pe_ratio = data.get("pe_ratio")
        market_cap = data.get("market_cap")
        dividend_yield = data.get("dividend_yield")
        current_price = data.get("current_price", 0)

        score = 50
        reasons = []

        # P/E Analysis
        if pe_ratio:
            if pe_ratio < 0:
                score -= 10
                reasons.append("Negative earnings")
            elif pe_ratio < 15:
                score += 20
                reasons.append(f"Low P/E ({pe_ratio:.1f}) suggests undervaluation")
            elif pe_ratio < 25:
                score += 10
                reasons.append(f"Reasonable P/E ({pe_ratio:.1f})")
            elif pe_ratio < 40:
                score += 0
                reasons.append(f"Elevated P/E ({pe_ratio:.1f}) pricing in growth")
            else:
                score -= 10
                reasons.append(f"High P/E ({pe_ratio:.1f}) may indicate overvaluation")
        else:
            reasons.append("P/E ratio unavailable")

        # Market Cap Analysis
        if market_cap:
            if market_cap > 200_000_000_000:  # $200B+
                score += 10
                reasons.append("Mega-cap with stability")
            elif market_cap > 50_000_000_000:  # $50B+
                score += 8
                reasons.append("Large-cap company")
            elif market_cap > 10_000_000_000:  # $10B+
                score += 5
                reasons.append("Mid-cap with growth potential")
            elif market_cap > 2_000_000_000:  # $2B+
                score += 2
                reasons.append("Small-cap with higher risk/reward")
            else:
                score -= 5
                reasons.append("Micro-cap with elevated risk")

        # Dividend Analysis
        if dividend_yield:
            if dividend_yield > 0.05:
                score += 10
                reasons.append(f"Strong dividend yield ({dividend_yield*100:.1f}%)")
            elif dividend_yield > 0.02:
                score += 5
                reasons.append(f"Moderate dividend ({dividend_yield*100:.1f}%)")
            elif dividend_yield > 0:
                score += 2
                reasons.append(f"Small dividend ({dividend_yield*100:.2f}%)")

        # Determine signal
        if score >= 70:
            signal = "buy"
            confidence = min(1.0, (score - 50) / 50)
        elif score <= 30:
            signal = "sell"
            confidence = min(1.0, (50 - score) / 50)
        else:
            signal = "hold"
            confidence = 0.5

        return AnalystOutput(
            ticker=ticker,
            analyst_type=AnalystType.FUNDAMENTAL,
            score=min(100, max(0, score)),
            signal=signal,
            confidence=confidence,
            rationale=" | ".join(reasons),
            metrics={
                "pe_ratio": pe_ratio,
                "market_cap": market_cap,
                "dividend_yield": dividend_yield,
            }
        )


class TechnicalAnalyst:
    """Analyst focused on technical indicators."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key

    def analyze(self, ticker: str, signal_data: dict) -> AnalystOutput:
        """Analyze technical indicators for a ticker."""
        signal = signal_data.get("signal", "hold")
        strength = signal_data.get("strength", 0.5)
        indicators = signal_data.get("indicators", {})
        hist_return = signal_data.get("historical_return", 0)
        volatility = signal_data.get("volatility", 0.3)
        sharpe = signal_data.get("sharpe_ratio", 0)

        reasons = []

        # Signal analysis
        if signal == "buy":
            score = 60 + strength * 30
            reasons.append(f"Technical buy signal (strength: {strength:.0%})")
        elif signal == "sell":
            score = 40 - strength * 30
            reasons.append(f"Technical sell signal (strength: {strength:.0%})")
        else:
            score = 50
            reasons.append("Technical indicators neutral")

        # Historical return adjustment
        if hist_return > 0.2:
            score += 10
            reasons.append(f"Strong 1Y return ({hist_return:.1%})")
        elif hist_return > 0:
            score += 5
            reasons.append(f"Positive 1Y return ({hist_return:.1%})")
        elif hist_return < -0.2:
            score -= 10
            reasons.append(f"Poor 1Y return ({hist_return:.1%})")
        else:
            score -= 5
            reasons.append(f"Negative 1Y return ({hist_return:.1%})")

        # Volatility consideration
        if volatility < 0.2:
            score += 5
            reasons.append(f"Low volatility ({volatility:.1%})")
        elif volatility > 0.5:
            score -= 5
            reasons.append(f"High volatility ({volatility:.1%})")

        # Sharpe ratio
        if sharpe > 1:
            score += 10
            reasons.append(f"Excellent risk-adjusted returns (Sharpe: {sharpe:.2f})")
        elif sharpe > 0.5:
            score += 5
            reasons.append(f"Good risk-adjusted returns (Sharpe: {sharpe:.2f})")
        elif sharpe < 0:
            score -= 5
            reasons.append(f"Negative risk-adjusted returns (Sharpe: {sharpe:.2f})")

        confidence = min(1.0, abs(score - 50) / 50 + 0.3)

        return AnalystOutput(
            ticker=ticker,
            analyst_type=AnalystType.TECHNICAL,
            score=min(100, max(0, score)),
            signal=signal,
            confidence=confidence,
            rationale=" | ".join(reasons),
            metrics={
                "signal": signal,
                "strength": strength,
                "historical_return": hist_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                **indicators,
            }
        )


class SentimentAnalyst:
    """Analyst focused on market sentiment."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key

    def analyze(self, ticker: str, sentiment_data: dict) -> AnalystOutput:
        """Analyze sentiment for a ticker."""
        sentiment = sentiment_data.get("sentiment", "neutral")
        position_52w = sentiment_data.get("52w_position", 0.5)

        reasons = []

        # Base score from sentiment
        if sentiment == "bullish":
            score = 70
            reasons.append("Bullish market sentiment")
        elif sentiment == "bearish":
            score = 30
            reasons.append("Bearish market sentiment")
        else:
            score = 50
            reasons.append("Neutral market sentiment")

        # 52-week position analysis
        if position_52w > 0.9:
            score += 5
            reasons.append("Trading at 52-week highs (momentum)")
        elif position_52w > 0.7:
            score += 10
            reasons.append("Strong position in 52-week range")
        elif position_52w < 0.1:
            score -= 5
            reasons.append("Trading at 52-week lows (potential value or distress)")
        elif position_52w < 0.3:
            score += 5
            reasons.append("Potential value opportunity near 52-week lows")

        # Determine signal
        if score >= 65:
            signal = "buy"
        elif score <= 35:
            signal = "sell"
        else:
            signal = "hold"

        confidence = min(1.0, abs(score - 50) / 50 + 0.2)

        return AnalystOutput(
            ticker=ticker,
            analyst_type=AnalystType.SENTIMENT,
            score=min(100, max(0, score)),
            signal=signal,
            confidence=confidence,
            rationale=" | ".join(reasons),
            metrics={
                "sentiment": sentiment,
                "52w_position": position_52w,
            }
        )


class RiskAnalyst:
    """Analyst focused on risk assessment."""

    def __init__(self, llm_provider: str = "openai", api_key: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key

    def analyze(
        self,
        ticker: str,
        risk_data: dict,
        risk_preference: str = "moderate"
    ) -> AnalystOutput:
        """Analyze risk for a ticker."""
        risk_level = risk_data.get("risk_level", "medium")
        volatility = risk_data.get("volatility", 0.3)
        sharpe = risk_data.get("sharpe_ratio", 0)
        within_tolerance = risk_data.get("within_tolerance", True)

        reasons = []

        # Base score from risk level alignment
        if risk_preference == "conservative":
            if risk_level == "low":
                score = 80
                reasons.append("Low risk aligns with conservative profile")
            elif risk_level == "medium":
                score = 50
                reasons.append("Medium risk is moderate for conservative investors")
            else:
                score = 20
                reasons.append("High risk does not align with conservative profile")
        elif risk_preference == "aggressive":
            if risk_level == "high":
                score = 70
                reasons.append("High risk acceptable for aggressive profile")
            elif risk_level == "medium":
                score = 60
                reasons.append("Medium risk provides growth with some stability")
            else:
                score = 50
                reasons.append("Low risk may limit return potential")
        else:  # moderate
            if risk_level == "medium":
                score = 70
                reasons.append("Medium risk aligns with moderate profile")
            elif risk_level == "low":
                score = 60
                reasons.append("Low risk provides stability")
            else:
                score = 40
                reasons.append("High risk may not align with moderate profile")

        # Tolerance adjustment
        if not within_tolerance:
            score -= 20
            reasons.append("Risk metrics outside tolerance thresholds")

        # Signal based on risk-adjusted suitability
        if score >= 60:
            signal = "buy"
        elif score <= 40:
            signal = "sell"
        else:
            signal = "hold"

        confidence = min(1.0, abs(score - 50) / 50 + 0.3)

        return AnalystOutput(
            ticker=ticker,
            analyst_type=AnalystType.RISK,
            score=min(100, max(0, score)),
            signal=signal,
            confidence=confidence,
            rationale=" | ".join(reasons),
            metrics={
                "risk_level": risk_level,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "within_tolerance": within_tolerance,
            }
        )


# Factory functions
def create_fundamental_analyst(llm_provider: str = "openai", api_key: Optional[str] = None) -> FundamentalAnalyst:
    return FundamentalAnalyst(llm_provider, api_key)


def create_technical_analyst(llm_provider: str = "openai", api_key: Optional[str] = None) -> TechnicalAnalyst:
    return TechnicalAnalyst(llm_provider, api_key)


def create_sentiment_analyst(llm_provider: str = "openai", api_key: Optional[str] = None) -> SentimentAnalyst:
    return SentimentAnalyst(llm_provider, api_key)


def create_risk_analyst(llm_provider: str = "openai", api_key: Optional[str] = None) -> RiskAnalyst:
    return RiskAnalyst(llm_provider, api_key)
