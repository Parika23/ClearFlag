"""Human-readable threshold insights built from calculated analytics only."""
from __future__ import annotations


class ClearFlagInsightsService:
    def __init__(self, analytics): self.analytics = analytics
    def cards(self):
        if not self.analytics.has_data: return []
        total = self.analytics.total_cases; risks = self.analytics.risk_level_counts; reviews = self.analytics.review_status_counts
        cards = []
        if risks["high"] / total >= 0.30:
            cards.append({"category":"risk","icon":"🚨","title":"High alert volume","message":f"{risks['high']} of {total} cases are high risk.","status":"warning"})
        signals = self.analytics.signal_frequency()
        if not signals.empty:
            cards.append({"category":"pattern","icon":"🔎","title":"Most common signal","message":f"{signals.index[0]} appears in {signals.iloc[0]} case(s).","status":"info"})
        if reviews["pending"] / total >= 0.50:
            cards.append({"category":"oversight","icon":"👤","title":"Review backlog","message":f"{reviews['pending']} case(s) are awaiting human review.","status":"warning"})
        return cards


class ClearFlagTrendService:
    """Session-like accuracy trends; streak resets whenever a trainee misses."""
    def __init__(self, attempts): self.attempts = attempts
    def summary(self):
        if self.attempts.empty: return None
        results = [bool(x) for x in self.attempts["matched"]]
        current = best = 0
        for matched in results:
            current = current + 1 if matched else 0; best = max(best, current)
        midpoint = len(results) // 2
        if midpoint < 1: direction = "Stable"
        else:
            earlier = sum(results[:midpoint]) / midpoint; recent = sum(results[midpoint:]) / len(results[midpoint:])
            direction = "Improving" if recent > earlier + .05 else "Declining" if recent < earlier - .05 else "Stable"
        return {"accuracy":round(sum(results) / len(results) * 100, 1), "current_streak":current, "best_streak":best, "trend":direction, "attempts":len(results)}
