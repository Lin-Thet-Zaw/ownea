import numpy as np
import pandas as pd
from talib import ATR # For Average True Range calculation

def nz(x, y=None):
    '''
    Equivalent to Pine Script's nz() function.
    Returns x if it's not NaN or None; otherwise, returns y (if not NaN or None), or 0.
    '''
    if pd.isna(x) or x is None: # Use pd.isna for robustness with numpy/pandas NaNs
        if y is not None and not pd.isna(y):
            return y
        else:
            return 0
    else:
        return x

def Indicator(df_rates_orig: pd.DataFrame):
    '''
    This function takes a dataframe with the candlesticks for a given symbol,
    applies a custom indicator logic, and returns 3 key indicator variables
    (maximum, minimum, average) for the second to last candle (the most recently
    closed complete candle).

    Args:
        df_rates_orig (pd.DataFrame): DataFrame containing candle data with
                                      'open', 'high', 'low', 'close', 'time' columns.

    Returns:
        tuple: (maximum, minimum, average) for the second to last candle.
               Returns (np.nan, np.nan, np.nan) if not enough data.
    '''

    # Ensure the DataFrame is sorted by time, ascending
    df_rates_orig = df_rates_orig.sort_values(by='time').reset_index(drop=True)

    # Check for minimum required data for ATR and subsequent calculations
    atr_period = 18
    # We need at least atr_period + 1 candles to get one ATR value
    # and then at least one more for prev_close, plus one for current candle's src.
    # So effectively, at least atr_period + 2 candles for calculations to start being meaningful.
    if len(df_rates_orig) < atr_period + 2:
        # print(f"Warning: Not enough data for Indicator calculation. Need at least {atr_period + 2} candles, got {len(df_rates_orig)}.")
        return np.nan, np.nan, np.nan

    # Initialize lists to store indicator values for each candle
    # These lists will be filled from the index where calculations become valid.
    upper_lst = [np.nan] * len(df_rates_orig)
    lower_lst = [np.nan] * len(df_rates_orig)
    spt_lst = [np.nan] * len(df_rates_orig)
    os_lst = [np.nan] * len(df_rates_orig)
    max_lst = [np.nan] * len(df_rates_orig)
    min_lst = [np.nan] * len(df_rates_orig)
    avg_lst = [np.nan] * len(df_rates_orig)

    # Calculate ATR once for the entire series. It will have NaNs at the beginning.
    atr_series = ATR(high=df_rates_orig['high'], low=df_rates_orig['low'], close=df_rates_orig['close'], timeperiod=atr_period)

    # Iterate through the DataFrame to calculate indicator values for each candle.
    # We start from 'atr_period' index because ATR(18) requires 18 previous candles.
    # The loop goes up to the last candle (len(df_rates_orig) - 1).
    # The function then returns values for the second-to-last candle.
    for i in range(atr_period, len(df_rates_orig)):
        # Get data for the current candle (index i)
        src = df_rates_orig['close'].iloc[i]
        current_high = df_rates_orig['high'].iloc[i]
        current_low = df_rates_orig['low'].iloc[i]
        
        # Get data for the previous candle (index i-1)
        # These are crucial for comparing against previous indicator states
        prev_close = df_rates_orig['close'].iloc[i-1]
        
        current_atr = atr_series.iloc[i]
        
        # Handle cases where current_atr might be NaN for some reason (e.g., insufficient data start)
        if pd.isna(current_atr):
            continue # Skip calculation for this candle if ATR is not available

        atr_multiplier = current_atr * 5 # As per original code's multiplier
        
        # Calculate 'up' and 'dn' bounds based on current candle's mid-point and ATR
        up = np.mean([current_high, current_low]) + atr_multiplier
        dn = np.mean([current_high, current_low]) - atr_multiplier

        # Get the 'upper' and 'lower' values from the previous candle's calculation (index i-1)
        # Using nz() to handle initial NaN values
        prev_upper_val = nz(upper_lst[i-1])
        prev_lower_val = nz(lower_lst[i-1])

        # Calculate 'upper' (resistance line)
        # If previous close was below previous upper, take the minimum of current 'up' and previous 'upper'
        # Otherwise, 'upper' is just current 'up'
        if prev_close < prev_upper_val:
            upper = min(up, prev_upper_val)
        else:
            upper = up

        # Calculate 'lower' (support line)
        # If previous close was above previous lower, take the maximum of current 'dn' and previous 'lower'
        # Otherwise, 'lower' is just current 'dn'
        if prev_close > prev_lower_val:
            lower = max(dn, prev_lower_val)
        else:
            lower = dn
        
        # Store current 'upper' and 'lower' values
        upper_lst[i] = upper
        lower_lst[i] = lower

        # Calculate 'os' (oscillator state: 1 for overbought, 0 for oversold, or retain previous)
        prev_os_val = nz(os_lst[i-1], 0) # Default prev_os to 0 if not available
        if src > upper:
            os = 1 # Price is above upper bound, likely overbought
        elif src < lower:
            os = 0 # Price is below lower bound, likely oversold
        else:
            os = prev_os_val # Price is within bounds, retain previous state

        os_lst[i] = os # Store current 'os'

        # Calculate 'spt' (Support/Resistance Point)
        # If overbought (os == 1), spt is the lower bound. If oversold/neutral (os == 0), spt is the upper bound.
        if os == 1:
            spt = lower
        else:
            spt = upper
        
        spt_lst[i] = spt # Store current 'spt'

        # Calculate 'maximum' and 'minimum' indicator lines
        # The original `Cross` function was problematic. Re-interpreting the logic:
        # A "cross" typically implies a change in relationship (e.g., price crosses a line).
        # Here, it's approximated by checking if the price has crossed the `spt` value
        # from the perspective of the previous candle's close relative to the current `spt`.

        # Initialize prev_max_val and prev_min_val with the current source if they are the first valid values
        prev_max_val = nz(max_lst[i-1], src)
        prev_min_val = nz(min_lst[i-1], src)

        # Check for a "crossing" event: did prev_close and src cross the spt line?
        is_crossing = False
        if not pd.isna(prev_close) and not pd.isna(spt):
            if (prev_close < spt and src >= spt) or \
               (prev_close > spt and src <= spt):
                 is_crossing = True

        if is_crossing:
            # If a cross is detected, reset or re-evaluate max/min based on current src
            max_val = max(prev_max_val, src) # Take the higher of previous max or current src
            min_val = min(prev_min_val, src) # Take the lower of previous min or current src
        elif os == 0: # Price is oversold (below lower band) -> looking for buy opportunity
            # max_val follows spt (resistance), min_val tracks price (support)
            max_val = min(spt, prev_max_val) # Upper boundary is either spt or previous max (whichever is lower)
            min_val = min(src, prev_min_val) # Lower boundary is either current src or previous min (whichever is lower)
        else: # os == 1 (Price is overbought, above upper band) -> looking for sell opportunity
            # max_val tracks price (resistance), min_val follows spt (support)
            max_val = max(src, prev_max_val) # Upper boundary is either current src or previous max (whichever is higher)
            min_val = max(spt, prev_min_val) # Lower boundary is either spt or previous min (whichever is higher)

        max_lst[i] = max_val
        min_lst[i] = min_val

        # Calculate 'average' line
        avg_val = np.mean([max_val, min_val])
        avg_lst[i] = avg_val

    # The loop has calculated indicator values for all candles up to the last one (index len-1).
    # The requirement is to return values for the "second to last candle only" (index len-2).
    target_idx = len(df_rates_orig) - 2

    # Ensure the target index is valid and calculations were performed up to that point
    if target_idx < atr_period: # Not enough data for the second-to-last candle to have valid indicators
        return np.nan, np.nan, np.nan

    final_maximum = nz(max_lst[target_idx])
    final_minimum = nz(min_lst[target_idx])
    final_average = nz(avg_lst[target_idx])
    
    return final_maximum, final_minimum, final_average
