from alpacaClient import alpacaClient
from messageClient import messageClient
from datetime import datetime, timedelta

secrets = {
    "alpaca_api_key": "******",
    "alpaca_secret_key": "******",
    "sender_email": "******",
    "sender_password": "******",
    "recipient_email": "******"
}

ema_50_tqqq = 0

def lambda_handler_function():
    global ema_50_tqqq

    stock = "TQQQ"

    # Initialize alpaca client
    alpaca_client = alpacaClient(secrets["alpaca_api_key"], secrets["alpaca_secret_key"], test_mode=True)
    # Initialize message client
    message_client = messageClient(secrets["sender_email"], secrets["sender_password"], secrets["recipient_email"])

    # Get current position (either in cash or in stock)
    inCash = alpaca_client.in_cash()

    # Get current price of TQQQ
    curr_price = alpaca_client.get_price_of_stock(stock)

    # Compute 50 day exponential average of TQQQ
    day_50_exponential_avg = alpaca_client.get_50_day_exponential_avg(stock)
    # day_50_exponential_avg = (curr_price - ema_50_tqqq) * (2/51) + ema_50_tqqq

    # Store response message to text
    current_datetime = datetime.now()
    text_response = f"({current_datetime.strftime('%m/%d/%Y')})\nProgram executed at: {current_datetime.strftime('%H:%M')}\n\n"

    # Determine if to buy or sell or hold
    if (day_50_exponential_avg > curr_price) and not inCash:
        # Sell
        print(f"Selling stock (day_50_exponential_avg: {day_50_exponential_avg}) (curr_price: {curr_price}) (inCash: {inCash})")
        submitted_time, filled_time, filled_price = alpaca_client.sell_max_stock(stock)
        if filled_time is None:
            text_response += f"WARNING: Attempted to sell {stock}\n\nOrder submitted at {submitted_time}, but not filled after 2 minutes. Please check account to determine if order went thru.\n\nAsk price (at time of comparision to 50-day ema: {day_50_exponential_avg}): {curr_price}"
        else:
            text_response += f"Sold {stock}\n\nOrder submitted at {submitted_time}, filled at {filled_time}\nAsk price (at time of comparision to 50-day ema: {day_50_exponential_avg}): {curr_price}\nFilled price: {filled_price}"
    elif (day_50_exponential_avg < curr_price) and inCash:
        # Buy
        print(f"Buying stock (day_50_exponential_avg: {day_50_exponential_avg}) (curr_price: {curr_price}) (inCash: {inCash})")
        submitted_time, filled_time, filled_price = alpaca_client.buy_max_stock(stock)
        if filled_time is None:
            text_response += f"WARNING: Attempted to purchase {stock}\n\nOrder submitted at {submitted_time}, but not filled after 5 minutes. Please check account to determine if order went thru.\n\nAsk price (at time of comparision to 50-day ema: {day_50_exponential_avg}): {curr_price}"
        else:
            text_response += f"Purchased {stock}\n\nOrder submitted at {submitted_time}, filled at {filled_time}\nAsk price (at time of comparision to 50-day ema: {day_50_exponential_avg}): {curr_price}\nFilled price: {filled_price}"
    else:
        print(f"Taking no action (day_50_exponential_avg: {day_50_exponential_avg}) (curr_price: {curr_price}) (inCash: {inCash})")
        position = "cash" if inCash else stock
        text_response += f"No action taken. Remaining in {position}."
    
    # Send text message
    message_client.send_message(f"Trading Algorithm update ({current_datetime.strftime('%m/%d/%Y')})", text_response)

    # Determine when market closes next --> set trigger for when to run next
    next_closing_time = alpaca_client.get_next_closing_time()
    mins_1_before_closing = next_closing_time - timedelta(minutes=1)

    # Recompute ema_50_tqqq (after market is closed)
    ema_50_tqqq = alpaca_client.recompute_50_ema(stock, ema_50_tqqq)

    return mins_1_before_closing

lambda_handler_function()
