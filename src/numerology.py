"""
Zorak Corp Numerology Module - Life Path Calculator

Used to determine if trading is allowed on a given day.
Days with Life Path number 3 are blocked from trading.
"""

from datetime import datetime, date
from typing import Union


def reduce_to_single_digit(n: int) -> int:
    """Reduce a number to a single digit by summing its digits repeatedly."""
    while n >= 10:
        n = sum(int(d) for d in str(n))
    return n


def calculate_life_path(target_date: Union[datetime, date]) -> int:
    """
    Calculate the Zorak Corp Life Path number for a given date.
    
    Zorak Corp Method:
    1. Reduce month to single digit
    2. Reduce day to single digit
    3. Reduce year to single digit
    4. Add the three reduced values
    5. Reduce the sum to a single digit
    
    Args:
        target_date: The date to calculate life path for
        
    Returns:
        Single digit life path number (1-9)
    
    Example:
        July 19, 1987 → 07/19/1987
        Month: 0 + 7 = 7
        Day: 1 + 9 = 10 → 1 + 0 = 1
        Year: 1 + 9 + 8 + 7 = 25 → 2 + 5 = 7
        Sum: 7 + 1 + 7 = 15 → 1 + 5 = 6
        Life Path = 6
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    month = target_date.month
    day = target_date.day
    year = target_date.year
    
    # Reduce each component to single digit
    reduced_month = reduce_to_single_digit(month)
    reduced_day = reduce_to_single_digit(day)
    reduced_year = reduce_to_single_digit(sum(int(d) for d in str(year)))
    
    # Sum and reduce to final life path
    total = reduced_month + reduced_day + reduced_year
    life_path = reduce_to_single_digit(total)
    
    return life_path


def is_trading_allowed_today() -> tuple[bool, int, str]:
    """
    Check if trading is allowed today based on Zorak Corp numerology.
    
    Returns:
        tuple: (is_allowed, life_path_number, explanation)
    """
    today = datetime.now().date()
    life_path = calculate_life_path(today)
    
    # Block trading on Life Path 3 days
    if life_path == 3:
        explanation = (
            f"🔢 Today's Life Path: {life_path}\n"
            f"📅 Date: {today.strftime('%m/%d/%Y')}\n"
            f"⛔ Trading BLOCKED - Life Path 3 day\n"
            f"💡 Per Zorak Corp numerology, avoid trading on Life Path 3 days"
        )
        return False, life_path, explanation
    
    explanation = (
        f"🔢 Today's Life Path: {life_path}\n"
        f"📅 Date: {today.strftime('%m/%d/%Y')}\n"
        f"✅ Trading ALLOWED"
    )
    return True, life_path, explanation


def get_life_path_breakdown(target_date: Union[datetime, date] = None) -> str:
    """
    Get a detailed breakdown of the life path calculation.
    
    Args:
        target_date: Date to calculate (defaults to today)
        
    Returns:
        Formatted string showing calculation steps
    """
    if target_date is None:
        target_date = datetime.now().date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()
    
    month = target_date.month
    day = target_date.day
    year = target_date.year
    
    # Calculate reductions with steps
    reduced_month = reduce_to_single_digit(month)
    reduced_day = reduce_to_single_digit(day)
    year_sum = sum(int(d) for d in str(year))
    reduced_year = reduce_to_single_digit(year_sum)
    
    total = reduced_month + reduced_day + reduced_year
    life_path = reduce_to_single_digit(total)
    
    breakdown = f"""
🔢 Zorak Corp Life Path Calculation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Date: {target_date.strftime('%B %d, %Y')} → {month:02d}/{day:02d}/{year}

Step 1 - Reduce each part:
  Month: {month} → {reduced_month}
  Day:   {day} → {reduced_day}
  Year:  {year} → {year_sum} → {reduced_year}

Step 2 - Add reduced values:
  {reduced_month} + {reduced_day} + {reduced_year} = {total}

Step 3 - Final reduction:
  {total} → {life_path}

✨ Life Path = {life_path}
{'⛔ TRADING BLOCKED' if life_path == 3 else '✅ TRADING ALLOWED'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return breakdown.strip()


if __name__ == "__main__":
    # Test with today's date
    print(get_life_path_breakdown())
    print()
    
    # Test with example date from user (July 19, 1987 should equal 6)
    test_date = date(1987, 7, 19)
    print(get_life_path_breakdown(test_date))
