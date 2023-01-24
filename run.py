import ccxt
import schedule
import time
import os
from dotenv import load_dotenv
import config

load_dotenv()
api_key = os.getenv('API_KEY')
api_key_secret = os.getenv('API_KEY_SECRET')
ordersDict = {}
total_average_cost = 0
total_cost = 0
total_quantity = 0
safety_timer = 0

if not api_key or not api_key_secret:
    raise ValueError("API_KEY or API_KEY_SECRET not set in the environment.")

# Initialiseer een exchange object
exchange = ccxt.binance({
    'rateLimit': 2000,
    'enableRateLimit': True,
    'apiKey': api_key,
    'secret': api_key_secret,
})

def placeOrder(pair,side,quantity):
    try:
        order = exchange.create_order(pair, 'market', side, quantity)
        if side == 'buy':
            ordersDict[order['id']] = {'pair': pair, 'quantity': quantity, 'status': 'open'}
            print(ordersDict)
    except Exception as e: print(e)



def fetchOrder():
    global total_average_cost
    global total_cost
    global total_quantity

    pair = config.pair
        # Loop door de items in de dictionary
    try:
        for order_id in ordersDict:
            if ordersDict[order_id]['status'] == 'open':
                # Haal informatie over de order op
                order = exchange.fetch_order(symbol=pair,id=order_id)
                # Voeg de status van de order toe aan de dictionary
                ordersDict[order_id]['status'] = order['status']

                # Controleer of de order gesloten is
                if order['status'] == 'closed':
                    ordersDict[order_id]['average'] = order['average']
                    ordersDict[order_id]['quantity'] = order['amount']
                    # Bereken de totale kosten voor deze order
                    total_cost += order['average'] * order['amount']
                    # Voeg de gekochte hoeveelheid toe aan de totale hoeveelheid
                    total_quantity += order['amount']

            
        if total_quantity != 0:
            average_cost = total_cost / total_quantity
            total_average_cost = average_cost
            print(f'The average buy price is: {average_cost}')
        else: total_average_cost = 0
    except Exception as e: print(e)
    
 

def sellOrders():
    try:
        if isSellingPossible():
            for order_id in dict(ordersDict):
                if ordersDict[order_id]['status'] == 'closed':
                    quantity = ordersDict[order_id]['quantity']
                    placeOrder(config.pair,'sell',quantity)
                    del ordersDict[order_id]
                    time.sleep(1)
                    break
    except Exception as e: print(e)



            

def checkDCA():
    global total_average_cost
    global safety_timer
    if total_average_cost != 0:
        print('Check if DCA is possible...')
        current_price = getPrice()
        deviation = ((current_price - total_average_cost) / total_average_cost)*100
        if deviation < -abs(config.dca_spread):
            print('DCA order possible!')
            placeOrder(config.pair,'buy',getQuantity(config.trading_limit,config.pair))
            print(f'Safety timer is now activated, it is now {safety_timer} seconds')
            time.sleep(safety_timer)
            safety_timer += 1
        else: print(f'Not possible, current price is too high! Deviation is {deviation}, must be lower than {config.dca_spread}')



def isSellingPossible():
    if ordersDict:
        current_price = getPrice()
        sell_price = total_average_cost * (1+config.gain)
        print(f'Selling at a price of {sell_price}, current price is {current_price}')


        if current_price > sell_price:
            return True
        else:
            checkDCA() 
            return False


def getPrice():
    try:
        ticker = exchange.fetch_ticker(config.pair)
        last = ticker['last']
        return last
    except Exception as e: print(e)


def initialOrder():
    global safety_timer
    global total_average_cost
    global total_cost
    global total_quantity
    if not ordersDict:
        total_average_cost = 0
        total_cost = 0
        total_quantity = 0
        safety_timer = 0
        placeOrder(config.pair,'buy',getQuantity(config.trading_limit,config.pair))

        

def getQuantity(trading_limit,ticker):
    lastPrice = getPrice()
    amount = trading_limit / lastPrice
    return amount





# Plan de functie om elke seconde uit te voeren
schedule.every(1).seconds.do(fetchOrder)
schedule.every(1).seconds.do(sellOrders)
schedule.every(5).seconds.do(initialOrder)


while True:
    schedule.run_pending()
    time.sleep(1)