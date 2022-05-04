from ibapi.client import EClient
from ibapi.wrapper import EWrapper  
from ibapi.contract import Contract
from ibapi.common import BarData
from ibapi.order import Order
import datetime
import math



class IBapi(EWrapper, EClient):
    TICKER = "FB" 
    MAX_Stop_Orders_Per_Day=10
    MAX_Stop_Orders_Per_Hour=8
    START_OF_TRADING = "16:30:00"
    END_OF_DAY = "23:00:00"
    Buy_Stop_Percent = 1
    Sell_Limit=[1,2,3,4,5,6,7,8,9,10]
    Sell_Limit_Amt=[0.1,0.1,0.1,0.1,0.1,  0.1,0.1,0.1,0.1,0.1];
    Sell_Stop_Percent = 1
    Buy_Limit=[1,2,3,4,5,6,7,8,9,10]
    Buy_Limit_Amt= [0.1,0.1,0.1,0.1,0.1,  0.1,0.1,0.1,0.1,0.1];
    USD_Quantity = [100,110,120,130,140,150,160,170,180,190]

    serverTime = None
    openPrice = None
    price = None
    remainLot = 0
    
    MAX_Stop_Orders_Per_Day_Counter = 0
    MAX_Stop_Orders_Per_Hour_Counter =0
    lastHour =0

    buy_stop_orderid = -1
    sell_stop_orderid = -1

    buy_stop_level = 0
    sell_stop_level = 0
    nextOrderId = 1

    tradeState = 0
    tradeDirection = 0
    stoplossId=0
    limiOrderIdList=[]
    tickCount = 0
    def __init__(self):
        EClient.__init__(self, self)
        self.contract = self.Stock_contract(self.TICKER)
        self.tradeState = 0


    def Stock_contract(self,symbol, secType='STK', exchange='SMART', currency='USD'):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        return contract

    def timeInRange(self):
        return True

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 2:
            self.price =price
            self.tickCount = self.tickCount+1
            if(self.tickCount>20):
	            print(f'\rOpen price:{self.openPrice} , Current Price:{self.price}, Remain Lot:{self.remainLot} buy/sell level:{self.buy_stop_level}/{self.sell_stop_level}',end='', flush=True);
	            self.tickCount = 0
            if(self.openPrice is not None and self.price is not None and self.tradeState==0): #meet open price
                if(self.price<self.buy_stop_level and self.price>self.sell_stop_level):#meet price condition
                    if(self.timeInRange()==False):
                        return;
                    if (self.MAX_Stop_Orders_Per_Day_Counter>=self.MAX_Stop_Orders_Per_Day and
                        self.MAX_Stop_Orders_Per_Hour_Counter>=self.MAX_Stop_Orders_Per_Hour):
                        return;
                    self.nextOrderId = self.nextOrderId +1
                    self.buy_stop_orderid = self.nextOrderId;
                    order = Order();
                    order.action = "BUY";
                    order.orderType = "STP";
                    order.auxPrice = self.buy_stop_level;
                    order.totalQuantity = self.USD_Quantity[self.MAX_Stop_Orders_Per_Day_Counter]
                    self.remainLot = order.totalQuantity
                    self.placeOrder(self.nextOrderId, self.contract, order)

                    self.nextOrderId = self.nextOrderId +1
                    self.sell_stop_orderid = self.nextOrderId;
                    order = Order();
                    order.action = "SELL";
                    order.orderType = "STP";
                    order.auxPrice = self.sell_stop_level;
                    order.totalQuantity = self.USD_Quantity[self.MAX_Stop_Orders_Per_Day_Counter]
                    self.placeOrder(self.nextOrderId, self.contract, order)

                    self.MAX_Stop_Orders_Per_Day_Counter = self.MAX_Stop_Orders_Per_Day_Counter + 1
                    self.MAX_Stop_Orders_Per_Hour_Counter = self.MAX_Stop_Orders_Per_Hour_Counter+1
                    self.tradeState = 1
                    print(f'\nPlaced order\n')
        if tickType==14:
            self.openPrice = price
            self.buy_stop_level = math.floor(self.openPrice*(1+self.Buy_Stop_Percent/100)*100)/100
            self.sell_stop_level = math.floor(self.openPrice*(1-self.Sell_Stop_Percent/100)*100)/100
    def stopOrderFilled(self):
        return None

    def limitOrderFilled(self):
        return None 

    def nextValidId(self, orderId:int):
        #4 first message received is this one
        print("setting nextValidOrderId: %d", orderId)
        self.nextOrderId = orderId

    def error(self, reqId, errorCode, errorString):
        print("Error. Id: " , reqId, " Code: " , errorCode , " Msg: " , errorString)

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice):
        print('OrderStatus. Id: ', orderId, 'Status: ', status, 'Filled: ', filled, 'Remaining: ', remaining,
              'LastFillPrice: ', lastFillPrice)

    def openOrder(self, orderId, contract, order, orderState):
        print('openOrder id:', orderId, contract.symbol, contract.secType, '@', contract.exchange, ':', order.action,
              order.orderType, order.totalQuantity, orderState.status)

    def execDetails(self, reqId, contract, execution):
        print('Order Executed: ', reqId, contract.symbol, contract.secType, contract.currency, execution.execId,
              execution.orderId, execution.shares, execution.lastLiquidity)
        
        if(self.tradeState==1):
            batchOrder = [];
            self.remainLot = execution.shares
            if(execution.orderId == self.buy_stop_orderid):
                self.cancelOrder(self.sell_stop_orderid)
                self.tradeDirection = 1
                for i in range(len(self.Sell_Limit)):
                    order = Order()
                    order.action = "SELL";
                    order.orderType = "LMT";
                    order.lmtPrice = math.floor(self.buy_stop_level*(1+self.Sell_Limit[i]/100)*100)/100;
                    order.totalQuantity = math.floor(self.Sell_Limit_Amt[i]*self.remainLot)
                    batchOrder.append(order)
                order = Order()
                order.action = "SELL";
                order.orderType = "STP";
                order.auxPrice = self.openPrice;
                order.totalQuantity = execution.shares
                batchOrder.append(order)
            else:
                self.cancelOrder(self.buy_stop_orderid)
                self.tradeDirection = -1
                for i in range(len(self.Sell_Limit)):
                    order = Order()
                    order.action = "BUY";
                    order.orderType = "LMT";
                    order.lmtPrice = math.floor(self.buy_stop_level*(1-self.Sell_Limit[i]/100)*100)/100;
                    order.totalQuantity = math.floor(self.Sell_Limit_Amt[i]*self.remainLot)
                    batchOrder.append(order)
                order = Order()
                order.action = "BUY";
                order.orderType = "STP";
                order.auxPrice = self.openPrice;
                order.totalQuantity = execution.shares
                batchOrder.append(order)
            for o in batchOrder:
                self.nextOrderId = self.nextOrderId +1
                self.placeOrder(self.nextOrderId, self.contract, o)
                if(o.orderType=="LMT"):
                    self.limiOrderIdList.append(self.nextOrderId)
                else:
                    self.stoplossId = self.nextOrderId
            self.tradeState = 2              
            print('sent limit orders')  
            return
        if(self.tradeState==2):
            if(execution.orderId==self.stoplossId):#got stop loss
                for oId in self.limiOrderIdList:
                    self.cancelOrder(oId)
                self.tradeState = 0
                self.remainLot = 0
                print('got stoploss')  

            else:
                self.limiOrderIdList.pop(0)
                print('got tp level',self.limiOrderIdList)  
                self.remainLot = self.remainLot-execution.shares
                self.cancelOrder(self.stoplossId)
                if(self.remainLot==0):
                    self.tradeState = 0
                    self.remainLot = 0
                else:
                    self.nextOrderId = self.nextOrderId +1
                    order = Order()
                    order.orderType = "STP";
                    order.auxPrice = self.openPrice
                    order.totalQuantity = self.remainLot
                    if self.tradeDirection==1:
                        order.action = "SELL";
                    else:                    
                        order.action = "BUY";
                    self.placeOrder(self.nextOrderId, self.contract, order)
                    self.stoplossId = self.nextOrderId 
            return

    def start(self):
        self.reqMktData(1, self.contract, "", False, False, [])
        return
    
app = IBapi()
app.connect('95.168.191.114', 7497, 123)
app.start()
app.run()

