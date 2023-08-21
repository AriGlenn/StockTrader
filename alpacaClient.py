from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, GetCalendarRequest
from alpaca.data import StockLatestQuoteRequest, StockHistoricalDataClient, StockBarsRequest, TimeFrame
from datetime import datetime, timedelta
import time
import numpy as np


class alpacaClient:
    def __init__(self, api_key, secret_key, test_mode=False):
        # Initialize data client
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        # Initialize trading client
        self.trading_client = TradingClient(api_key, secret_key, paper=test_mode)

    def _get_market_days_ago(self, days_ago):
        print(f"Getting {days_ago} market days ago")
        current_date = datetime.now().date()
        result_date = current_date - timedelta(days=2*days_ago)
        request_params =  GetCalendarRequest(
            start = result_date.strftime('%Y-%m-%d'),
            end = current_date.strftime('%Y-%m-%d')
        )
        trading_calendar = self.trading_client.get_calendar(request_params)
        dates = [date.close for date in trading_calendar][-days_ago:]
        return dates[0]
    
    def _get_account_info(self):
        print("Getting account info")
        account = self.trading_client.get_account()
        account_info = {}
        for property_name, value in account:
            account_info[property_name] = value
        return account_info
    
    def _get_cash_holdings(self):
        print("Getting cash holdings")
        return self._get_account_info()["non_marginable_buying_power"]

    def _get_all_assets(self):
        print("Getting all assets")
        return self.trading_client.get_all_positions()
    
    def _get_order_status(self, order_id):
        print(f"Getting status of order id: {order_id}")
        filled_time = None
        filled_price = None
        num_attempts = 1
        while not filled_time:
            if num_attempts != 1:
                print("Order not filled yet, sleeping for 30 seconds...")
                time.sleep(30)
            print(f"Checking attempt #{num_attempts}")
            status_info = {}
            order_status = self.trading_client.get_order_by_id(order_id)
            for key, val in order_status:
                status_info[key] = val
            filled_time = status_info["filled_at"]
            filled_price = status_info["filled_avg_price"]
            if num_attempts == 4:
                # Report error if order not filled after 2 minutes
                print("WARNING: Checked order status for 2 minutes and order was not filled")
                break
            num_attempts += 1
        return filled_time.strftime("%H:%M:%S"), filled_price
    
    def _buy_stock_notional(self, stock, notional_amount):
        print(f"Buying {notional_amount} worth of {stock}")
        # Create market order
        market_order_data = MarketOrderRequest(
            symbol=stock,
            notional=notional_amount,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY
        )
        # Place order
        market_order = self.trading_client.submit_order(order_data=market_order_data)
        order_info = {}
        for key, val in market_order:
            order_info[key] = val
        submitted_time = order_info["submitted_at"].strftime("%H:%M:%S")
        print(f"Order to buy submitted at {submitted_time} (id: {order_info['id']})")
        # Get order status
        filled_time, filled_price = self._get_order_status(order_info["id"])
        return submitted_time, filled_time, filled_price

    def buy_max_stock(self, stock):
        print(f"Buying max stock of {stock}")
        # Get cash holdings
        cash_holdings = self._get_cash_holdings()
        # Convert all cash to stock
        return self._buy_stock_notional(stock, cash_holdings)
    
    def sell_max_stock(self, stock):
        print(f"Selling max stock of {stock}")
        market_order = self.trading_client.close_position(stock)
        order_info = {}
        for key, val in market_order:
            order_info[key] = val
        submitted_time = order_info["submitted_at"].strftime("%H:%M:%S")
        print(f"Order to sell submitted at {submitted_time} (id: {order_info['id']})")
        # Get order status
        filled_time, filled_price = self._get_order_status(order_info["id"])
        return submitted_time, filled_time, filled_price

    def get_price_of_stock(self, stock):
        print(f"Getting price of {stock}")
        quote = self.data_client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=stock))
        print(f'Current price of {stock} is: {quote[stock].ask_price}')
        return quote[stock].ask_price
    
    def get_closing_price(self, stock):
        request_params = StockBarsRequest(
            symbol_or_symbols=stock,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=1),
            end=datetime.now()
        )
        data = self.data_client.get_stock_bars(request_params)[stock][0]
        return data.close

    def get_50_day_exponential_avg(self, stock):
        print(f"Getting 50-day exponential moving average of {stock}")
        period_length = 50 + 1 + 1
        start_date = self._get_market_days_ago(period_length)
        request_params = StockBarsRequest(
            symbol_or_symbols=stock,
            timeframe=TimeFrame.Day,
            start=start_date
        )
        days = self.data_client.get_stock_bars(request_params)[stock]
        closing_prices = [day.close for day in days]
        print(f"Closing prices recorded: {closing_prices}")
        sma_prev = np.sum(closing_prices[:-1])/50
        ema_prev = sma_prev
        curr_price = closing_prices[-1]
        ema_curr = (curr_price - sma_prev) * (2/51) + ema_prev
        print(f"50-day ema: {ema_curr}")
        return ema_curr

    def get_next_closing_time(self):
        print("Getting next closing time")
        clock = self.trading_client.get_clock()
        return clock.next_close
    
    def in_cash(self):
        print("Getting in cash position")
        return (len(self._get_all_assets()) == 0)

    def market_open(self):
        print("Getting status of market clock")
        return self.trading_client.get_clock().is_open
    
    def recompute_50_ema(self, stock, ema):
        print("Recomputing 50 day ema")
        # Sleep until market is closed
        while (self.market_open()):
            time.sleep(60)
        # Recompute ema_50_tqqq (after market is closed)
        return ((self.closing_price(stock) - ema) * (2/51) + ema)
