import sys
import pandas as pd
from time import sleep
import MetaTrader5 as mt5
from datetime import datetime
from pytz import utc # Import utc timezone

# Ensure local imports work by adding current directory to path
sys.path.append('.')

# Import custom modules
from DataProcessing import Indicator
from OrderProcessing import Execute_Buy_Order, Execute_Sell_Order # These will now send Telegram messages
from TimeProcessing import MarketIsOpen, NewCandleUpdate, get_mt5_interval

# Trading symbols and timeframes
# Each tuple now stores: (symbol, timeframe, last_processed_candle_timestamp)
# last_processed_candle_timestamp will be updated in UTC
symbols = [
    ['EURUSD-VIP', '15m', None], ['XAUUSD-VIP', '15m', None], ['EURGBP-VIP', '15m', None], ['EURCAD-VIP', '15m', None], ['EURAUD-VIP', '15m', None], ['EURNZD-VIP', '15m', None],
    ['XAUUSD-VIP', '30m', None], ['EURCHF-VIP', '30m', None], ['GBPUSD-VIP', '30m', None], ['GBPCAD-VIP', '30m', None], ['GBPNZD-VIP', '30m', None], ['GBPAUD-VIP', '30m', None],
    ['XAUUSD-VIP', '1h', None],  ['GBPJPY-VIP', '1h', None],  ['GBPCHF-VIP', '1h', None],  ['USDCAD-VIP', '1h', None],  ['USDJPY-VIP', '1h', None],  ['USDCHF-VIP', '1h', None],
    ['CADJPY-VIP', '2h', None],  ['CADCHF-VIP', '2h', None],  ['NZDUSD-VIP', '2h', None],  ['NZDCAD-VIP', '2h', None],  ['NZDCHF-VIP', '2h', None],
    ['XAUUSD-VIP', '4h', None],  ['AUDUSD-VIP', '4h', None],  ['AUDCAD-VIP', '4h', None],  ['AUDNZD-VIP', '4h', None],  ['AUDJPY-VIP', '4h', None], ['AUDCHF-VIP', '4h', None],
    ['CHFJPY-VIP', '4h', None],
    ['XAUUSD-VIP', '1d', None],
]

# Initialize MT5 and login once at the start of the program
# This block handles initial connection regardless of market open status
mt5_account, mt5_passw, server = None, None, None

while True:
    try:
        mt5_account = int(input('Enter MT5 account number: '))
        mt5_passw = str(input('Enter MT5 password: '))
        server = str(input('Enter server name: '))
        break
    except ValueError:
        print('Invalid input. Account number must be an integer. Please try again.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}. Please try again.')

# Initialize MetaTrader5 terminal
if not mt5.initialize(login=mt5_account, password=mt5_passw, server=server):
    print(f'initialize() failed, error code={mt5.last_error()}')
    sys.exit()
print(f"MetaTrader5 initialized successfully for account #{mt5_account}")

# Logging in to MT5 account
if not mt5.login(login=mt5_account, password=mt5_passw, server=server):
    print(f'Failed to connect to account #{mt5_account}, error code={mt5.last_error()}')
    mt5.shutdown()
    sys.exit()
print(f"Successfully logged in to MT5 account #{mt5_account}")


# Main Program Loop
while True:
    # Check market status. If market is closed, sleep until it opens.
    if not MarketIsOpen():
        print('\nMARKET IS CLOSED.\nSleeping till market opens...')
        # Reset last processed candle timestamps when market closes
        for symbol_lst in symbols:
            symbol_lst[2] = None # Set last_processed_candle_timestamp to None
        
        # Sleep for a shorter interval and check more frequently or until market opens
        while not MarketIsOpen():
            sleep(300) # Sleep for 5 minutes
            if mt5.terminal_info().connected: # Check connection during sleep
                print("Market still closed. Sleeping...")
            else:
                print("Connection lost while market closed. Attempting to re-initialize...")
                if not mt5.initialize(login=mt5_account, password=mt5_passw, server=server):
                    print(f'Re-initialize failed, error code={mt5.last_error()}. Retrying...')
                    sleep(60) # Wait a bit before next re-init attempt
                    continue
                if not mt5.login(login=mt5_account, password=mt5_passw, server=server):
                    print(f'Re-login failed, error code={mt5.last_error()}. Retrying...')
                    sleep(60) # Wait a bit before next re-login attempt
                    continue
                print("Reconnected to MT5.")
        print("\nMARKET IS OPEN! Starting trading analysis...")

    # Analysis & Trading Loop (runs when market is open)
    while MarketIsOpen():
        # Check internet connection from terminal
        if not mt5.terminal_info().connected:
            print("MT5 terminal disconnected. Attempting to re-connect...")
            if not mt5.initialize(login=mt5_account, password=mt5_passw, server=server):
                print(f'Re-initialize failed, error code={mt5.last_error()}. Retrying...')
                sleep(30)
                continue
            if not mt5.login(login=mt5_account, password=mt5_passw, server=server):
                print(f'Re-login failed, error code={mt5.last_error()}. Retrying...')
                sleep(30)
                continue
            print("Successfully reconnected to MT5.")
            continue # Continue to the next iteration of the inner loop to process symbols

        for i, symbol_lst in enumerate(symbols):
            symbol, timeframe, last_processed_candle_timestamp = symbol_lst

            # Use NewCandleUpdate to check if it's the right system time for a potential new candle
            if NewCandleUpdate(timeframe):
                # Fetch the latest candle's data directly from MT5
                rates_latest_candle = mt5.copy_rates_from_pos(symbol, get_mt5_interval(timeframe), 0, 1)

                if rates_latest_candle is None or len(rates_latest_candle) == 0:
                    print(f"Failed to retrieve latest rates for {symbol}. Skipping this cycle.")
                    continue
                
                # Get the timestamp of the latest candle returned by MT5 (converted to UTC datetime)
                current_candle_timestamp_mt5 = datetime.fromtimestamp(rates_latest_candle[0][0], tz=utc)
                
                # Check if this candle's timestamp is newer than the last one we processed for this symbol
                if last_processed_candle_timestamp is None or current_candle_timestamp_mt5 > last_processed_candle_timestamp:
                    print(f"--- Processing new candle for {symbol} ({timeframe}): {current_candle_timestamp_mt5} ---")
                    
                    # Select symbol on Market Watch (necessary before getting rates/ticks)
                    if not mt5.symbol_select(symbol, True): # True to add if not exists
                        print(f'Failed to select {symbol} on Market Watch, error code={mt5.last_error()}\nShutting down the program...')
                        mt5.shutdown()
                        sys.exit()
                    
                    # Process candles only if symbol has no open positions
                    if len(mt5.positions_get(symbol=symbol)) < 1:
                        # Retrieve last 550 candles for indicator calculation
                        rates = mt5.copy_rates_from_pos(symbol, get_mt5_interval(timeframe), 0, 550)
                        
                        if rates is not None and len(rates) > 0:
                            # Create DataFrame and convert time column to datetime objects (important for DataProcessing)
                            df_rates = pd.DataFrame(rates)
                            df_rates['time'] = pd.to_datetime(df_rates['time'], unit='s', utc=True)
                            
                            # Ensure enough data exists for indicator calculation (min 20 candles: 2 for prev_high/low + ATR period)
                            if len(df_rates) < 20: 
                                print(f"Not enough historical data ({len(df_rates)} candles) for {symbol} to calculate indicators. Skipping.")
                                continue

                            # Get current open (last candle), previous high, and previous low (second to last candle)
                            curr_open = df_rates.iloc[-1]['open']
                            prv_high = df_rates.iloc[-2]['high']
                            prv_low = df_rates.iloc[-2]['low']
                            
                            # Analyze candles and return indicator lines values for the previous complete candle
                            maximum, minimum, average = Indicator(df_rates)
                            
                            # Check if indicator values are valid (not NaN)
                            if pd.isna(maximum) or pd.isna(minimum) or pd.isna(average):
                                print(f"Indicator calculation resulted in NaN for {symbol}. Skipping trading opportunity.")
                                continue

                            # Define buy and sell Conditions
                            buy_condition = ((prv_low <= minimum) and (curr_open < average))
                            sell_condition = ((prv_high >= maximum) and (curr_open > average))

                            # Execute Sell/Buy Order if conditions are met
                            # These functions now send Telegram messages instead of executing trades
                            if buy_condition:
                                print(f"Buy condition met for {symbol}. Sending buy signal to Telegram...")
                                # Pass the timeframe to the Execute_Buy_Order function
                                Execute_Buy_Order(symbol=symbol, openp=curr_open, min_val=minimum, avg_val=average, timeframe=timeframe)
                            elif sell_condition:
                                print(f"Sell condition met for {symbol}. Sending sell signal to Telegram...")
                                # Pass the timeframe to the Execute_Sell_Order function
                                Execute_Sell_Order(symbol=symbol, openp=curr_open, max_val=maximum, avg_val=average, timeframe=timeframe)
                            else:
                                print(f"No trade condition met for {symbol}.")

                        else:
                            print(f'Failed to retrieve sufficient historical rates for {symbol} from MT5 terminal. Skipping...')
                    else:
                        print(f"Skipping {symbol} as there are open positions already. Waiting for position close or manual intervention.")
                    
                    # Update the last processed candle timestamp for this symbol
                    symbols[i][2] = current_candle_timestamp_mt5
        
        # After checking all symbols, sleep for a short period before the next loop iteration
        sleep(5) # Sleep for 5 seconds to prevent excessive CPU usage and API calls.