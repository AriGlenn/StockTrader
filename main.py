from alpacaClient import alpacaClient
from messageClient import messageClient
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import boto3
import pytz
import os

# Define lambda client and cloudwatch events
lambda_client = boto3.client('lambda')
cloudwatch_events = boto3.client('events')

# ema_50_tqqq = 0
def lambda_handler_function():
    # global ema_50_tqqq
    stock = "TQQQ"

    # Get secrets
    secrets = get_secrets()

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
    est = pytz.timezone('US/Eastern')
    current_datetime = datetime.now(est)
    text_response = f"({current_datetime.strftime('%m/%d/%Y')})\nProgram executed at: {current_datetime.strftime('%H:%M')} (EST)\n\n"

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

    # # Recompute ema_50_tqqq (after market is closed)
    # ema_50_tqqq = alpaca_client.recompute_50_ema(stock, ema_50_tqqq)

    # Determine when market closes next
    next_closing_time = alpaca_client.get_next_closing_time()
    # Set trigger for next runtime
    mins_2_before_closing = next_closing_time - timedelta(minutes=2)

    statement_id = "scheduled-trade-event"
    rule_name = "TradeEvent"
    arn = os.environ['AWS_LAMBDA_FUNCTION_ARN']

    # If the rule doesn't exist, create it, its target, and permissions
    if not rule_exists(rule_name):
        create_rule(rule_name, arn, statement_id)

    # Update the schedule expression for the next invocation
    date = mins_2_before_closing#datetime.utcnow() + timedelta(minutes=1)
    print(f"Next runtime scheduled for: {date}")
    scheduled_time = f"cron({date.minute} {date.hour} {date.day} {date.month} ? {date.year})"
    cloudwatch_events.put_rule(Name=rule_name, ScheduleExpression=scheduled_time)
    

def rule_exists(rule_name):
    try:
        cloudwatch_events.describe_rule(Name=rule_name)
        return True
    except cloudwatch_events.exceptions.ResourceNotFoundException:
        return False
    

def create_rule(rule_name, arn, statement_id):
    params = {
        'Name': rule_name,
        'ScheduleExpression': 'rate(1 minute)'  # Set fake value (will be changed below)
    }
    cloudwatch_events.put_rule(**params)
    
    params = {
        'Rule': rule_name,
        'Targets': [
            {
                'Arn': arn,
                'Id': 'fixed-target-id'
            }
        ]
    }
    cloudwatch_events.put_targets(**params)

    params = {
        'Action': 'lambda:InvokeFunction',
        'FunctionName': arn,
        'Principal': 'events.amazonaws.com',
        'SourceArn': f'arn:aws:events:us-east-2:983676090688:rule/{rule_name}',
        'StatementId': statement_id
    }
    lambda_client.add_permission(**params)


def get_secrets():
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name="us-east-2")
    try:
        get_secret_value_response = client.get_secret_value(SecretId="alpaca_secrets")
    except ClientError as e:
        raise e
    return get_secret_value_response
