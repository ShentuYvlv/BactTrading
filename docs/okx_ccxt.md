okx

Kind: global class
Extends: Exchange

    fetchStatus
    fetchTime
    fetchAccounts
    fetchMarkets
    fetchCurrencies
    fetchOrderBook
    fetchTicker
    fetchTickers
    fetchMarkPrice
    fetchMarkPrices
    fetchTrades
    fetchOHLCV
    fetchFundingRateHistory
    fetchTradingFee
    fetchBalance
    createMarketBuyOrderWithCost
    createMarketSellOrderWithCost
    createOrder
    createOrders
    editOrder
    cancelOrder
    cancelOrders
    cancelOrdersForSymbols
    cancelAllOrdersAfter
    fetchOrder
    fetchOpenOrders
    fetchCanceledOrders
    fetchClosedOrders
    fetchMyTrades
    fetchOrderTrades
    fetchLedger
    fetchDepositAddressesByNetwork
    fetchDepositAddress
    withdraw
    fetchDeposits
    fetchDeposit
    fetchWithdrawals
    fetchWithdrawal
    fetchLeverage
    fetchPosition
    fetchPositions
    fetchPositionsForSymbol
    transfer
    fetchTransfers
    fetchFundingInterval
    fetchFundingRate
    fetchFundingHistory
    setLeverage
    fetchPositionMode
    setPositionMode
    setMarginMode
    fetchCrossBorrowRates
    fetchCrossBorrowRate
    fetchBorrowRateHistories
    fetchBorrowRateHistory
    reduceMargin
    addMargin
    fetchMarketLeverageTiers
    fetchBorrowInterest
    borrowCrossMargin
    repayCrossMargin
    fetchOpenInterest
    fetchOpenInterestHistory
    fetchDepositWithdrawFees
    fetchSettlementHistory
    fetchUnderlyingAssets
    fetchGreeks
    closePosition
    fetchOption
    fetchOptionChain
    fetchConvertQuote
    createConvertTrade
    fetchConvertTrade
    fetchConvertTradeHistory
    fetchConvertCurrencies
    fetchMarginAdjustmentHistory
    fetchPositionsHistory
    fetchLongShortRatioHistory
    watchTrades
    watchTradesForSymbols
    unWatchTradesForSymbols
    unWatchTrades
    watchFundingRate
    watchTicker
    unWatchTicker
    watchTickers
    watchMarkPrice
    watchMarkPrices
    unWatchTickers
    watchBidsAsks
    watchLiquidationsForSymbols
    watchMyLiquidationsForSymbols
    watchOHLCV
    unWatchOHLCV
    watchOHLCVForSymbols
    unWatchOHLCVForSymbols
    watchOrderBook
    watchOrderBookForSymbols
    unWatchOrderBookForSymbols
    unWatchOrderBook
    watchBalance
    watchMyTrades
    watchPositions
    watchOrders
    createOrderWs
    editOrderWs
    cancelOrderWs
    cancelOrdersWs
    cancelAllOrdersWs

fetchStatus

the latest known information on the availability of the exchange API

Kind: instance method of okx
Returns: object - a status structure

See: https://www.okx.com/docs-v5/en/#status-get-status
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchStatus ([params])

fetchTime

fetches the current integer timestamp in milliseconds from the exchange server

Kind: instance method of okx
Returns: int - the current integer timestamp in milliseconds from the exchange server

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-system-time
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchTime ([params])

fetchAccounts

fetch all the accounts associated with a profile

Kind: instance method of okx
Returns: object - a dictionary of account structures indexed by the account type

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchAccounts ([params])

fetchMarkets

retrieves data on all markets for okx

Kind: instance method of okx
Returns: Array<object> - an array of objects representing market data

See: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-instruments
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchMarkets ([params])

fetchCurrencies

fetches all available currencies on an exchange

Kind: instance method of okx
Returns: object - an associative dictionary of currencies

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-currencies
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchCurrencies ([params])

fetchOrderBook

fetches information on open orders with bid (buy) and ask (sell) prices, volumes and other data

Kind: instance method of okx
Returns: object - A dictionary of order book structures indexed by market symbols

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-order-book
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the order book for
limit 	int 	No 	the maximum amount of order book entries to return
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.method 	string 	No 	'publicGetMarketBooksFull' or 'publicGetMarketBooks' default is 'publicGetMarketBooks'

okx.fetchOrderBook (symbol[, limit, params])

fetchTicker

fetches a price ticker, a statistical calculation with the information calculated over the past 24 hours for a specific market

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-ticker
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchTicker (symbol[, params])

fetchTickers

fetches price tickers for multiple markets, statistical information calculated over the past 24 hours for each market

Kind: instance method of okx
Returns: object - a dictionary of ticker structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-tickers
Param 	Type 	Required 	Description
symbols 	Array<string> 	No 	unified symbols of the markets to fetch the ticker for, all market tickers are returned if not assigned
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchTickers ([symbols, params])

fetchMarkPrice

fetches mark price for the market

Kind: instance method of okx
Returns: object - a dictionary of ticker structures

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-mark-price
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchMarkPrice (symbol[, params])

fetchMarkPrices

fetches price tickers for multiple markets, statistical information calculated over the past 24 hours for each market

Kind: instance method of okx
Returns: object - a dictionary of ticker structures

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-mark-price
Param 	Type 	Required 	Description
symbols 	Array<string> 	No 	unified symbols of the markets to fetch the ticker for, all market tickers are returned if not assigned
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchMarkPrices ([symbols, params])

fetchTrades

get the list of most recent trades for a particular symbol

Kind: instance method of okx
Returns: Array<Trade> - a list of trade structures

See

    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-trades
    https://www.okx.com/docs-v5/en/#rest-api-public-data-get-option-trades

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch trades for
since 	int 	No 	timestamp in ms of the earliest trade to fetch
limit 	int 	No 	the maximum amount of trades to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.method 	string 	No 	'publicGetMarketTrades' or 'publicGetMarketHistoryTrades' default is 'publicGetMarketTrades'
params.paginate 	boolean 	No 	only applies to publicGetMarketHistoryTrades default false, when true will automatically paginate by calling this endpoint multiple times

okx.fetchTrades (symbol[, since, limit, params])

fetchOHLCV

fetches historical candlestick data containing the open, high, low, and close price, and the volume of a market

Kind: instance method of okx
Returns: Array<Array<int>> - A list of candles ordered as timestamp, open, high, low, close, volume

See

    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks
    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks-history
    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-mark-price-candlesticks
    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-mark-price-candlesticks-history
    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-index-candlesticks
    https://www.okx.com/docs-v5/en/#rest-api-market-data-get-index-candlesticks-history

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch OHLCV data for
timeframe 	string 	Yes 	the length of time each candle represents
since 	int 	No 	timestamp in ms of the earliest candle to fetch
limit 	int 	No 	the maximum amount of candles to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.price 	string 	No 	"mark" or "index" for mark price and index price candles
params.until 	int 	No 	timestamp in ms of the latest candle to fetch
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters

okx.fetchOHLCV (symbol, timeframe[, since, limit, params])

fetchFundingRateHistory

fetches historical funding rate prices

Kind: instance method of okx
Returns: Array<object> - a list of funding rate structures

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate-history
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the funding rate history for
since 	int 	No 	timestamp in ms of the earliest funding rate to fetch
limit 	int 	No 	the maximum amount of funding rate structures to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters

okx.fetchFundingRateHistory (symbol[, since, limit, params])

fetchTradingFee

fetch the trading fees for a market

Kind: instance method of okx
Returns: object - a fee structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-fee-rates
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchTradingFee (symbol[, params])

fetchBalance

query for balance and get the amount of funds available for trading or funds locked in orders

Kind: instance method of okx
Returns: object - a balance structure

See

    https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance

Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.type 	string 	No 	wallet type, ['funding' or 'trading'] default is 'trading'

okx.fetchBalance ([params])

createMarketBuyOrderWithCost

create a market buy order by providing the symbol and cost

Kind: instance method of okx
Returns: object - an order structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to create an order in
cost 	float 	Yes 	how much you want to trade in units of the quote currency
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.createMarketBuyOrderWithCost (symbol, cost[, params])

createMarketSellOrderWithCost

create a market buy order by providing the symbol and cost

Kind: instance method of okx
Returns: object - an order structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to create an order in
cost 	float 	Yes 	how much you want to trade in units of the quote currency
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.createMarketSellOrderWithCost (symbol, cost[, params])

createOrder

create a trade order

Kind: instance method of okx
Returns: object - an order structure

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order
    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-multiple-orders
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-post-place-algo-order

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to create an order in
type 	string 	Yes 	'market' or 'limit'
side 	string 	Yes 	'buy' or 'sell'
amount 	float 	Yes 	how much of currency you want to trade in units of base currency
price 	float 	No 	the price at which the order is to be fulfilled, in units of the quote currency, ignored in market orders
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.reduceOnly 	bool 	No 	a mark to reduce the position size for margin, swap and future orders
params.postOnly 	bool 	No 	true to place a post only order
params.takeProfit 	object 	No 	takeProfit object in params containing the triggerPrice at which the attached take profit order will be triggered (perpetual swap markets only)
params.takeProfit.triggerPrice 	float 	No 	take profit trigger price
params.takeProfit.price 	float 	No 	used for take profit limit orders, not used for take profit market price orders
params.takeProfit.type 	string 	No 	'market' or 'limit' used to specify the take profit price type
params.stopLoss 	object 	No 	stopLoss object in params containing the triggerPrice at which the attached stop loss order will be triggered (perpetual swap markets only)
params.stopLoss.triggerPrice 	float 	No 	stop loss trigger price
params.stopLoss.price 	float 	No 	used for stop loss limit orders, not used for stop loss market price orders
params.stopLoss.type 	string 	No 	'market' or 'limit' used to specify the stop loss price type
params.positionSide 	string 	No 	if position mode is one-way: set to 'net', if position mode is hedge-mode: set to 'long' or 'short'
params.trailingPercent 	string 	No 	the percent to trail away from the current market price
params.tpOrdKind 	string 	No 	'condition' or 'limit', the default is 'condition'
params.hedged 	bool 	No 	swap and future only true for hedged mode, false for one way mode
params.marginMode 	string 	No 	'cross' or 'isolated', the default is 'cross'

okx.createOrder (symbol, type, side, amount[, price, params])

createOrders

create a list of trade orders

Kind: instance method of okx
Returns: object - an order structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-multiple-orders
Param 	Type 	Required 	Description
orders 	Array 	Yes 	list of orders to create, each object should contain the parameters required by createOrder, namely symbol, type, side, amount, price and params
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.createOrders (orders[, params])

editOrder

edit a trade order

Kind: instance method of okx
Returns: object - an order structure

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-amend-order
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-post-amend-algo-order

Param 	Type 	Required 	Description
id 	string 	Yes 	order id
symbol 	string 	Yes 	unified symbol of the market to create an order in
type 	string 	Yes 	'market' or 'limit'
side 	string 	Yes 	'buy' or 'sell'
amount 	float 	Yes 	how much of the currency you want to trade in units of the base currency
price 	float 	No 	the price at which the order is to be fulfilled, in units of the quote currency, ignored in market orders
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.clientOrderId 	string 	No 	client order id, uses id if not passed
params.stopLossPrice 	float 	No 	stop loss trigger price
params.newSlOrdPx 	float 	No 	the stop loss order price, set to stopLossPrice if the type is market
params.newSlTriggerPxType 	string 	No 	'last', 'index' or 'mark' used to specify the stop loss trigger price type, default is 'last'
params.takeProfitPrice 	float 	No 	take profit trigger price
params.newTpOrdPx 	float 	No 	the take profit order price, set to takeProfitPrice if the type is market
params.newTpTriggerPxType 	string 	No 	'last', 'index' or 'mark' used to specify the take profit trigger price type, default is 'last'
params.stopLoss 	object 	No 	stopLoss object in params containing the triggerPrice at which the attached stop loss order will be triggered
params.stopLoss.triggerPrice 	float 	No 	stop loss trigger price
params.stopLoss.price 	float 	No 	used for stop loss limit orders, not used for stop loss market price orders
params.stopLoss.type 	string 	No 	'market' or 'limit' used to specify the stop loss price type
params.takeProfit 	object 	No 	takeProfit object in params containing the triggerPrice at which the attached take profit order will be triggered
params.takeProfit.triggerPrice 	float 	No 	take profit trigger price
params.takeProfit.price 	float 	No 	used for take profit limit orders, not used for take profit market price orders
params.takeProfit.type 	string 	No 	'market' or 'limit' used to specify the take profit price type
params.newTpOrdKind 	string 	No 	'condition' or 'limit', the default is 'condition'

okx.editOrder (id, symbol, type, side, amount[, price, params])

cancelOrder

cancels an open order

Kind: instance method of okx
Returns: object - An order structure

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-order
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-post-cancel-algo-order

Param 	Type 	Required 	Description
id 	string 	Yes 	order id
symbol 	string 	Yes 	unified symbol of the market the order was made in
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	boolean 	No 	true if trigger orders
params.trailing 	boolean 	No 	set to true if you want to cancel a trailing order

okx.cancelOrder (id, symbol[, params])

cancelOrders

cancel multiple orders

Kind: instance method of okx
Returns: object - an list of order structures

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-multiple-orders
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-post-cancel-algo-order

Param 	Type 	Required 	Description
ids 	Array<string> 	Yes 	order ids
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	boolean 	No 	whether the order is a stop/trigger order
params.trailing 	boolean 	No 	set to true if you want to cancel trailing orders

okx.cancelOrders (ids, symbol[, params])

cancelOrdersForSymbols

cancel multiple orders for multiple symbols

Kind: instance method of okx
Returns: object - an list of order structures

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-multiple-orders
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-post-cancel-algo-order

Param 	Type 	Required 	Description
orders 	Array<CancellationRequest> 	Yes 	each order should contain the parameters required by cancelOrder namely id and symbol, example [{"id": "a", "symbol": "BTC/USDT"}, {"id": "b", "symbol": "ETH/USDT"}]
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	boolean 	No 	whether the order is a stop/trigger order
params.trailing 	boolean 	No 	set to true if you want to cancel trailing orders

okx.cancelOrdersForSymbols (orders[, params])

cancelAllOrdersAfter

dead man's switch, cancel all orders after the given timeout

Kind: instance method of okx
Returns: object - the api result

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-all-after
Param 	Type 	Required 	Description
timeout 	number 	Yes 	time in milliseconds, 0 represents cancel the timer
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.cancelAllOrdersAfter (timeout[, params])

fetchOrder

fetch an order by the id

Kind: instance method of okx
Returns: an order structure

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-details
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-get-algo-order-details

Param 	Type 	Required 	Description
id 	string 	Yes 	the order id
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra and exchange specific parameters
params.trigger 	boolean 	No 	true if fetching trigger orders

okx.fetchOrder (id, symbol[, params])

fetchOpenOrders

fetch all unfilled currently open orders

Kind: instance method of okx
Returns: Array<Order> - a list of order structures

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-list
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-get-algo-order-list

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
since 	int 	No 	the earliest time in ms to fetch open orders for
limit 	int 	No 	the maximum number of open orders structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	bool 	No 	True if fetching trigger or conditional orders
params.ordType 	string 	No 	"conditional", "oco", "trigger", "move_order_stop", "iceberg", or "twap"
params.algoId 	string 	No 	Algo ID "'433845797218942976'"
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters
params.trailing 	boolean 	No 	set to true if you want to fetch trailing orders

okx.fetchOpenOrders (symbol[, since, limit, params])

fetchCanceledOrders

fetches information on multiple canceled orders made by the user

Kind: instance method of okx
Returns: object - a list of order structures

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-7-days
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-get-algo-order-history

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol of the market orders were made in
since 	int 	No 	timestamp in ms of the earliest order, default is undefined
limit 	int 	No 	max number of orders to return, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	bool 	No 	True if fetching trigger or conditional orders
params.ordType 	string 	No 	"conditional", "oco", "trigger", "move_order_stop", "iceberg", or "twap"
params.algoId 	string 	No 	Algo ID "'433845797218942976'"
params.until 	int 	No 	timestamp in ms to fetch orders for
params.trailing 	boolean 	No 	set to true if you want to fetch trailing orders

okx.fetchCanceledOrders (symbol[, since, limit, params])

fetchClosedOrders

fetches information on multiple closed orders made by the user

Kind: instance method of okx
Returns: Array<Order> - a list of order structures

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-7-days
    https://www.okx.com/docs-v5/en/#order-book-trading-algo-trading-get-algo-order-history
    https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-3-months

Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol of the market orders were made in
since 	int 	No 	the earliest time in ms to fetch orders for
limit 	int 	No 	the maximum number of order structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	bool 	No 	True if fetching trigger or conditional orders
params.ordType 	string 	No 	"conditional", "oco", "trigger", "move_order_stop", "iceberg", or "twap"
params.algoId 	string 	No 	Algo ID "'433845797218942976'"
params.until 	int 	No 	timestamp in ms to fetch orders for
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters
params.method 	string 	No 	method to be used, either 'privateGetTradeOrdersHistory', 'privateGetTradeOrdersHistoryArchive' or 'privateGetTradeOrdersAlgoHistory' default is 'privateGetTradeOrdersHistory'
params.trailing 	boolean 	No 	set to true if you want to fetch trailing orders

okx.fetchClosedOrders (symbol[, since, limit, params])

fetchMyTrades

fetch all trades made by the user

Kind: instance method of okx
Returns: Array<Trade> - a list of trade structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-months
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
since 	int 	No 	the earliest time in ms to fetch trades for
limit 	int 	No 	the maximum number of trades structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.until 	int 	No 	Timestamp in ms of the latest time to retrieve trades for
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters

okx.fetchMyTrades (symbol[, since, limit, params])

fetchOrderTrades

fetch all the trades made from a single order

Kind: instance method of okx
Returns: Array<object> - a list of trade structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-months
Param 	Type 	Required 	Description
id 	string 	Yes 	order id
symbol 	string 	Yes 	unified market symbol
since 	int 	No 	the earliest time in ms to fetch trades for
limit 	int 	No 	the maximum number of trades to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchOrderTrades (id, symbol[, since, limit, params])

fetchLedger

fetch the history of changes, actions done by the user or operations that altered balance of the user

Kind: instance method of okx
Returns: object - a ledger structure

See

    https://www.okx.com/docs-v5/en/#rest-api-account-get-bills-details-last-7-days
    https://www.okx.com/docs-v5/en/#rest-api-account-get-bills-details-last-3-months
    https://www.okx.com/docs-v5/en/#rest-api-funding-asset-bills-details

Param 	Type 	Required 	Description
code 	string 	No 	unified currency code, default is undefined
since 	int 	No 	timestamp in ms of the earliest ledger entry, default is undefined
limit 	int 	No 	max number of ledger entries to return, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.marginMode 	string 	No 	'cross' or 'isolated'
params.until 	int 	No 	the latest time in ms to fetch entries for
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the available parameters

okx.fetchLedger ([code, since, limit, params])

fetchDepositAddressesByNetwork

fetch a dictionary of addresses for a currency, indexed by network

Kind: instance method of okx
Returns: object - a dictionary of address structures indexed by the network

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-address
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code of the currency for the deposit address
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchDepositAddressesByNetwork (code[, params])

fetchDepositAddress

fetch the deposit address for a currency associated with this account

Kind: instance method of okx
Returns: object - an address structure

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-address
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.network 	string 	No 	the network name for the deposit address

okx.fetchDepositAddress (code[, params])

withdraw

make a withdrawal

Kind: instance method of okx
Returns: object - a transaction structure

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-withdrawal
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
amount 	float 	Yes 	the amount to withdraw
address 	string 	Yes 	the address to withdraw to
tag 	string 	Yes 	
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.withdraw (code, amount, address, tag[, params])

fetchDeposits

fetch all deposits made to an account

Kind: instance method of okx
Returns: Array<object> - a list of transaction structures

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-deposit-history
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
since 	int 	No 	the earliest time in ms to fetch deposits for
limit 	int 	No 	the maximum number of deposits structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.until 	int 	No 	the latest time in ms to fetch entries for
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters

okx.fetchDeposits (code[, since, limit, params])

fetchDeposit

fetch data on a currency deposit via the deposit id

Kind: instance method of okx
Returns: object - a transaction structure

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-deposit-history
Param 	Type 	Required 	Description
id 	string 	Yes 	deposit id
code 	string 	Yes 	filter by currency code
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchDeposit (id, code[, params])

fetchWithdrawals

fetch all withdrawals made from an account

Kind: instance method of okx
Returns: Array<object> - a list of transaction structures

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-withdrawal-history
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
since 	int 	No 	the earliest time in ms to fetch withdrawals for
limit 	int 	No 	the maximum number of withdrawals structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.until 	int 	No 	the latest time in ms to fetch entries for
params.paginate 	boolean 	No 	default false, when true will automatically paginate by calling this endpoint multiple times. See in the docs all the availble parameters

okx.fetchWithdrawals (code[, since, limit, params])

fetchWithdrawal

fetch data on a currency withdrawal via the withdrawal id

Kind: instance method of okx
Returns: object - a transaction structure

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-withdrawal-history
Param 	Type 	Required 	Description
id 	string 	Yes 	withdrawal id
code 	string 	Yes 	unified currency code of the currency withdrawn, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchWithdrawal (id, code[, params])

fetchLeverage

fetch the set leverage for a market

Kind: instance method of okx
Returns: object - a leverage structure

See: https://www.okx.com/docs-v5/en/#rest-api-account-get-leverage
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.marginMode 	string 	No 	'cross' or 'isolated'

okx.fetchLeverage (symbol[, params])

fetchPosition

fetch data on a single open contract trade position

Kind: instance method of okx
Returns: object - a position structure

See: https://www.okx.com/docs-v5/en/#rest-api-account-get-positions
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol of the market the position is held in, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.instType 	string 	No 	MARGIN, SWAP, FUTURES, OPTION

okx.fetchPosition (symbol[, params])

fetchPositions

fetch all open positions

Kind: instance method of okx
Returns: Array<object> - a list of position structure

See

    https://www.okx.com/docs-v5/en/#rest-api-account-get-positions
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions-history history

Param 	Type 	Required 	Description
symbols 	Array<string>, undefined 	Yes 	list of unified market symbols
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.instType 	string 	No 	MARGIN, SWAP, FUTURES, OPTION

okx.fetchPositions (symbols[, params])

fetchPositionsForSymbol

fetch all open positions for specific symbol

Kind: instance method of okx
Returns: Array<object> - a list of position structure

See: https://www.okx.com/docs-v5/en/#rest-api-account-get-positions
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.instType 	string 	No 	MARGIN (if needed)

okx.fetchPositionsForSymbol (symbol[, params])

transfer

transfer currency internally between wallets on the same account

Kind: instance method of okx
Returns: object - a transfer structure

See: https://www.okx.com/docs-v5/en/#rest-api-funding-funds-transfer
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
amount 	float 	Yes 	amount to transfer
fromAccount 	string 	Yes 	account to transfer from
toAccount 	string 	Yes 	account to transfer to
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.transfer (code, amount, fromAccount, toAccount[, params])

fetchTransfers

fetch a history of internal transfers made on an account

Kind: instance method of okx
Returns: Array<object> - a list of transfer structures

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-bills-details-last-3-months
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code of the currency transferred
since 	int 	No 	the earliest time in ms to fetch transfers for
limit 	int 	No 	the maximum number of transfers structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchTransfers (code[, since, limit, params])

fetchFundingInterval

fetch the current funding rate interval

Kind: instance method of okx
Returns: object - a funding rate structure

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchFundingInterval (symbol[, params])

fetchFundingRate

fetch the current funding rate

Kind: instance method of okx
Returns: object - a funding rate structure

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchFundingRate (symbol[, params])

fetchFundingHistory

fetch the history of funding payments paid and received on this account

Kind: instance method of okx
Returns: object - a funding history structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-bills-details-last-3-months
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
since 	int 	No 	the earliest time in ms to fetch funding history for
limit 	int 	No 	the maximum number of funding history structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchFundingHistory (symbol[, since, limit, params])

setLeverage

set the level of leverage for a market

Kind: instance method of okx
Returns: object - response from the exchange

See: https://www.okx.com/docs-v5/en/#rest-api-account-set-leverage
Param 	Type 	Required 	Description
leverage 	float 	Yes 	the rate of leverage
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.marginMode 	string 	No 	'cross' or 'isolated'
params.posSide 	string 	No 	'long' or 'short' or 'net' for isolated margin long/short mode on futures and swap markets, default is 'net'

okx.setLeverage (leverage, symbol[, params])

fetchPositionMode

fetchs the position mode, hedged or one way, hedged for binance is set identically for all linear markets or all inverse markets

Kind: instance method of okx
Returns: object - an object detailing whether the market is in hedged or one-way mode

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the order book for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.accountId 	string 	No 	if you have multiple accounts, you must specify the account id to fetch the position mode

okx.fetchPositionMode (symbol[, params])

setPositionMode

set hedged to true or false for a market

Kind: instance method of okx
Returns: object - response from the exchange

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-set-position-mode
Param 	Type 	Required 	Description
hedged 	bool 	Yes 	set to true to use long_short_mode, false for net_mode
symbol 	string 	Yes 	not used by okx setPositionMode
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.setPositionMode (hedged, symbol[, params])

setMarginMode

set margin mode to 'cross' or 'isolated'

Kind: instance method of okx
Returns: object - response from the exchange

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-set-leverage
Param 	Type 	Required 	Description
marginMode 	string 	Yes 	'cross' or 'isolated'
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.leverage 	int 	No 	leverage

okx.setMarginMode (marginMode, symbol[, params])

fetchCrossBorrowRates

fetch the borrow interest rates of all currencies

Kind: instance method of okx
Returns: object - a list of borrow rate structures

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-interest-rate
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchCrossBorrowRates ([params])

fetchCrossBorrowRate

fetch the rate of interest to borrow a currency for margin trading

Kind: instance method of okx
Returns: object - a borrow rate structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-interest-rate
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchCrossBorrowRate (code[, params])

fetchBorrowRateHistories

retrieves a history of a multiple currencies borrow interest rate at specific time slots, returns all currencies if no symbols passed, default is undefined

Kind: instance method of okx
Returns: object - a dictionary of borrow rate structures indexed by the market symbol

See: https://www.okx.com/docs-v5/en/#financial-product-savings-get-public-borrow-history-public
Param 	Type 	Required 	Description
codes 	Array<string>, undefined 	Yes 	list of unified currency codes, default is undefined
since 	int 	No 	timestamp in ms of the earliest borrowRate, default is undefined
limit 	int 	No 	max number of borrow rate prices to return, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchBorrowRateHistories (codes[, since, limit, params])

fetchBorrowRateHistory

retrieves a history of a currencies borrow interest rate at specific time slots

Kind: instance method of okx
Returns: Array<object> - an array of borrow rate structures

See: https://www.okx.com/docs-v5/en/#financial-product-savings-get-public-borrow-history-public
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code
since 	int 	No 	timestamp for the earliest borrow rate
limit 	int 	No 	the maximum number of borrow rate structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchBorrowRateHistory (code[, since, limit, params])

reduceMargin

remove margin from a position

Kind: instance method of okx
Returns: object - a margin structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-increase-decrease-margin
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
amount 	float 	Yes 	the amount of margin to remove
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.reduceMargin (symbol, amount[, params])

addMargin

add margin

Kind: instance method of okx
Returns: object - a margin structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-increase-decrease-margin
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
amount 	float 	Yes 	amount of margin to add
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.addMargin (symbol, amount[, params])

fetchMarketLeverageTiers

retrieve information on the maximum leverage, and maintenance margin for trades of varying trade sizes for a single market

Kind: instance method of okx
Returns: object - a leverage tiers structure

See: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-position-tiers
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.marginMode 	string 	No 	'cross' or 'isolated'

okx.fetchMarketLeverageTiers (symbol[, params])

fetchBorrowInterest

fetch the interest owed by the user for borrowing currency for margin trading

Kind: instance method of okx
Returns: Array<object> - An list of borrow interest structures

See: https://www.okx.com/docs-v5/en/#rest-api-account-get-interest-accrued-data
Param 	Type 	Required 	Description
code 	string 	Yes 	the unified currency code for the currency of the interest
symbol 	string 	Yes 	the market symbol of an isolated margin market, if undefined, the interest for cross margin markets is returned
since 	int 	No 	timestamp in ms of the earliest time to receive interest records for
limit 	int 	No 	the number of borrow interest structures to retrieve
params 	object 	No 	exchange specific parameters
params.type 	int 	No 	Loan type 1 - VIP loans 2 - Market loans Default is Market loans
params.marginMode 	string 	No 	'cross' or 'isolated'

okx.fetchBorrowInterest (code, symbol[, since, limit, params])

borrowCrossMargin

create a loan to borrow margin (need to be VIP 5 and above)

Kind: instance method of okx
Returns: object - a margin loan structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-vip-loans-borrow-and-repay
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code of the currency to borrow
amount 	float 	Yes 	the amount to borrow
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.borrowCrossMargin (code, amount[, params])

repayCrossMargin

repay borrowed margin and interest

Kind: instance method of okx
Returns: object - a margin loan structure

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-vip-loans-borrow-and-repay
Param 	Type 	Required 	Description
code 	string 	Yes 	unified currency code of the currency to repay
amount 	float 	Yes 	the amount to repay
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.id 	string 	No 	the order ID of borrowing, it is necessary while repaying

okx.repayCrossMargin (code, amount[, params])

fetchOpenInterest

Retrieves the open interest of a currency

Kind: instance method of okx
Returns: object - an open interest structurehttps://docs.ccxt.com/#/?id=open-interest-structure

See: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-open-interest
Param 	Type 	Required 	Description
symbol 	string 	Yes 	Unified CCXT market symbol
params 	object 	No 	exchange specific parameters

okx.fetchOpenInterest (symbol[, params])

fetchOpenInterestHistory

Retrieves the open interest history of a currency

Kind: instance method of okx
Returns: An array of open interest structures

See

    https://www.okx.com/docs-v5/en/#rest-api-trading-data-get-contracts-open-interest-and-volume
    https://www.okx.com/docs-v5/en/#rest-api-trading-data-get-options-open-interest-and-volume

Param 	Type 	Required 	Description
symbol 	string 	Yes 	Unified CCXT currency code or unified symbol
timeframe 	string 	Yes 	"5m", "1h", or "1d" for option only "1d" or "8h"
since 	int 	No 	The time in ms of the earliest record to retrieve as a unix timestamp
limit 	int 	No 	Not used by okx, but parsed internally by CCXT
params 	object 	No 	Exchange specific parameters
params.until 	int 	No 	The time in ms of the latest record to retrieve as a unix timestamp

okx.fetchOpenInterestHistory (symbol, timeframe[, since, limit, params])

fetchDepositWithdrawFees

fetch deposit and withdraw fees

Kind: instance method of okx
Returns: Array<object> - a list of fees structures

See: https://www.okx.com/docs-v5/en/#rest-api-funding-get-currencies
Param 	Type 	Required 	Description
codes 	Array<string>, undefined 	Yes 	list of unified currency codes
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchDepositWithdrawFees (codes[, params])

fetchSettlementHistory

fetches historical settlement records

Kind: instance method of okx
Returns: Array<object> - a list of settlement history objects

See: https://www.okx.com/docs-v5/en/#rest-api-public-data-get-delivery-exercise-history
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol to fetch the settlement history for
since 	int 	No 	timestamp in ms
limit 	int 	No 	number of records
params 	object 	No 	exchange specific params

okx.fetchSettlementHistory (symbol[, since, limit, params])

fetchUnderlyingAssets

fetches the market ids of underlying assets for a specific contract market type

Kind: instance method of okx
Returns: Array<object> - a list of underlying assets

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-underlying
Param 	Type 	Required 	Description
params 	object 	No 	exchange specific params
params.type 	string 	No 	the contract market type, 'option', 'swap' or 'future', the default is 'option'

okx.fetchUnderlyingAssets ([params])

fetchGreeks

fetches an option contracts greeks, financial metrics used to measure the factors that affect the price of an options contract

Kind: instance method of okx
Returns: object - a greeks structure

See: https://www.okx.com/docs-v5/en/#public-data-rest-api-get-option-market-data
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch greeks for
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchGreeks (symbol[, params])

closePosition

closes open positions for a market

Kind: instance method of okx
Returns: Array<object> - A list of position structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-close-positions
Param 	Type 	Required 	Description
symbol 	string 	Yes 	Unified CCXT market symbol
side 	string 	No 	'buy' or 'sell', leave as undefined in net mode
params 	object 	No 	extra parameters specific to the okx api endpoint
params.clientOrderId 	string 	No 	a unique identifier for the order
params.marginMode 	string 	No 	'cross' or 'isolated', default is 'cross;
params.code 	string 	No 	required in the case of closing cross MARGIN position for Single-currency margin margin currency EXCHANGE SPECIFIC PARAMETERS
params.autoCxl 	boolean 	No 	whether any pending orders for closing out needs to be automatically canceled when close position via a market order. false or true, the default is false
params.tag 	string 	No 	order tag a combination of case-sensitive alphanumerics, all numbers, or all letters of up to 16 characters

okx.closePosition (symbol[, side, params])

fetchOption

fetches option data that is commonly found in an option chain

Kind: instance method of okx
Returns: object - an option chain structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-ticker
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchOption (symbol[, params])

fetchOptionChain

fetches data for an underlying asset that is commonly found in an option chain

Kind: instance method of okx
Returns: object - a list of option chain structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-tickers
Param 	Type 	Required 	Description
code 	string 	Yes 	base currency to fetch an option chain for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.uly 	string 	No 	the underlying asset, can be obtained from fetchUnderlyingAssets ()

okx.fetchOptionChain (code[, params])

fetchConvertQuote

fetch a quote for converting from one currency to another

Kind: instance method of okx
Returns: object - a conversion structure

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-estimate-quote
Param 	Type 	Required 	Description
fromCode 	string 	Yes 	the currency that you want to sell and convert from
toCode 	string 	Yes 	the currency that you want to buy and convert into
amount 	float 	No 	how much you want to trade in units of the from currency
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchConvertQuote (fromCode, toCode[, amount, params])

createConvertTrade

convert from one currency to another

Kind: instance method of okx
Returns: object - a conversion structure

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-convert-trade
Param 	Type 	Required 	Description
id 	string 	Yes 	the id of the trade that you want to make
fromCode 	string 	Yes 	the currency that you want to sell and convert from
toCode 	string 	Yes 	the currency that you want to buy and convert into
amount 	float 	No 	how much you want to trade in units of the from currency
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.createConvertTrade (id, fromCode, toCode[, amount, params])

fetchConvertTrade

fetch the data for a conversion trade

Kind: instance method of okx
Returns: object - a conversion structure

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-convert-history
Param 	Type 	Required 	Description
id 	string 	Yes 	the id of the trade that you want to fetch
code 	string 	No 	the unified currency code of the conversion trade
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchConvertTrade (id[, code, params])

fetchConvertTradeHistory

fetch the users history of conversion trades

Kind: instance method of okx
Returns: Array<object> - a list of conversion structures

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-convert-history
Param 	Type 	Required 	Description
code 	string 	No 	the unified currency code
since 	int 	No 	the earliest time in ms to fetch conversions for
limit 	int 	No 	the maximum number of conversion structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.until 	int 	No 	timestamp in ms of the latest conversion to fetch

okx.fetchConvertTradeHistory ([code, since, limit, params])

fetchConvertCurrencies

fetches all available currencies that can be converted

Kind: instance method of okx
Returns: object - an associative dictionary of currencies

See: https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-convert-currencies
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.fetchConvertCurrencies ([params])

fetchMarginAdjustmentHistory

fetches the history of margin added or reduced from contract isolated positions

Kind: instance method of okx
Returns: Array<object> - a list of margin structures

See

    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-bills-details-last-7-days
    https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-bills-details-last-3-months

Param 	Type 	Required 	Description
symbol 	string 	No 	not used by okx fetchMarginAdjustmentHistory
type 	string 	No 	"add" or "reduce"
since 	int 	No 	the earliest time in ms to fetch margin adjustment history for
limit 	int 	No 	the maximum number of entries to retrieve
params 	object 	Yes 	extra parameters specific to the exchange api endpoint
params.auto 	boolean 	No 	true if fetching auto margin increases

okx.fetchMarginAdjustmentHistory ([symbol, type, since, limit, params])

fetchPositionsHistory

fetches historical positions

Kind: instance method of okx
Returns: Array<object> - a list of position structures

See: https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions-history
Param 	Type 	Required 	Description
symbols 	string 	No 	unified market symbols
since 	int 	No 	timestamp in ms of the earliest position to fetch
limit 	int 	No 	the maximum amount of records to fetch, default=100, max=100
params 	object 	Yes 	extra parameters specific to the exchange api endpoint
params.marginMode 	string 	No 	"cross" or "isolated" EXCHANGE SPECIFIC PARAMETERS
params.instType 	string 	No 	margin, swap, futures or option
params.type 	string 	No 	the type of latest close position 1: close position partially, 2：close all, 3：liquidation, 4：partial liquidation; 5：adl, is it is the latest type if there are several types for the same position
params.posId 	string 	No 	position id, there is attribute expiration, the posid will be expired if it is more than 30 days after the last full close position, then position will use new posid
params.before 	string 	No 	timestamp in ms of the earliest position to fetch based on the last update time of the position
params.after 	string 	No 	timestamp in ms of the latest position to fetch based on the last update time of the position

okx.fetchPositionsHistory ([symbols, since, limit, params])

fetchLongShortRatioHistory

fetches the long short ratio history for a unified market symbol

Kind: instance method of okx
Returns: Array<object> - an array of long short ratio structures

See: https://www.okx.com/docs-v5/en/#trading-statistics-rest-api-get-contract-long-short-ratio
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the long short ratio for
timeframe 	string 	No 	the period for the ratio
since 	int 	No 	the earliest time in ms to fetch ratios for
limit 	int 	No 	the maximum number of long short ratio structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.until 	int 	No 	timestamp in ms of the latest ratio to fetch

okx.fetchLongShortRatioHistory (symbol[, timeframe, since, limit, params])

watchTrades

get the list of most recent trades for a particular symbol

Kind: instance method of okx
Returns: Array<object> - a list of trade structures
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch trades for
since 	int 	No 	timestamp in ms of the earliest trade to fetch
limit 	int 	No 	the maximum amount of trades to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchTrades (symbol[, since, limit, params])

watchTradesForSymbols

get the list of most recent trades for a particular symbol

Kind: instance method of okx
Returns: Array<object> - a list of trade structures
Param 	Type 	Required 	Description
symbols 	string 	Yes 	
since 	int 	No 	timestamp in ms of the earliest trade to fetch
limit 	int 	No 	the maximum amount of trades to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchTradesForSymbols (symbols[, since, limit, params])

unWatchTradesForSymbols

unWatches from the stream channel

Kind: instance method of okx
Returns: Array<object> - a list of trade structures
Param 	Type 	Required 	Description
symbols 	Array<string> 	Yes 	
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.unWatchTradesForSymbols (symbols[, params])

unWatchTrades

unWatches from the stream channel

Kind: instance method of okx
Returns: Array<object> - a list of trade structures
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch trades for
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.unWatchTrades (symbol[, params])

watchFundingRate

watch the current funding rate

Kind: instance method of okx
Returns: object - a funding rate structure

See: https://www.okx.com/docs-v5/en/#public-data-websocket-funding-rate-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchFundingRate (symbol[, params])

watchTicker

watches a price ticker, a statistical calculation with the information calculated over the past 24 hours for a specific market

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.watchTicker (symbol[, params])

unWatchTicker

unWatches a price ticker, a statistical calculation with the information calculated over the past 24 hours for a specific market

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.unWatchTicker (symbol[, params])

watchTickers

watches a price ticker, a statistical calculation with the information calculated over the past 24 hours for all markets of a specific list

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	No 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.watchTickers ([symbols, params])

watchMarkPrice

watches a mark price

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#public-data-websocket-mark-price-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.watchMarkPrice (symbol[, params])

watchMarkPrices

watches mark prices

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#public-data-websocket-mark-price-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	No 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.watchMarkPrices ([symbols, params])

unWatchTickers

unWatches a price ticker, a statistical calculation with the information calculated over the past 24 hours for all markets of a specific list

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	No 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.channel 	string 	No 	the channel to subscribe to, tickers by default. Can be tickers, sprd-tickers, index-tickers, block-tickers

okx.unWatchTickers ([symbols, params])

watchBidsAsks

watches best bid & ask for symbols

Kind: instance method of okx
Returns: object - a ticker structure

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-tickers-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	Yes 	unified symbol of the market to fetch the ticker for
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchBidsAsks (symbols[, params])

watchLiquidationsForSymbols

watch the public liquidations of a trading pair

Kind: instance method of okx
Returns: object - an array of liquidation structures

See: https://www.okx.com/docs-v5/en/#public-data-websocket-liquidation-orders-channel
Param 	Type 	Required 	Description
symbols 	string 	Yes 	
since 	int 	No 	the earliest time in ms to fetch liquidations for
limit 	int 	No 	the maximum number of liquidation structures to retrieve
params 	object 	No 	exchange specific parameters for the okx api endpoint

okx.watchLiquidationsForSymbols (symbols[, since, limit, params])

watchMyLiquidationsForSymbols

watch the private liquidations of a trading pair

Kind: instance method of okx
Returns: object - an array of liquidation structures

See: https://www.okx.com/docs-v5/en/#trading-account-websocket-balance-and-position-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	Yes 	
since 	int 	No 	the earliest time in ms to fetch liquidations for
limit 	int 	No 	the maximum number of liquidation structures to retrieve
params 	object 	No 	exchange specific parameters for the okx api endpoint

okx.watchMyLiquidationsForSymbols (symbols[, since, limit, params])

watchOHLCV

watches historical candlestick data containing the open, high, low, and close price, and the volume of a market

Kind: instance method of okx
Returns: Array<Array<int>> - A list of candles ordered as timestamp, open, high, low, close, volume
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch OHLCV data for
timeframe 	string 	Yes 	the length of time each candle represents
since 	int 	No 	timestamp in ms of the earliest candle to fetch
limit 	int 	No 	the maximum amount of candles to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchOHLCV (symbol, timeframe[, since, limit, params])

unWatchOHLCV

watches historical candlestick data containing the open, high, low, and close price, and the volume of a market

Kind: instance method of okx
Returns: Array<Array<int>> - A list of candles ordered as timestamp, open, high, low, close, volume
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch OHLCV data for
timeframe 	string 	Yes 	the length of time each candle represents
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.unWatchOHLCV (symbol, timeframe[, params])

watchOHLCVForSymbols

watches historical candlestick data containing the open, high, low, and close price, and the volume of a market

Kind: instance method of okx
Returns: Array<Array<int>> - A list of candles ordered as timestamp, open, high, low, close, volume
Param 	Type 	Required 	Description
symbolsAndTimeframes 	Array<Array<string>> 	Yes 	array of arrays containing unified symbols and timeframes to fetch OHLCV data for, example [['BTC/USDT', '1m'], ['LTC/USDT', '5m']]
since 	int 	No 	timestamp in ms of the earliest candle to fetch
limit 	int 	No 	the maximum amount of candles to fetch
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchOHLCVForSymbols (symbolsAndTimeframes[, since, limit, params])

unWatchOHLCVForSymbols

unWatches historical candlestick data containing the open, high, low, and close price, and the volume of a market

Kind: instance method of okx
Returns: Array<Array<int>> - A list of candles ordered as timestamp, open, high, low, close, volume
Param 	Type 	Required 	Description
symbolsAndTimeframes 	Array<Array<string>> 	Yes 	array of arrays containing unified symbols and timeframes to fetch OHLCV data for, example [['BTC/USDT', '1m'], ['LTC/USDT', '5m']]
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.unWatchOHLCVForSymbols (symbolsAndTimeframes[, params])

watchOrderBook

watches information on open orders with bid (buy) and ask (sell) prices, volumes and other data

Kind: instance method of okx
Returns: object - A dictionary of order book structures indexed by market symbols

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to fetch the order book for
limit 	int 	No 	the maximum amount of order book entries to return
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.depth 	string 	No 	okx order book depth, can be books, books5, books-l2-tbt, books50-l2-tbt, bbo-tbt

okx.watchOrderBook (symbol[, limit, params])

watchOrderBookForSymbols

watches information on open orders with bid (buy) and ask (sell) prices, volumes and other data

Kind: instance method of okx
Returns: object - A dictionary of order book structures indexed by market symbols

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	Yes 	unified array of symbols
limit 	int 	No 	1,5, 400, 50 (l2-tbt, vip4+) or 40000 (vip5+) the maximum amount of order book entries to return
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.depth 	string 	No 	okx order book depth, can be books, books5, books-l2-tbt, books50-l2-tbt, bbo-tbt

okx.watchOrderBookForSymbols (symbols[, limit, params])

unWatchOrderBookForSymbols

unWatches information on open orders with bid (buy) and ask (sell) prices, volumes and other data

Kind: instance method of okx
Returns: object - A dictionary of order book structures indexed by market symbols

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
Param 	Type 	Required 	Description
symbols 	Array<string> 	Yes 	unified array of symbols
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.limit 	int 	No 	the maximum amount of order book entries to return
params.depth 	string 	No 	okx order book depth, can be books, books5, books-l2-tbt, books50-l2-tbt, bbo-tbt

okx.unWatchOrderBookForSymbols (symbols[, params])

unWatchOrderBook

unWatches information on open orders with bid (buy) and ask (sell) prices, volumes and other data

Kind: instance method of okx
Returns: object - A dictionary of order book structures indexed by market symbols

See: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified array of symbols
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.limit 	int 	No 	the maximum amount of order book entries to return
params.depth 	string 	No 	okx order book depth, can be books, books5, books-l2-tbt, books50-l2-tbt, bbo-tbt

okx.unWatchOrderBook (symbol[, params])

watchBalance

watch balance and get the amount of funds available for trading or funds locked in orders

Kind: instance method of okx
Returns: object - a balance structure
Param 	Type 	Required 	Description
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.watchBalance ([params])

watchMyTrades

watches information on multiple trades made by the user

Kind: instance method of okx
Returns: Array<object> - a list of trade structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-order-channel
Param 	Type 	Required 	Description
symbol 	string 	No 	unified market symbol of the market trades were made in
since 	int 	No 	the earliest time in ms to fetch trades for
limit 	int 	No 	the maximum number of trade structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	bool 	No 	true if fetching trigger or conditional trades
params.type 	string 	No 	'spot', 'swap', 'future', 'option', 'ANY', 'SPOT', 'MARGIN', 'SWAP', 'FUTURES' or 'OPTION'
params.marginMode 	string 	No 	'cross' or 'isolated', for automatically setting the type to spot margin

okx.watchMyTrades ([symbol, since, limit, params])

watchPositions

watch all open positions

Kind: instance method of okx
Returns: Array<object> - a list of position structure

See: https://www.okx.com/docs-v5/en/#trading-account-websocket-positions-channel
Param 	Type 	Description
symbols 	Array<string>, undefined 	list of unified market symbols
since 		
limit 		
params 	object 	extra parameters specific to the exchange API endpoint

okx.watchPositions (symbols, since, limit, params[])

watchOrders

watches information on multiple orders made by the user

Kind: instance method of okx
Returns: Array<object> - a list of order structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-order-channel
Param 	Type 	Required 	Description
symbol 	string 	No 	unified market symbol of the market the orders were made in
since 	int 	No 	the earliest time in ms to fetch orders for
limit 	int 	No 	the maximum number of order structures to retrieve
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.trigger 	bool 	No 	true if fetching trigger or conditional orders
params.type 	string 	No 	'spot', 'swap', 'future', 'option', 'ANY', 'SPOT', 'MARGIN', 'SWAP', 'FUTURES' or 'OPTION'
params.marginMode 	string 	No 	'cross' or 'isolated', for automatically setting the type to spot margin

okx.watchOrders ([symbol, since, limit, params])

createOrderWs

create a trade order

Kind: instance method of okx
Returns: object - an order structure

See: https://www.okx.com/docs-v5/en/#websocket-api-trade-place-order
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified symbol of the market to create an order in
type 	string 	Yes 	'market' or 'limit'
side 	string 	Yes 	'buy' or 'sell'
amount 	float 	Yes 	how much of currency you want to trade in units of base currency
price 	float, undefined 	No 	the price at which the order is to be fulfilled, in units of the quote currency, ignored in market orders
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.test 	boolean 	Yes 	test order, default false

okx.createOrderWs (symbol, type, side, amount[, price, params])

editOrderWs

edit a trade order

Kind: instance method of okx
Returns: object - an order structure

See

    https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-amend-order
    https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-amend-multiple-orders

Param 	Type 	Required 	Description
id 	string 	Yes 	order id
symbol 	string 	Yes 	unified symbol of the market to create an order in
type 	string 	Yes 	'market' or 'limit'
side 	string 	Yes 	'buy' or 'sell'
amount 	float 	Yes 	how much of the currency you want to trade in units of the base currency
price 	float, undefined 	No 	the price at which the order is to be fulfilled, in units of the quote currency, ignored in market orders
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.editOrderWs (id, symbol, type, side, amount[, price, params])

cancelOrderWs

cancel multiple orders

Kind: instance method of okx
Returns: object - an list of order structures

See: https://okx-docs.github.io/apidocs/websocket_api/en/#cancel-order-trade
Param 	Type 	Required 	Description
id 	string 	Yes 	order id
symbol 	string 	Yes 	unified market symbol, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint
params.clOrdId 	string 	No 	client order id

okx.cancelOrderWs (id, symbol[, params])

cancelOrdersWs

cancel multiple orders

Kind: instance method of okx
Returns: object - an list of order structures

See: https://www.okx.com/docs-v5/en/#order-book-trading-trade-ws-mass-cancel-order
Param 	Type 	Required 	Description
ids 	Array<string> 	Yes 	order ids
symbol 	string 	Yes 	unified market symbol, default is undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.cancelOrdersWs (ids, symbol[, params])

cancelAllOrdersWs

cancel all open orders of a type. Only applicable to Option in Portfolio Margin mode, and MMP privilege is required.

Kind: instance method of okx
Returns: Array<object> - a list of order structures

See: https://docs.okx.com/websockets/#message-cancelAll
Param 	Type 	Required 	Description
symbol 	string 	Yes 	unified market symbol, only orders in the market of this symbol are cancelled when symbol is not undefined
params 	object 	No 	extra parameters specific to the exchange API endpoint

okx.cancelAllOrdersWs (symbol[, params])