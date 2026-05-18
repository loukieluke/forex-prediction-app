POSITIVE_WORDS = {
    "rally",
    "bullish",
    "growth",
    "gain",
    "surge",
    "strong",
    "optimistic",
    "upside",
}
NEGATIVE_WORDS = {
    "crash",
    "bearish",
    "drop",
    "recession",
    "loss",
    "weak",
    "inflation",
    "downside",
    "war",
}


def keyword_sentiment_score(text: str) -> float:
    words = set(text.lower().split())
    pos_hits = len(words.intersection(POSITIVE_WORDS))
    neg_hits = len(words.intersection(NEGATIVE_WORDS))
    total = pos_hits + neg_hits
    if total == 0:
        return 0.0
    return (pos_hits - neg_hits) / total


def score_headlines(headlines: list[str]) -> float:
    if not headlines:
        return 0.0
    scores = [keyword_sentiment_score(item) for item in headlines]
    return sum(scores) / len(scores)
