import MetaTrader5 as mt5
from pytz import utc # For UTC timezone awareness
from datetime import datetime, time, timedelta # Added timedelta for more robust time calcs


def MarketIsOpen():
    '''
    This function checks if the forex market is currently open based on UTC time.
    Forex market typically opens Sunday 22:00 UTC and closes Friday 21:59 UTC.
    '''
    date_now_utc = datetime.now(tz=utc)
    time_now_utc = date_now_utc.time()
    
    # Define market open and close times in UTC
    open_time_utc = time(hour=22, minute=0, second=0)   # Sunday 22:00 UTC
    close_time_utc = time(hour=21, minute=59, second=0) # Friday 21:59 UTC

    # Get the day of the week (Monday=0, Sunday=6)
    weekday = date_now_utc.weekday()

    # Market is closed on Saturday (weekday 5)
    if weekday == 5:
        return False
    
    # Market is closed on Sunday before open_time_utc
    if weekday == 6 and time_now_utc < open_time_utc:
        return False
    
    # Market is closed on Friday after close_time_utc
    if weekday == 4 and time_now_utc >= close_time_utc:
        return False
    
    # Otherwise, the market is considered open
    return True

def NewCandleUpdate(tframe: str):
    '''
    Returns True if the current UTC system time aligns with the start of a new candle
    for the given trading timeframe (e.g., if it's 00, 15, 30, 45 minutes for a 15m timeframe).
    This function helps to reduce unnecessary API calls by only checking for new candles
    when a new interval begins.

    Args:
        tframe (str): The trading timeframe string (e.g., '5m', '15m', '1h', '4h', '1d').

    Returns:
        bool: True if a new candle interval has just started, False otherwise.
    '''
    date_now_utc = datetime.now(tz=utc)
    current_minute = date_now_utc.minute
    current_hour = date_now_utc.hour

    if tframe == '1m':
        return (current_minute % 1 == 0)
    elif tframe == '3m':
        return (current_minute % 3 == 0)
    elif tframe == '5m':
        return (current_minute % 5 == 0)
    elif tframe == '15m':
        return (current_minute % 15 == 0)
    elif tframe == '30m':
        return (current_minute % 30 == 0)
    elif tframe == '1h':
        return (current_minute == 0)
    elif tframe == '2h':
        return (current_minute == 0 and current_hour % 2 == 0)
    elif tframe == '3h':
        return (current_minute == 0 and current_hour % 3 == 0)
    elif tframe == '4h':
        return (current_minute == 0 and current_hour % 4 == 0)
    elif tframe == '1d':
        # Daily candle typically opens at 00:00 UTC
        return (current_minute == 0 and current_hour == 0)
    else:
        print(f'Invalid timeframe input: {tframe}. Please use a valid timeframe from the list (5m, 15m, 30m, 1h, 2h, 3h, 4h, 1d).')
        return False # Should not happen with validated input


def get_mt5_interval(trading_frame: str):
    '''
    Returns the MetaTrader5 timeframe object corresponding to the given trading timeframe string.

    Args:
        trading_frame (str): The trading timeframe string (e.g., '1m', '5m', '1h').

    Returns:
        int: The MetaTrader5 timeframe constant (e.g., mt5.TIMEFRAME_M15).
             Returns None if the input timeframe is not recognized.
    '''
    if trading_frame == '1m':
        return mt5.TIMEFRAME_M1
    elif trading_frame == '3m':
        return mt5.TIMEFRAME_M3
    elif trading_frame == '5m':
        return mt5.TIMEFRAME_M5
    elif trading_frame == '15m':
        return mt5.TIMEFRAME_M15
    elif trading_frame == '30m':
        return mt5.TIMEFRAME_M30
    elif trading_frame == '1h':
        return mt5.TIMEFRAME_H1
    elif trading_frame == '2h':
        return mt5.TIMEFRAME_H2
    elif trading_frame == '3h':
        return mt5.TIMEFRAME_H3
    elif trading_frame == '4h':
        return mt5.TIMEFRAME_H4
    elif trading_frame == '1d':
        return mt5.TIMEFRAME_D1
    else:
        print(f"Error: Unknown trading timeframe '{trading_frame}'.")
        return None
