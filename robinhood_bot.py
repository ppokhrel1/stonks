
import random
import time

excludes = ['AEM']

to_close = ['PLTR', 'NPA']
#symbol, strike, expiry, quantity
to_open = [ ('BOX', '20.0', "2021-04-16", 1 ),
	('WIFI', '17.0' "2021-04-16", 1), 
	#( ),
]

leg1 = {"expirationDate":"2019-12-20",
		"strike":"2.00",
		"optionType":"call",
		"effect":"open",
		"action":"buy"}

leg2 = {"expirationDate":"2019-12-20",
		"strike":"4.00",
		"optionType":"call",
		"effect":"open",
		"action":"sell"}

spread = [leg1,leg2]



stocks = [ "SLB","EOG","MPC","WFC","AEG","FNB","TKR","CIG","UBS","CNQ","COOP","FTI",
"BBVA","TCOM","SBSW","REI","MS","GSL","RTX","SCS","BBL","WRK","DE","HES","TTE","MGM",
"ADM","ING","CMA","TOL","QFIN","PXD","MTB","EWBC","NTRS","SYY","BHP","MFC","LYG","HBAN",
"FMBI","VRTX","TFC","BK","VTR","VNET","LYB","AL","PTSI","DCP","USB","AGO","BWA","OC","NVDA",
"SAP","OI","STT","BPOP","CMI","DKS","RF","CVGI","OLED","AXL","KEY","STAG","BMO","EMN","TS",
"DFS","TCBI","CCK","STM","BKU","EGO","GMED","MUI","ABR","SRC","SPG","HCI","OLN","BBI","CDE",
"OSK","TRGP","SWCH","TPR","CHKP","TTD",
	#from tickeron engine december 12 weekly play
	#'ERF', 'HFFG', 'YELL', 'RELL', 'SUZ', 'GGB',
]

stocks = set(list(stocks))
#random.shuffle(stocks)

#stop_loss_list = [ 'SRNE', 'NMRK', 'CURV']

#trade_counter = [0, 0]
max_iv = 0.60
num_orders = 4 #number of options trades at any moment (one is adready there, AUR)

#from pyrh import Robinhood
import robin_stocks.robinhood as rh
import pyotp
from datetime import datetime
import datetime as dt
import numpy as np
import tulipy as ti
import sched
import time
import sys
from bot_helpers import *

#limit price = option's current price + 0.01
#order_buy_option_limit("open", "debit", limitPrice, symbol, quantity, expirationDate, strike, optionType='call', timeInForce='gfd')
#order_sell_option_limit("close", "credit", "2.0", "SPY", 5, "2020-04-20", 300, "call", "gtc")

#A Simple Robinhood Python Trading Bot using RSI (buy <=30 and sell >=70 RSI) and with support and resistance.
#Youtube : Jacob Amaral
# Log in to Robinhood app (will prompt for two-factor)
with open('keys.txt', 'r') as f:
	lines = [a.strip() for a in f.readlines() ] 

	totp = pyotp.TOTP(lines[0]).now()
	login = rh.login(lines[1],lines[2], mfa_code=totp)


#stop loss list 
#only activate if bought before today
my_list = rh.account.get_open_stock_positions()
#print(my_list)
dates = [ dt.date.fromisoformat(a['updated_at'].split('T')[0]) for a in my_list ]
my_list = [ my_list[a] for a in range(len(dates)) if datetime.date.today() > dates[a] ]
stop_loss_list = [rh.stocks.get_instrument_by_url(a['instrument'])['symbol'] for a in my_list ]
stop_loss_list = [a for a in stop_loss_list if a not in excludes]
#print(stocks)
#print(stop_loss_list)
def order_spread(stock, max_iv = 0.60, vol_min = 100):
	#ret_val = rh.orders.order_option_spread("debit", price, stock, 1, spread, timeInForce="gfd", )
	#r.order_buy_option_limit('open', 'debit', price = price, symbol = ticker, quantity = 1, expirationDate = exp_date, strike = strike , optionType=opt_type, timeInForce='gfd')
	#print(stock)
	spread, buy_price, iv, volume = find_options(stock)
	price = round(buy_price, 2) + 0.01
	#print(price)
	ret_val = stock + " IV too high or volume too low"
	print(iv)
	print(volume)
	print(spread)
	#print(stock)
	if iv <= max_iv and volume > vol_min:
		ret_val = rh.orders.order_option_spread("debit", price, stock, 1, spread, timeInForce="gfd", )
		#print(ret_val)
	return ret_val

def sell_spread(stock):
	#ret_val = r.order_sell_option_limit('close', 'credit', price = price, symbol = symbol, quantity = 1, expirationDate = exp_date, strike = strike, optionType = opt_type, timeInForce='gfd')
	#return ret_val
	curr_price, true_price, spread = find_current_price(stock)

	price = curr_price - 0.01
	print( price)
	ret_val = rh.orders.order_option_spread("credit", round(price, 2), stock, 1, spread, timeInForce="gfd", )
	return ret_val


def stop_win_loss(stock, loss_percent=0.3, win_percent=0.8 ):
	curr_price, true_price, spread = find_current_price(stock)

	#if goes less than stop loss or greater than profit percent
	if curr_price < true_price * ( 1 - loss_percent) or curr_price > true_price*(1+win_percent):
		val = sell_spread(stock)
		return val

def stock_stop_win_loss(stock, loss_percent=0.04, win_percent=0.08 ):
	all_open_options = rh.account.get_open_stock_positions()

	#open_and_pending_options = [ rh.stocks.get_instrument_by_url(b['instrument']) for b in all_open_options if b['symbol']==stock ]
	#print("stop loss for :" + stock)
	true_price = [ a['average_buy_price'] for a in all_open_options if rh.stocks.get_instrument_by_url(a['instrument'])['symbol']==stock ][0]
	
	#print(true_price)
	true_price = float(true_price)
	quantity = [ a['quantity'] for a in all_open_options if rh.stocks.get_instrument_by_url(a['instrument'])['symbol']==stock ][0]
	quantity = float(quantity)
	#rh.orders.order_sell_stop_loss(stock, float(val_buy['quantity']), round(rh.get_latest_price(stock)*(1-0.02), 2) )
	curr_price = rh.get_latest_price(stock)[0]
	curr_price = float(curr_price)
	#print(curr_price)
	if curr_price < true_price * ( 1 - loss_percent) or curr_price > true_price*(1+win_percent):
		#val = sell_spread(stock)
		val = rh.orders.order_sell_fractional_by_quantity(stock, quantity, timeInForce='gfd', extendedHours=False)
		print("sell order for :" + stock + " triggered.")
		return val


#Setup our variables, we haven't entered a trade yet and our RSI period
enteredTrade = False
rsiPeriod = 14
#Initiate our scheduler so we can keep checking every minute for new price changes
s = sched.scheduler(time.time, time.sleep)
counter = 0
def run(stock, num_orders, enteredTrade = False): 
	global counter , max_iv
	global rsiPeriod
	#print("Getting historical quotes")
	# Get 5 minute bar data for Ford stock
	time.sleep(0.025)

	#historical_quotes = rh.stocks.get_stock_historicals(stock, "day", "year")
	historical_quotes = rh.stocks.get_stock_historicals(stock, "hour", "month")
	#historical_quotes = rh.stocks.get_stock_historicals(stock, "10minute", "week")
	#print(historical_quotes[:5])
	closePrices = []
	volumes = []

	#format close prices for RSI
	currentIndex = 0
	currentSupport  = 0
	currentResistance = 0
	#print(historical_quotes)
	for key in historical_quotes:
		if (currentIndex >= len(historical_quotes) - (rsiPeriod + 1)):
			if (currentIndex >= (rsiPeriod-1) and datetime.datetime.strptime(key['begins_at'], '%Y-%m-%dT%H:%M:%SZ').minute == 0):
				currentSupport = 0
				currentResistance = 0
			if(float(key['close_price']) < currentSupport or currentSupport == 0):
			   currentSupport = float(key['close_price'])
			if(float(key['close_price']) > currentResistance):
			   currentResistance = float(key['close_price'])
			closePrices.append(float(key['close_price']))
			volumes.append(float(key['volume']) )
		currentIndex += 1
	DATA = np.array(closePrices)

	#longer trend
	historical_quotes_long = rh.stocks.get_stock_historicals(stock, "day", "year")
	#historical_quotes = rh.stocks.get_stock_historicals(stock, "10minute", "week")
	#print(historical_quotes[:5])
	closePrices_long = []
	volumes_long = []

	#format close prices for RSI
	high_long, low_long = [], []
	currentIndex_long = 0
	currentSupport_long  = 0
	currentResistance_long = 0
	rsiPeriod_long = 14
	#print(historical_quotes)
	for key in historical_quotes_long:
		if (currentIndex_long >= len(historical_quotes_long) - (rsiPeriod_long + 1)):
			if (currentIndex_long >= (rsiPeriod_long-1) and datetime.datetime.strptime(key['begins_at'], '%Y-%m-%dT%H:%M:%SZ').minute == 0):
				currentSupport_long = 0
				currentResistance_long = 0
			if(float(key['close_price']) < currentSupport_long or currentSupport_long == 0):
			   currentSupport_long = float(key['close_price'])
			if(float(key['close_price']) > currentResistance_long):
			   currentResistance_long = float(key['close_price'])
			closePrices_long.append(float(key['close_price']))
			volumes_long.append(float(key['volume']) )
			high_long.append(float(key['high_price']) )
			low_long.append(float(key['low_price']) )
			
		currentIndex_long += 1
	DATA_long = np.array(closePrices)
	#data = rh.options.find_options_by_expiration_and_strike("BOX", "2021-04-16", '20.0', optionType='call', info=None) [0] 

	#print(data)
	#print(data['adjusted_mark_price'] )
	if (len(closePrices) > (rsiPeriod)):
		#Calculate RSI
		#adx_ = 0
		adx_ = ti.adx(np.array(high_long), np.array(low_long), np.array(closePrices_long), 7)
		#print(dmi)
		#if dmi[0] > dmi[1]: adx_ = dmi[0]
		rsi = ti.rsi(DATA, period=rsiPeriod)
		vwap = ti.vwma(np.array(DATA), np.array(volumes), period=10)
		sma = ti.hma(np.array(DATA), period=13) #hull moving average
		short_period, long_period, signal_period = 9, 12, 24

		sma_long = ti.hma(np.array(DATA_long), period=13) #hull moving average
		short_period, long_period, signal_period = 9, 12, 24
		macd, macd_signal, macd_histogram = ti.macd(DATA, short_period=short_period,
			long_period=long_period, 
			signal_period=signal_period)

		macd_long, macd_signal_long, macd_histogram_long = ti.macd(DATA_long, short_period=short_period,
			long_period=long_period, 
			signal_period=signal_period)
		rsi_long = ti.rsi(DATA_long, period=rsiPeriod )
		ema_long = ti.ema(np.array(rsi_long), period=13) #hull moving average
		vwap_long = ti.vwma(np.array(DATA_long), np.array(volumes_long), period=10)
		#ema_rsi = ti.ema(np.array(sma), period=12)

		signal1 = adx_[-1] > 25 and adx_[-1] >= adx_[-1]
		signal2 = vwap_long[-1] <= DATA[-1] and float(key['close_price']) <= currentSupport_long
		signal3 = vwap[-1] <= DATA[-1] and float(key['close_price']) <= currentSupport

		signal4 = ( (macd_long[-1] > macd_signal_long[-1]  and macd_long[-1] > macd_long[-2] > macd_long[-3] ) or \
			(macd_long[-1] < macd_signal_long[-1]   and macd_long[-1] > macd_long[-2] > macd_long[-3] ) ) and \
			abs(macd_long[-1] - macd_signal_long[-1]) <= 0.03
		
		signal5 = rsi[-1] < 45 and rsi_long[-1] < 60
		
		signal6 = ( (macd[-1] > macd_signal[-1]   and macd[-1] >= macd[-2]  ) or \
			(macd[-1] < macd_signal[-1]  and macd[-1] >= macd[-2] ) ) and \
			abs(macd[-1] - macd_signal[-1]) <= 0.03
		
		#signal3 = signal3 and signal5

		signal7 = sma[-1] < vwap[-1] or sma_long[-1] < vwap_long[-1]
		
		signals = [signal1, signal2, signal3, signal4, signal5, signal6, signal7]
		#print(adx_)
		#instrument = rh.instruments("F")[0]
		#If rsi is less than or equal to 30 buy
		#if rsi[len(rsi)-1] <= 45 and \
		#print(stock)
		#print(vwap[-1] - sma[-1] )
		# > macd_long[-3] 
		## buy at best point of the day
		#if not enteredTrade and rsi_long[-1] > ema_long[-1] and 40 < ema_rsi[-1] < 60 and \
		if	len([a for a in signals if a == True] ) >= 6:
			#print("Buying RSI is below 35!")
			#option position
			#buy if number of open option orders is less than 2
			all_open_options = rh.options.get_open_option_positions()
			open_and_pending_options = [b['chain_symbol'] for b in all_open_options]
			
			#stock positions
			all_open_options = rh.account.get_open_stock_positions()
			open_and_pending_options = [ rh.stocks.get_instrument_by_url(b['instrument'])['symbol'] for b in all_open_options]
			
			#print(len(open_and_pending_options))
			#only buy less than the predetermined number at a time and only one time
			#rsi less than 50 (not oversold)
			# macd less than signal and difference less than 0.02
			# or macd > signal and macd - signal < 0.02 and macd growing
			# 
			## buy at the best point of the day
			## short rsi at buy zone and long at not overbought
			if len(open_and_pending_options) <= num_orders * 2 and stock not in open_and_pending_options:
				#and abs(macd[-1] - macd_signal[-1]) <= 0.03				
				#and abs(macd[-1] - macd_signal[-1]) <= 0.03

				#( (macd[-1] < macd_signal[-1] and abs(macd[-1] - macd_signal[-1]) < abs(macd[-2] - macd_signal[-2]) ) or \
				#(macd[-1] > macd_signal[-1] and abs(macd[-1]-macd_signal[-1]) > abs(macd[-1] - macd_signal[-2]) ) ):# or (macd[-1] > macd[-3] and  macd[-1] < macd_signal[-1])):
				#place buy order
				val_buy = []
				try:
					#options trading
					#val = order_spread(stock, max_iv = max_iv) #order a spread to be filled

					#stock
					val_buy = rh.orders.order_buy_fractional_by_price(stock, 20, timeInForce='gfd', extendedHours=True)

					print(val_buy)
					#print(val)
					#enteredTrade = True#si) - 1]
					time.sleep(5) #sleep for 3 seconds for order to complete
					
					#set stop loss for stock
					
					#val = rh.orders.order_sell_stop_loss(stock, float(val_buy['quantity']), round(rh.get_latest_price(stock)*(1-0.02), 2) )
				
				except Exception as e:
					print(e)
					print("Could not enter trade due to an error")
					print(stock)
				
				#rh.orders.cancel_all_option_orders() #cancel all pending orders not fulfilled since last run
				#pass

			else:
				print(stock + ": max orders reached or macd < signal")
			#rh.place_buy_order(instrument, 1)
			#rh.orders.order_buy_option_limit("open", "debit", limitPrice, symbol, quantity, expirationDate, strike, optionType='call', timeInForce='gfd')            
				
		else: pass#print(key['close_price'] )
		
		#Sell when RSI reaches 70
		#if rsi[len(rsi) - 1] >= 70 and \
		#macd less than signal and increasing
		#macd greater than signal and decreasing
		#rsi[-1] > 65 and
		if	enteredTrade:
			historical_quotes = rh.stocks.get_stock_historicals(stock, "day", "year")
			short_period, long_period, signal_period = 9, 12, 24
			macd, macd_signal, macd_histogram = ti.macd(DATA, short_period=short_period,
				long_period=long_period, 
				signal_period=signal_period)
			macd_long, macd_signal_long, macd_histogram_long = ti.macd(DATA, short_period=short_period,
				long_period=long_period, 
				signal_period=signal_period)
			rsi_long = ti.rsi(DATA_long, period=rsiPeriod )
			ema_long = ti.ema(np.array(rsi_long), period=13) #hull moving average
			# < macd[-3]  < macd[-3]
			#if rsi_long[-1] < ema_long[-1] and rsi[-1] > 70 or 
			if rsi_long[-1] > 70 or  ( (macd_long[-1] <= macd_signal_long[-1] and macd_long[-1] <= macd_long[-2] ) or \
			(macd_long[-1] >= macd_signal_long[-1] and macd_long[-1] <= macd_long[-2]  ) ) : # < macd[-3]
			
			#if ( (macd[-1] <= macd_signal[-1] and macd[-1] <= macd[-2] <= macd[-3]  ) or \
			#(macd[-1] >= macd_signal[-1] and macd[-1] <= macd[-2]<= macd[-3]  ) ) : # < macd[-3]
			
			#vwap[-1] <= sma[-1] and float(key['close_price']) >= currentResistance and currentResistance > 0 and enteredTrade and \
			#(macd[-1] > macd_signal[-1] and macd[-1] < macd[-2] < macd[-3] ):# or (macd[-1] > macd[-3] and  macd[-1] < macd_signal[-1]) ):
			#print(stock + ": Selling RSI is above 65!")
				print("sell order for :" + stock + " triggered.")
				##for stocks
				all_open_options = rh.account.get_open_stock_positions()
				quantity = [ a['quantity'] for a in all_open_options if rh.stocks.get_instrument_by_url(a['instrument'])['symbol']==stock ][0]
				#sell fractional order
				val = rh.orders.order_sell_fractional_by_quantity(stock, quantity, timeInForce='gfd', extendedHours=False)
				#print(val)
				#rh.place_sell_order(instrument, 1)
				#order_sell_option_limit("close", "credit", "2.0", "SPY", 5, "2020-04-20", 300, "call", "gtc")
				enteredTrade = False

		else: pass#print(key['close_price'] )
		#print(rsi)
	#val = rh.orders.order_buy_option_limit("open", "debit", 1.10, "BOX", 1, "2021-04-16", "20", optionType='call', timeInForce='gfd')
	#print(val)
	#call this method again every 5 minutes for new price changes
	counter += 1
	#if counter < 4:
	return enteredTrade

def run_stocks(sc, stocks, stop_loss_list, num_orders):
	#rh.orders.cancel_all_option_orders() #cancel all pending orders not fulfilled since last run
	rh.orders.cancel_all_stock_orders() #cancel stock orders
	for stock in stocks:
		#if rh.options.get_open_option_positions() <= num_orders * 2: #if num_orders is not full
		try:
			entered_trade = run(stock, num_orders)
		except Exception as e:
			print(e)
			print("stock probably does not exist")
	for stock in stop_loss_list:
		try: #stop loss function
			#option one
			#stp = stop_win_loss(stock, loss_percent=0.4, win_percent=1.0 )
			#stock one
			#check stop criteria one with enteredTrade counter
			check_stop_criteria = run(stock, num_orders, enteredTrade=True)
			
			stp = stock_stop_win_loss(stock)
			#print(stp)
		except Exception as e:
			print(e)
			print(stock + ": Stop loss did not work, no open position. ")
		#if entered_trade: break
	#stop loss

	#20 minutes
	#s.enter(20*60, 1, run_stocks, (sc, stocks, stop_loss_list, num_orders))

#a = order_spread('SPY', max_iv = 1.2)
#a = rh.options.get_open_option_positions()
#a = [b['chain_symbol'] for b in a]
#print(a)

s.enter(1, 1, run_stocks, (s, stocks, stop_loss_list, num_orders))
s.run()

#val = rh.order_buy_market('AAPL',1)

#val = rh.stocks.get_latest_price('AAPL', includeExtendedHours=False)
#val = rh.orders.order_sell_fractional_by_price('AAPL', 20, timeInForce='gfd', extendedHours=True)


# val = rh.account.get_open_stock_positions()
# print(val)
# val = rh.stocks.get_instrument_by_url('https://api.robinhood.com/instruments/450dfc6d-5510-4d40-abfb-f633b7d9be3e/')
# # val = rh.orders.order_sell_stop_loss('AAPL', val_buy['quantity'], round(rh.get_latest_price('AAPL')*(1-0.02), 2) )
# print(val)
# val = rh.stocks.get_latest_price('AAPL')

#sc = 0
#print(run(sc))
