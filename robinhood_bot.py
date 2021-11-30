
import random
import time

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

stocks = ['DE', 'LNG', 'ALL', 'BYD', 'NYT', 'TRGP', 'MMP',
	'EVFM', 'HAIN', 'HUN', 'MMP' ]

random.shuffle(stocks)
stop_loss_list = [ ]

#trade_counter = [0, 0]
max_iv = 0.60
num_orders = 2 #number of options trades at any moment (one is adready there, AUR)

#from pyrh import Robinhood
import robin_stocks.robinhood as rh
import pyotp
from datetime import datetime
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



def order_spread(stock, max_iv = 0.60, vol_min = 100):
	#ret_val = rh.orders.order_option_spread("debit", price, stock, 1, spread, timeInForce="gfd", )
	#r.order_buy_option_limit('open', 'debit', price = price, symbol = ticker, quantity = 1, expirationDate = exp_date, strike = strike , optionType=opt_type, timeInForce='gfd')
	#print(stock)
	spread, buy_price, iv, volume = find_options(stock)
	price = round(buy_price, 2) + 0.02
	#print(price)
	ret_val = stock + " Not entered trade, Cant order spread"
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

	price = curr_price - 0.02
	print( price)
	ret_val = rh.orders.order_option_spread("credit", round(price, 2), stock, 1, spread, timeInForce="gfd", )
	return ret_val


def stop_win_loss(stock, loss_percent=0.3, win_percent=0.8 ):
	curr_price, true_price, spread = find_current_price(stock)

	#if goes less than stop loss or greater than profit percent
	if curr_price < true_price * ( 1 - loss_percent) or curr_price > true_price*(1+win_percent):
		val = sell_spread(stock)
		return val

#Setup our variables, we haven't entered a trade yet and our RSI period
enteredTrade = False
rsiPeriod = 14
#Initiate our scheduler so we can keep checking every minute for new price changes
s = sched.scheduler(time.time, time.sleep)
counter = 0
def run(stock, num_orders): 
	global enteredTrade, counter , max_iv
	global rsiPeriod
	print("Getting historical quotes")
	# Get 5 minute bar data for Ford stock
	#historical_quotes = rh.stocks.get_stock_historicals(stock, "hour", "month")
	historical_quotes = rh.stocks.get_stock_historicals(stock, "10minute", "week")
	#print(historical_quotes[:5])
	closePrices = []
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
				print("Resetting support and resistance")
			if(float(key['close_price']) < currentSupport or currentSupport == 0):
			   currentSupport = float(key['close_price'])
			   print("Current Support is : ")
			   print(currentSupport)
			if(float(key['close_price']) > currentResistance):
			   currentResistance = float(key['close_price'])
			   print("Current Resistance is : ")
			   print(currentResistance)
			closePrices.append(float(key['close_price']))
		currentIndex += 1
	DATA = np.array(closePrices)
	#data = rh.options.find_options_by_expiration_and_strike("BOX", "2021-04-16", '20.0', optionType='call', info=None) [0] 

	#print(data)
	#print(data['adjusted_mark_price'] )
	if (len(closePrices) > (rsiPeriod)):
		#Calculate RSI
		rsi = ti.rsi(DATA, period=rsiPeriod)
		#instrument = rh.instruments("F")[0]
		#If rsi is less than or equal to 30 buy
		if rsi[len(rsi)-1] <= 30 and float(key['close_price']) <= currentSupport and not enteredTrade:
			print("Buying RSI is below 30!")
			#buy if number of open option orders is less than 2
			all_open_options = rh.options.get_open_option_positions()
			open_and_pending_options = [b['chain_symbol'] for b in all_open_options]
			#only buy less than the predetermined number at a time and only one time
			if len(open_and_pending_options) <= num_orders * 2 and stock not in open_and_pending_options:
				#place buy order
				try:
					val = order_spread(stock, max_iv = max_iv) #order a spread to be filled
					print(val)
					enteredTrade = True#si) - 1]
				except Exception as e:
					print(e)
					print("Could not enter trade due to an error")
					print(stock)
				time.sleep(5) #sleep for 3 seconds for order to complete
				rh.orders.cancel_all_option_orders() #cancel all pending orders not fulfilled since last run
				#pass
			else:
				print("Already have option or no max orders reached or ran into error")
			#rh.place_buy_order(instrument, 1)
			#rh.orders.order_buy_option_limit("open", "debit", limitPrice, symbol, quantity, expirationDate, strike, optionType='call', timeInForce='gfd')            
				
		else: print(key['close_price'] )
		
		#Sell when RSI reaches 70
		if rsi[len(rsi) - 1] >= 70 and float(key['close_price']) >= currentResistance and currentResistance > 0 and enteredTrade:
			print("Selling RSI is above 70!")
			#rh.place_sell_order(instrument, 1)
			#order_sell_option_limit("close", "credit", "2.0", "SPY", 5, "2020-04-20", 300, "call", "gtc")
			enteredTrade = False
		else: print(key['close_price'] )
		#print(rsi)
	#val = rh.orders.order_buy_option_limit("open", "debit", 1.10, "BOX", 1, "2021-04-16", "20", optionType='call', timeInForce='gfd')
	#print(val)
	#call this method again every 5 minutes for new price changes
	counter += 1
	#if counter < 4:
	return enteredTrade

def run_stocks(sc, stocks, stop_loss_list, num_orders):
	rh.orders.cancel_all_option_orders() #cancel all pending orders not fulfilled since last run
	for stock in stocks:
		#if rh.options.get_open_option_positions() <= num_orders * 2: #if num_orders is not full
		entered_trade = run(stock, num_orders)
		
	for stock in stop_loss_list:
		try: #stop loss function
			stp = stop_win_loss(stock, loss_percent=0.4, win_percent=1.0 )
			print(stp)
		except Exception as e:
			print(e)
			print("Stop loss did not work, no open option ")
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

#sc = 0
#print(run(sc))
