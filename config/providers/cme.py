"""CME Futures Trading Configuration Provider"""

from typing import List


def get_rth_windows(tz: str) -> List[str]:
    """
    Get CME Regular Trading Hours windows for the given timezone.
    
    CME Futures Trading Hours (ET):
    - NQ & CL: 6:00 PM Sunday - 5:00 PM Friday (with 1-hour daily break 5-6 PM)
    
    Args:
        tz: Timezone string (e.g., "America/New_York")
        
    Returns:
        List of trading window strings in format ["HH:MM-HH:MM"]
    """
    # CME Futures Trading Hours (ET)
    # NQ & CL: 6:00 PM Sunday - 5:00 PM Friday (with 1-hour daily break 5-6 PM)
    return [
        "18:00-23:59",  # Sunday 6 PM - 11:59 PM
        "00:00-17:00",  # Monday-Thursday: 12 AM - 5 PM
        "18:00-23:59",  # Monday-Thursday: 6 PM - 11:59 PM  
        "00:00-17:00",  # Friday: 12 AM - 5 PM
    ]


def get_supported_symbols() -> List[str]:
    """
    Get list of supported CME futures symbols.
    
    Returns:
        List of supported symbol strings
    """
    return [
        "NQ",  # E-mini NASDAQ-100
        "CL",  # Crude Oil
        "ES",  # E-mini S&P 500
        "YM",  # E-mini Dow Jones
        "RTY", # E-mini Russell 2000
        "GC",  # Gold
        "SI",  # Silver
        "NG",  # Natural Gas
        "ZB",  # 30-Year Treasury Bond
        "ZN",  # 10-Year Treasury Note
        "ZF",  # 5-Year Treasury Note
        "ZT",  # 2-Year Treasury Note
    ]
