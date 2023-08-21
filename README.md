# StockTrader
### Automatic stock trader implementing algorithm for maximizing performance and minimizing drawdown for TQQQ

#### Algorithm
The goal of the algorithm is to capture at least the growth of TQQQ and to reduce the drawdown.

TQQQ is an extremely high performing ETF that has immense drawdown. To minimize this drawdown one possible algorithm is to follow the 50 DMA of TQQQ to determine when to transition between US government bonds and TQQQ. This however, requires the assumption that when the stock market trends downwards, bonds upwards. During the COVID era, this assumption proved false. To account for this the algorithm that is implemented transitions between TQQQ and remaining in cash.

At the end of every trading day -- 1 minute before closing as this is as close as the algorithm can get give the use of the Alpaca API -- the algorithm computes the 50-day EMA. If the 50-day EMA is greater than the current price of TQQQ, the algorithm executes a SELL order, whereas if the price of TQQQ is greater than the 50-day EMA, the algorithm executes a BUY order. Resulting in either remaining in fully in TQQQ or fully in cash.

The algorithm is able to significantly reduce daily draw down, acheiving a maximum daily draw down of under 20%. It is also able to acheive ~80% cumulative annual growth rate. As a result, it performs much better than TQQQ when investing over the long term.

#### API usage
The implemented algorithm relies on the Alpaca API as it was the API with the greatest amount of documenation to allow individual users to interact with the stock market. The code will be updated once Schwab releases its upcoming trading API.

#### To run
To run this algorithm one should set up an automation to execute the program 1 minute before market closing (minimizing this time while ensure trades are still able to execute before the market closes will acheive maximum growth as the results explained above were acheived using market data of closing prices).

* Currently the program is structured assuming it will be run on a lambda function hosted via AWS, but this is not a requirement.
