
import math
import numpy as np
import pandas as pd
import pandas_ta as ta
from yahoo_fin import options
from joblib import Parallel, delayed
import robin_stocks.robinhood as rh
import pyotp
import datetime as dt
import datetime
import time

with open('keys.txt', 'r') as f:
	lines = [a.strip() for a in f.readlines() ]	

	totp = pyotp.TOTP(lines[0]).now()
	login = rh.login(lines[1],lines[2], mfa_code=totp)



def find_options(symbol):
	
	now = dt.datetime.now()
	start = now + dt.timedelta(30)
	end = now + dt.timedelta(60 )
	date_generated = [start + dt.timedelta(days=x) for x in range(0, (end-start).days)]
	date_list = []
	for date in date_generated:
		date_list.append(date.strftime("%Y-%m-%d"))

	#plugs in list of dates to filter out
	data = rh.options.find_tradable_options(symbol, optionType=None)

	df = pd.DataFrame(data)
	new_df = df[df['expiration_date'].isin(date_list)].reset_index(drop=True)

	#creates a list of strikes prices
	strike_list = new_df.strike_price.unique().tolist()

	#grabs current stock price of stock
	current_price = rh.stocks.get_latest_price(symbol)[0]

	#appends current stock price to list
	strike_list.append(current_price)

	strike_list = list(set(strike_list ))
	#sorts out the list
	strike_list_sort = sorted(strike_list,key=float)

	#print(strike_list_sort)
	#grab the furthest stock price from the 30-45 date range
	expirationDate = sorted(new_df.expiration_date.unique())[-1]
	#print(expirationDate)
	#create a 'bookmark' for stock price
	i = strike_list_sort.index(current_price)
	
	#grab the stock price that is above the 'bookamrk'
	strike_a = strike_list_sort[i+1] #long call strike price

	print(strike_list_sort)
	print(i)
	print(strike_a)
	print(strike_list_sort[i+2])
	#strike_a
	#print(len(strike_list_sort))
	#print(strike_list_sort[i+3] )
	#print(expirationDate)
	#fill in all info to get info for option price
	#data = rh.options.find_tradable_options(symbol)
	data = rh.options.find_options_by_expiration_and_strike(symbol, expirationDate, strike_list_sort[i+1], optionType='call', info=None)

	
	#data2 = rh.options.find_options_by_expiration_and_strike(symbol, expirationDate, strike_list_sort[i+2] , optionType='call', info=None)
	#grab the next one
	data2 = []
	counter = True

	i = i+2
	while counter == True:
		data2 = rh.options.find_options_by_expiration_and_strike(symbol, expirationDate, strike_list_sort[i] , optionType='call', info=None)
		i+=1
		#print(data2)
		if data2 !=[]: counter = False
	#grabbing the price for the option
	#print(data)
	#data.extend(data2)

	#print(data2)

	buy_price = abs( float(data[0]['mark_price']) - float(data2[0]['mark_price'] ) ) + 0.01 #add for high fill rate

	leg1 = {"expirationDate":data[0]['expiration_date'],
		"strike":data[0]['strike_price'],
		"optionType":"call",
		"effect":"open",
		"action":"buy"}

	leg2 = {"expirationDate": data2[0]['expiration_date'],
		"strike":data2[0]['strike_price'],
		"optionType":"call",
		"effect":"open",
		"action":"sell"}

	spread = [leg1, leg2]

	volume = min([int(data[0]['volume']), int(data2[0]['volume']) ] )
	#print(spread)
	#print(buy_price)
	#positions = rh.options.get_open_option_positions()
	#print([a for a in positions if a['chain_symbol'] == symbol])

	#historical_data = rh.get_option_historicals(symbol, leg1['expirationDate'], leg1['strike'], leg1['optionType'], "day", "year", "regular", info=None)

	#print(historical_data)
	print( rh.options.get_open_option_positions() )
	#print(rh.get_chains('OTLY') )
	#print(rh.get_option_market_data_by_id('37a867eb-5420-4c5d-9eb9-e8d38727293e' ) )
	max_iv = max([ float(data2[0]['implied_volatility']), float(data[0]['implied_volatility'] )] )
	return spread, buy_price, max_iv, volume


#this is to find options of a sybmol to close
def find_price_diff(option1_id, option2_id):
	price1 = rh.get_option_market_data_by_id(option1_id )[0]['high_fill_rate_sell_price']
	price2 = rh.get_option_market_data_by_id(option2_id )[0]['high_fill_rate_sell_price']

	val1 = rh.get_option_market_data_by_id(option1_id )
	ins = rh.stocks.get_instrument_by_url(val1[0]['instrument'] )
	data = ins

	val2 = rh.get_option_market_data_by_id(option2_id )
	ins = rh.stocks.get_instrument_by_url(val2[0]['instrument'] )
	data2 = ins

	#low_vol = min([ int(val2[0]['volume']), int(val1[0]['volume'] ) ])
	#print(data)
	leg1 = {"expirationDate":data['expiration_date'],
		"strike":data['strike_price'],
		"optionType":"call",
		"effect":"close",
		"action":"sell"}

	leg2 = {"expirationDate": data2['expiration_date'],
		"strike":data2['strike_price'],
		"optionType":"call",
		"effect":"close",
		"action":"buy"}

	spread = [leg1, leg2]


	#print(spread)
	#print(ins)
	return float(price2) - float(price1), spread#, low_vol
	#pass

def find_current_price(stock):

	open_pos = [a for a in rh.options.get_open_option_positions() if a['chain_symbol']==stock ]
	#print(open_pos)
	true_price = float(open_pos[1]['average_price']) + float(open_pos[0]['average_price']) #true price of the spread

	open_pos_1 = open_pos[0]
	open_pos_2 = open_pos[1]

	#print(open_pos)
	price, spread = find_price_diff(open_pos_1['option'].split('/')[-2], open_pos_2['option'].split('/')[-2] )
	#print(spread)
	return abs(price), abs(true_price), spread
	#curr price, price bought, spread, volume 
	#current price and true price

if __name__ == "__main__":
	val, price, max_iv, vol =find_options("SPY")

	print(val, price, vol)
	#open_pos_1 = rh.options.get_open_option_positions()[0]
	#open_pos_2 = rh.options.get_open_option_positions()[1]

	#options = find_price_diff(open_pos_1['option'].split('/')[-2], open_pos_2['option'].split('/')[-2] )

	#print(options)
	# stock = 'AUR'
	#price, true_price, spread = find_current_price(stock)

	# price = str( round(price, 2))

	# #def sell_spread(stock, price, spread):
 #    #ret_val = r.order_sell_option_limit('close', 'credit', price = price, symbol = symbol, quantity = 1, expirationDate = exp_date, strike = strike, optionType = opt_type, timeInForce='gfd')
 #    #return ret_val
	# ret_val = rh.orders.order_option_spread("credit", price, stock, 1, spread, timeInForce="gfd", )

	# print( ret_val)



