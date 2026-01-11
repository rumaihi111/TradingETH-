"""
Technical Indicators Module
Provides RSI and other indicators for trading decisions
"""

from typing import List, Dict, Any
import pandas as pd


def calculate_rsi(candles: List[Dict[str, Any]], period: int = 7) -> float:
    """
    Calculate RSI (Relative Strength Index) for given candles.
    
    Args:
        candles: List of OHLCV dictionaries with 'close' prices
        period: RSI period (default 7)
        
    Returns:
        Current RSI value (0-100)
    """
    if len(candles) < period + 1:
        return 50.0  # Neutral if not enough data
    
    # Extract closing prices
    closes = [float(c['close']) for c in candles]
    
    # Calculate price changes
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    
    # Separate gains and losses
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # Calculate initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Calculate RSI using smoothed averages
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    # Avoid division by zero
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return sum(prices) / len(prices)
    
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema


def calculate_sma(prices: List[float], period: int) -> float:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return sum(prices) / len(prices)
    
    return sum(prices[-period:]) / period


def calculate_atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) for volatility measurement.
    
    Args:
        candles: List of OHLCV dictionaries
        period: ATR period (default 14)
        
    Returns:
        Current ATR value
    """
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)
    
    # Calculate ATR as simple moving average of true ranges
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 4)


def get_support_resistance_levels(candles: List[Dict[str, Any]], num_levels: int = 3) -> Dict[str, List[float]]:
    """
    Identify support and resistance levels from price action.
    
    Args:
        candles: List of OHLCV dictionaries
        num_levels: Number of support/resistance levels to identify
        
    Returns:
        Dictionary with 'support' and 'resistance' level lists
    """
    if len(candles) < 20:
        return {'support': [], 'resistance': []}
    
    # Extract highs and lows
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    
    # Find swing highs (resistance)
    resistance_levels = []
    for i in range(2, len(candles) - 2):
        if (candles[i]['high'] > candles[i-1]['high'] and 
            candles[i]['high'] > candles[i-2]['high'] and
            candles[i]['high'] > candles[i+1]['high'] and
            candles[i]['high'] > candles[i+2]['high']):
            resistance_levels.append(candles[i]['high'])
    
    # Find swing lows (support)
    support_levels = []
    for i in range(2, len(candles) - 2):
        if (candles[i]['low'] < candles[i-1]['low'] and 
            candles[i]['low'] < candles[i-2]['low'] and
            candles[i]['low'] < candles[i+1]['low'] and
            candles[i]['low'] < candles[i+2]['low']):
            support_levels.append(candles[i]['low'])
    
    # Sort and take most recent/relevant levels
    resistance_levels = sorted(set(resistance_levels), reverse=True)[:num_levels]
    support_levels = sorted(set(support_levels), reverse=True)[:num_levels]
    
    return {
        'support': support_levels,
        'resistance': resistance_levels
    }
