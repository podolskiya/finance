# ml/sentiment.py
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import streamlit as st

# ── Model loader (cached so it only loads once) ──
@st.cache_resource(show_spinner="Loading FinBERT model...")
def load_finbert():
    """
    Load FinBERT from HuggingFace.
    ProsusAI/finbert is fine-tuned on financial news
    for positive / negative / neutral classification.
    """
    from transformers import pipeline
    print("[FINBERT] Loading model (first run ~30s)...")
    return pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        tokenizer="ProsusAI/finbert",
        top_k=None,               # return all 3 class scores
        truncation=True,
        max_length=512
    )


def fetch_news(ticker: str, max_items: int = 100) -> pd.DataFrame:
    """
    Fetch recent news for a ticker via yfinance.
    Returns DataFrame with title, summary, date, url.
    """
    stock = yf.Ticker(ticker)
    news  = stock.news

    if not news:
        return pd.DataFrame()

    rows = []
    for item in news[:max_items]:
        try:
            content = item.get('content', {})
            title   = content.get('title', '')
            summary = content.get('summary', '')
            pub_ts  = content.get('pubDate', '')

            # Parse date
            if pub_ts:
                try:
                    date = pd.to_datetime(pub_ts).tz_localize(None)
                except:
                    date = pd.to_datetime('today')
            else:
                date = pd.to_datetime('today')

            if title:
                rows.append({
                    'date':      date,
                    'title':     title,
                    'summary':   summary or title,
                    'url':       content.get('canonicalUrl', {}).get('url', ''),
                    'publisher': content.get('provider', {}).get('displayName', 'Unknown')
                })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date', ascending=False).reset_index(drop=True)
    return df


def score_sentiment(texts: list, pipe) -> list:
    """
    Run FinBERT on a list of texts.
    Returns list of dicts with positive/negative/neutral scores
    and a compound score in [-1, +1].
    """
    results = []
    for text in texts:
        if not text or len(text.strip()) < 5:
            results.append({
                'positive': 0.33, 'negative': 0.33,
                'neutral':  0.34, 'compound': 0.0,
                'label':    'neutral'
            })
            continue
        try:
            out    = pipe(text[:512])[0]
            scores = {item['label'].lower(): item['score'] for item in out}
            pos    = scores.get('positive', 0)
            neg    = scores.get('negative', 0)
            neu    = scores.get('neutral',  0)
            # Compound: scaled from -1 to +1
            compound = pos - neg
            label    = max(scores, key=scores.get)
            results.append({
                'positive': round(pos, 4),
                'negative': round(neg, 4),
                'neutral':  round(neu, 4),
                'compound': round(compound, 4),
                'label':    label
            })
        except Exception:
            results.append({
                'positive': 0.33, 'negative': 0.33,
                'neutral':  0.34, 'compound': 0.0,
                'label':    'neutral'
            })
    return results


def analyse_news(ticker: str, max_items: int = 100) -> pd.DataFrame:
    """
    Fetch news and run FinBERT scoring.
    Returns enriched DataFrame with sentiment columns.
    """
    pipe = load_finbert()
    news = fetch_news(ticker, max_items)

    if news.empty:
        return pd.DataFrame()

    # Score on title + summary combined for richer signal
    texts    = (news['title'] + '. ' + news['summary']).tolist()
    scores   = score_sentiment(texts, pipe)
    score_df = pd.DataFrame(scores)

    return pd.concat([news.reset_index(drop=True),
                      score_df.reset_index(drop=True)], axis=1)


def daily_sentiment(scored_news: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate article-level scores to daily sentiment.
    Uses exponential weighting — more recent articles
    within a day get higher weight.
    """
    if scored_news.empty:
        return pd.DataFrame()

    df = scored_news.copy()
    df['date_only'] = df['date'].dt.normalize()

    daily = df.groupby('date_only').agg(
        compound_mean = ('compound', 'mean'),
        compound_std  = ('compound', 'std'),
        positive_mean = ('positive', 'mean'),
        negative_mean = ('negative', 'mean'),
        neutral_mean  = ('neutral',  'mean'),
        n_articles    = ('compound', 'count'),
        bullish       = ('label',    lambda x: (x=='positive').sum()),
        bearish       = ('label',    lambda x: (x=='negative').sum()),
    ).reset_index()

    daily.columns.name = None
    daily = daily.rename(columns={'date_only': 'date'})
    daily = daily.sort_values('date')

    # Rolling smoothed compound (3-day EMA)
    daily['compound_smooth'] = (
        daily['compound_mean']
        .ewm(span=3, adjust=False)
        .mean()
    )
    return daily


def sentiment_signals(daily: pd.DataFrame,
                      price_data: pd.DataFrame,
                      bull_threshold:  float = 0.15,
                      bear_threshold:  float = -0.15,
                      min_articles:    int   = 1) -> pd.Series:
    """
    Generate trading signals from daily sentiment.

    Long  (+1) : smoothed compound > bull_threshold
    Short (-1) : smoothed compound < bear_threshold
    Flat  ( 0) : neutral zone or insufficient articles
    """
    close = price_data['Close'].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    signals = pd.Series(0.0, index=close.index)

    for _, row in daily.iterrows():
        date    = row['date']
        score   = row['compound_smooth']
        n_arts  = row['n_articles']

        if n_arts < min_articles:
            continue

        # Find matching trading days
        mask = (signals.index.normalize() == date)
        if not mask.any():
            # Use next available trading day
            future = signals.index[signals.index.normalize() >= date]
            if len(future) > 0:
                mask = signals.index == future[0]

        if score > bull_threshold:
            signals[mask] = 1.0
        elif score < bear_threshold:
            signals[mask] = -1.0

    # Forward-fill signals for days without news
    signals = signals.replace(0, np.nan).ffill().fillna(0)
    return signals


def combined_signals(sentiment_sig: pd.Series,
                     price_sig:     pd.Series,
                     sent_weight:   float = 0.4) -> pd.Series:
    """
    Blend sentiment signals with price-based signals.
    sentiment_weight: 0=pure price, 1=pure sentiment
    """
    price_weight = 1 - sent_weight
    raw = (sentiment_sig * sent_weight +
           price_sig.reindex(sentiment_sig.index).fillna(0) * price_weight)
    combined = raw.apply(
        lambda x: 1 if x > 0.3 else (-1 if x < -0.3 else 0)
    )
    return combined