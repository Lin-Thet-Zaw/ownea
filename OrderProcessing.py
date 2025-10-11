import numpy as np
import MetaTrader5 as mt5
import requests # Added for Telegram API calls

# --- Telegram Bot Configuration ---
# IMPORTANT: Replace with your actual Telegram Bot Token and Chat ID
# How to get a bot token: Talk to BotFather on Telegram (search for @BotFather).
# How to get your chat ID: Send a message to your bot, then go to
# https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates in your browser.
# Look for 'chat' -> 'id' in the JSON response.
TELEGRAM_BOT_TOKEN = '8075859191:AAFI4-6kBSF9tKbPWd6XgqS-xXHjU0AgAgM'
TELEGRAM_CHAT_ID = '-1002731577965'
# ----------------------------------

def send_telegram_message(message: str):
    """
    Sends a message to a Telegram chat using the Telegram Bot API.

    Args:
        message (str): The text message to send.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram bot token or chat ID is not configured. Cannot send message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # Use Markdown for formatting (e.g., bold text)
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"Telegram message sent successfully. Response: {response.json()}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error sending Telegram message: {http_err} - {response.text}")
    except Exception as err:
        print(f"Other error sending Telegram message: {err}")


def get_lot(balance):
    '''
    This function calculates the lot size for a given trade based on the current account balance.
    It uses a tiered approach to determine lot size.
    '''
    minimum, maximum = 1000, 2001
    
    while True:
        if 0 <= int(balance) <= 500:
            return round((250 / 20000), 2) # Example fixed lot for very small balances
        elif 501 <= int(balance) <= 1000:
            return round((np.mean([500, 1000]) / 20000), 2)
        elif minimum <= int(balance) < maximum:
            return round((np.mean([minimum, maximum]) / 20000), 2)
        else:
            # If balance is outside the current [minimum, maximum] range, expand the range
            minimum += 1000
            maximum += 1000
            continue # Continue loop with expanded range
    

def get_sl(entry, tp):
    '''
    This function calculates the stop loss value based on a risk-to-reward ratio (RRR) of 1.2.
    
    Args:
        entry (float): The trade entry price.
        tp (float): The take profit price.
        
    Returns:
        float: The calculated stop loss price.
    '''
    return (entry - ((tp - entry) / 1.2))


def Buy_req(symbol, entryp, min_val, avg_val):
    '''
    This function creates and returns a dictionary representing a buy order request
    for MetaTrader 5. Although the order won't be sent, these values are used for the Telegram message.
    
    Args:
        symbol (str): The trading symbol (e.g., 'EURUSD').
        entryp (float): The intended entry price.
        min_val (float): The calculated 'minimum' indicator value.
        avg_val (float): The calculated 'average' indicator value.
        
    Returns:
        dict: A dictionary configured with relevant details for an MT5 buy order request (for values only),
              including TP1, TP2, and TP3.
    '''
    # Get lot amount based on current account balance
    account_info = mt5.account_info()._asdict()
    if account_info:
        current_balance = account_info.get('balance', 0.0)
    else:
        print("Could not retrieve MT5 account info. Using default balance 0.0.")
        current_balance = 0.0

    lot = get_lot(current_balance)
    
    # Double the lot if the entry price is closer to the average line (as per original logic)
    if entryp >= np.mean([min_val, avg_val]):
        lot = round(lot * 2, 2)

    # Get the number of decimal places for the current symbol (important for price precision)
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        decimals = symbol_info.digits # Use symbol_info.digits for precision
    else:
        decimals = 5 if 'JPY' not in symbol else 3 # Fallback if symbol_info fails

    # Get the current ask price for buy order
    current_ask_price = mt5.symbol_info_tick(symbol).ask
        
    # Calculate TP3 (original TP)
    tp3 = round(avg_val, decimals)
    
    # Calculate the distance between entry and TP3
    distance = tp3 - current_ask_price
    
    # Calculate TP1 and TP2, splitting the distance into three equal parts
    tp1 = round(current_ask_price + (distance / 3), decimals)
    tp2 = round(current_ask_price + (2 * distance / 3), decimals)

    # Create the buy request dictionary (only for value extraction, not for sending)
    req = {
        'action': mt5.TRADE_ACTION_DEAL, # This action type is kept for consistency but is not used to send order
        'symbol': symbol,
        'volume': lot,
        'type': mt5.ORDER_TYPE_BUY,
        'price': current_ask_price,
        'sl': round(get_sl(current_ask_price, avg_val), decimals), # SL based on actual ask price, not entryp
        'tp1': tp1, # First Take Profit
        'tp2': tp2, # Second Take Profit
        'tp3': tp3, # Third Take Profit (original TP)
        'deviation': 1, # Kept for consistency, not used to send order
        'type_time': mt5.ORDER_TIME_GTC, # Kept for consistency, not used to send order
        'type_filling': mt5.ORDER_FILLING_FOK # Kept for consistency, not used to send order
    }
    
    return req


def Sell_req(symbol, entryp, max_val, avg_val):
    '''
    This function creates and returns a dictionary representing a sell order request
    for MetaTrader 5. Although the order won't be sent, these values are used for the Telegram message.
    
    Args:
        symbol (str): The trading symbol (e.g., 'EURUSD').
        entryp (float): The intended entry price.
        max_val (float): The calculated 'maximum' indicator value.
        avg_val (float): The calculated 'average' indicator value.
        
    Returns:
        dict: A dictionary configured with relevant details for an MT5 sell order request (for values only),
              including TP1, TP2, and TP3.
    '''
    # Get lot amount based on current account balance
    account_info = mt5.account_info()._asdict()
    if account_info:
        current_balance = account_info.get('balance', 0.0)
    else:
        print("Could not retrieve MT5 account info. Using default balance 0.0.")
        current_balance = 0.0

    lot = get_lot(current_balance)
    
    # Double the lot if the entry price is closer to the average line (as per original logic)
    if entryp <= np.mean([max_val, avg_val]):
        lot = round(lot * 2, 2)
    
    # Get the number of decimal places for the current symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        decimals = symbol_info.digits
    else:
        decimals = 5 if 'JPY' not in symbol else 3 # Fallback

    # Get the current bid price for sell order
    current_bid_price = mt5.symbol_info_tick(symbol).bid

    # Calculate TP3 (original TP)
    tp3 = round(avg_val, decimals)

    # Calculate the distance between entry and TP3 (negative for sell, as price decreases)
    distance = tp3 - current_bid_price
    
    # Calculate TP1 and TP2, splitting the distance into three equal parts
    tp1 = round(current_bid_price + (distance / 3), decimals)
    tp2 = round(current_bid_price + (2 * distance / 3), decimals)

    # Create the sell request dictionary (only for value extraction, not for sending)
    req = {
        'action': mt5.TRADE_ACTION_DEAL, # This action type is kept for consistency but is not used to send order
        'symbol': symbol,
        'volume': lot,
        'type': mt5.ORDER_TYPE_SELL,
        'price': current_bid_price,
        'sl': round(get_sl(current_bid_price, avg_val), decimals), # SL based on actual bid price, not entryp
        'tp1': tp1, # First Take Profit
        'tp2': tp2, # Second Take Profit
        'tp3': tp3, # Third Take Profit (original TP)
        'deviation': 1, # Kept for consistency, not used to send order
        'type_time': mt5.ORDER_TIME_GTC, # Kept for consistency, not used to send order
        'type_filling': mt5.ORDER_FILLING_FOK # Kept for consistency, not used to send order
    }

    return req


def Execute_Buy_Order(symbol: str, openp: float, min_val: float, avg_val: float, timeframe: str):
    '''
    This function simulates a buy order by sending a Telegram message with trade details.
    It no longer sends actual orders to MetaTrader 5.
    
    Args:
        symbol (str): The trading symbol.
        openp (float): The open price of the current candle (used for reference in logic).
        min_val (float): The calculated 'minimum' indicator value.
        avg_val (float): The calculated 'average' indicator value.
        timeframe (str): The timeframe of the signal (e.g., '15m', '1h').
    '''
    # Create buy request to get the calculated price, SL, and TP
    buy_request = Buy_req(symbol, openp, min_val, avg_val)
    
    # Extract relevant details for the Telegram message
    trade_symbol = buy_request['symbol']
    trade_price = buy_request['price']
    trade_sl = buy_request['sl']
    trade_tp1 = buy_request['tp1']
    trade_tp2 = buy_request['tp2']
    trade_tp3 = buy_request['tp3']

    message = (
        f"🟢 *Buy Signal Alert*\n"
        f"📊 *Symbol*: {trade_symbol}\n"
        f"⏳ *Timeframe*: {timeframe}\n"
        f"📈 *Entry Price*: {trade_price:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🚫 *Stop Loss (SL)*: {trade_sl:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 1 (TP1)*: {trade_tp1:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 2 (TP2)*: {trade_tp2:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 3 (TP3)*: {trade_tp3:.{mt5.symbol_info(trade_symbol).digits}f}"
    )
    
    print(f"Simulating Buy order for {symbol}. Sending Telegram message...")
    send_telegram_message(message)
    print(f"Buy signal message sent for {symbol}.")


def Execute_Sell_Order(symbol: str, openp: float, max_val: float, avg_val: float, timeframe: str):
    '''
    This function simulates a sell order by sending a Telegram message with trade details.
    It no longer sends actual orders to MetaTrader 5.
    
    Args:
        symbol (str): The trading symbol.
        openp (float): The open price of the current candle (used for reference in logic).
        max_val (float): The calculated 'maximum' indicator value.
        avg_val (float): The calculated 'average' indicator value.
        timeframe (str): The timeframe of the signal (e.g., '15m', '1h').
    '''
    # Create sell request to get the calculated price, SL, and TP
    sell_request = Sell_req(symbol, openp, max_val, avg_val)

    # Extract relevant details for the Telegram message
    trade_symbol = sell_request['symbol']
    trade_price = sell_request['price']
    trade_sl = sell_request['sl']
    trade_tp1 = sell_request['tp1']
    trade_tp2 = sell_request['tp2']
    trade_tp3 = sell_request['tp3']

    message = (
        f"🔴 *Sell Signal Alert*\n"
        f"📊 *Symbol*: {trade_symbol}\n"
        f"⏳ *Timeframe*: {timeframe}\n"
        f"📉 *Entry Price*: {trade_price:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🚫 *Stop Loss (SL)*: {trade_sl:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 1 (TP1)*: {trade_tp1:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 2 (TP2)*: {trade_tp2:.{mt5.symbol_info(trade_symbol).digits}f}\n"
        f"🎯 *Take Profit 3 (TP3)*: {trade_tp3:.{mt5.symbol_info(trade_symbol).digits}f}"
    )

    print(f"Simulating Sell order for {symbol}. Sending Telegram message...")
    send_telegram_message(message)
    print(f"Sell signal message sent for {symbol}.")
