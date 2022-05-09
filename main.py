from ibapi.client import EClient
from ibapi.wrapper import EWrapper  
from ibapi.contract import Contract
from ibapi.common import BarData
from ibapi.order import Order
import datetime 
import math

_test = False

class IBapi(EWrapper, EClient):
    TICKER = "SOXL" 
    SHOWEVERYTICK = 3
    TIMEOFFSET_UTC = 0
    MAX_Stop_Orders_Per_Day=10
    MAX_Stop_Orders_Per_Hour=8

    START_OF_TRADING = datetime.time(16-TIMEOFFSET_UTC,30,0)
    END_OF_DAY = datetime.time(23-TIMEOFFSET_UTC,00,0)
    Buy_Stop_Percent = 6
    Sell_Limit=[0.5,1,1.5,2,2.5,3,3.5,4,4.5,5]
    Sell_Limit_Amt=[0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1];
    Sell_Stop_Percent = 6
    Buy_Limit=[0.5,1,1.5,2,2.5,3,3.5,4,4.5,5]
    Buy_Limit_Amt= [0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1];
    USD_Quantity = [10000,10000,10000,10000,10000,10000,10000,10000,10000,10000]

    serverTime = None
    openPrice = None
    price = None
    high = None
    low = None

    remainLot = 0
    
    MAX_Stop_Orders_Per_Day_Counter = 0
    MAX_Stop_Orders_Per_Hour_Counter =0
    ReduceY = 0.1
    lastHour =0

    buy_stop_orderid = -1
    sell_stop_orderid = -1

    buy_stop_level = 0
    sell_stop_level = 0
    nextOrderId = 1

    tradeState = -2
    tradeDirection = 0
    stoplossId=0
    limiOrderIdList=[]
    tickCount = 0
    stpamount = 0
    def __init__(self):
        EClient.__init__(self, self)
        self.contract = self.Stock_contract(self.TICKER)
        self.tradeState = -2

        file_name = str(self.TICKER) + '-' + datetime.datetime.now().strftime("%d-%m_%H_%M_%S")
        self.save_logs_path = './logs' + '/' + file_name + '.txt'
        self.file = open(self.save_logs_path, "w+")

        if(_test):
            self.contract = self.Stock_contract("EUR",secType='CASH',exchange='IDEALPRO',currency='JPY')
            self.openPrice = 137
            self.buy_stop_level = math.floor(self.openPrice*(1+self.Buy_Stop_Percent/100)*100)/100
            self.sell_stop_level = math.floor(self.openPrice*(1-self.Sell_Stop_Percent/100)*100)/100

    def writeLog(self,message):
        print(self.TICKER+":"+message)
        self.file.write(self.TICKER+":"+message+"\r\n")

    def Stock_contract(self,symbol, secType='STK', exchange='SMART', currency='USD'):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        return contract

    def timeInRange(self):
        x = datetime.datetime.now().time()
        if(self.lastHour != x.hour):
            MAX_Stop_Orders_Per_Hour_Counter =0
            self.lastHour = x.hour
        rt = self.START_OF_TRADING <= x <= self.END_OF_DAY
        if(rt==False):
            MAX_Stop_Orders_Per_Day_Counter = 0
        return rt


    def tickPrice(self, reqId, tickType, price, attrib):
        if(self.timeInRange()==False):
            print(f'Waiting market {self.START_OF_TRADING}/{datetime.datetime.now()}')
            self.tradeState==-2
            return;
        else:
            if self.tradeState==-2:
                self.tradeState=-1
                self.reqAllOpenOrders();
                return;

        if tickType == 6:
            self.high = price
        if tickType == 7:
            self.low = price
        if tickType == 2:
            self.price =price
            self.tickCount = self.tickCount+1
            if(self.tickCount>self.SHOWEVERYTICK):
                pC = 0;
                pH = 0;
                pL = 0;
                if(self.openPrice is not None):
                    pC = math.floor(10000*self.price/self.openPrice-10000)/100;
                    pH = math.floor(10000*self.high/self.openPrice-10000)/100;
                    pL = math.floor(10000*self.low/self.openPrice-10000)/100;
                self.writeLog(f'\rTime:{self.START_OF_TRADING}/{datetime.datetime.now()} Open price:{self.openPrice} , Close:{self.price}[{pC}%],High:{self.high}[{pH}%],Low:{self.low}[{pL}%], Remain Lot:{self.remainLot} buy/sell level:{self.buy_stop_level}/{self.sell_stop_level}');
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
                    self.stpamount = self.USD_Quantity[math.floor(self.MAX_Stop_Orders_Per_Day_Counter)];
                    order = Order();
                    order.action = "BUY";
                    order.orderType = "STP";
                    order.auxPrice = self.buy_stop_level;
                    order.totalQuantity = self.stpamount;
                    self.placeOrder(self.nextOrderId, self.contract, order)
                    self.writeLog(f'Pending Buy {order.totalQuantity}@{order.auxPrice}:{self.nextOrderId}')

                    self.nextOrderId = self.nextOrderId +1
                    self.sell_stop_orderid = self.nextOrderId;
                    order = Order();
                    order.action = "SELL";
                    order.orderType = "STP";
                    order.auxPrice = self.sell_stop_level;
                    order.totalQuantity = self.stpamount;
                    self.placeOrder(self.nextOrderId, self.contract, order)
                    self.writeLog(f'Pending Sell {order.totalQuantity}@{order.auxPrice}:{self.nextOrderId}')

                    self.MAX_Stop_Orders_Per_Day_Counter = self.MAX_Stop_Orders_Per_Day_Counter + 1
                    self.MAX_Stop_Orders_Per_Hour_Counter = self.MAX_Stop_Orders_Per_Hour_Counter+1
                    self.tradeState = 1
                    self.writeLog(f'\nPlaced both stop order\n')
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
        self.writeLog(f'setting nextValidOrderId: {orderId}')
        self.nextOrderId = orderId

    def error(self, reqId, errorCode, errorString):
        if(errorCode<1000 or errorCode>3000):
            self.writeLog(f'{errorString}')

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId,
                    whyHeld, mktCapPrice):
        return;
        #self.writeLog(f'OrderStatus. Id: , {orderId}, Status: , {status}, Filled: , {filled}, Remaining: , {remaining}, LastFillPrice:, {lastFillPrice}')

    def openOrder(self, orderId, contract, order, orderState):
        if(self.tradeState==-1 and contract.symbol==self.contract.symbol):
            self.writeLog(f'Cancel order {orderId}, {contract.symbol}')
            self.cancelOrder(orderId)
        #self.writeLog(f'openOrder id:, {orderId}, {contract.symbol}, {contract.secType}, @, {contract.exchange}, :, {order.action},{order.orderType}, {order.totalQuantity}, {orderState.status}')

    def openOrderEnd(self):
        super().openOrderEnd()
        if(self.tradeState==-1):
            self.reqPositions()
            self.writeLog("Completed to cancel all old order.")

    def position(self, account: str, contract: Contract, position,avgCost: float):
        super().position(account, contract, position, avgCost)
        if(contract.symbol==self.contract.symbol and self.tradeState==-1):
            self.writeLog(f'Close Position. Account:{account} Symbol:{contract.symbol} SecType: {contract.secType} Currency:{contract.currency} Position:{position} Avg cost:{avgCost}')
            if(position!=0.0):
                order = Order()
                order.orderType = "MKT";
                if(position>0):
                    order.action = "SELL";
                    order.totalQuantity = position
                else:
                    order.action = "BUY";
                    order.totalQuantity = -position
                self.nextOrderId = self.nextOrderId +1
                self.placeOrder(self.nextOrderId,self.contract,order)

    def positionEnd(self):
        super().positionEnd()
        if self.tradeState==-1:
            self.tradeState = 0
            self.writeLog("Completed to close all old position.")

    def execDetails(self, reqId, contract, execution):
        #print(execution)
        #self.writeLog(f'Order Executed: ,{ reqId}, {contract.symbol}, {contract.secType}, {contract.currency}, {execution.execId},{execution.orderId}, {execution.shares}, {execution.lastLiquidity},{execution.cumQty}')
        
        if(self.tradeState==1 and (execution.orderId == self.buy_stop_orderid or execution.orderId == self.sell_stop_orderid )):
            if(execution.cumQty<self.stpamount):
                return;
            batchOrder = [];
            self.remainLot = execution.cumQty;#execution.shares
            if(execution.orderId == self.buy_stop_orderid):
                self.cancelOrder(self.sell_stop_orderid)
                self.tradeDirection = 1
                for i in range(len(self.Sell_Limit)):
                    order = Order()
                    order.action = "SELL";
                    order.orderType = "LMT";
                    order.lmtPrice = math.floor(execution.avgPrice*(1+self.Sell_Limit[i]/100)*100)/100;
                    order.totalQuantity = math.floor(self.Sell_Limit_Amt[i]*self.remainLot)
                    batchOrder.append(order)
                order = Order()
                order.action = "SELL";
                order.orderType = "STP";
                order.auxPrice = self.openPrice;
                order.totalQuantity = self.remainLot
                batchOrder.append(order)
            else:
                self.tradeDirection = -1
                self.cancelOrder(self.buy_stop_orderid)
                for i in range(len(self.Buy_Limit)):
                    order = Order()
                    order.action = "BUY";
                    order.orderType = "LMT";
                    order.lmtPrice = math.floor(execution.avgPrice*(1-self.Buy_Limit[i]/100)*100)/100;
                    order.totalQuantity = math.floor(self.Buy_Limit_Amt[i]*self.remainLot)
                    batchOrder.append(order)
                order = Order()
                order.action = "BUY";
                order.orderType = "STP";
                order.auxPrice = self.openPrice;
                order.totalQuantity = self.remainLot
                batchOrder.append(order)
            for o in batchOrder:
                self.nextOrderId = self.nextOrderId +1
                self.placeOrder(self.nextOrderId, self.contract, o)
                if(o.orderType=="LMT"):
                    self.writeLog(f'Pending {o.orderType} {o.totalQuantity}@{o.lmtPrice}:{self.nextOrderId}')
                    self.limiOrderIdList.append(self.nextOrderId)
                else:
                    self.writeLog(f'Pending {o.orderType} {o.totalQuantity}@{o.auxPrice}:{self.nextOrderId}')
                    self.stoplossId = self.nextOrderId
            self.tradeState = 2              
            self.writeLog('sent all limit orders')  
            return
        if(self.tradeState==2):
            limitId = False
            for orderId in self.limiOrderIdList:
                if(orderId==execution.orderId):
                    limitId = True
            if(limitId==False):
                return;
            if(execution.orderId==self.stoplossId):#got stop loss
                for oId in self.limiOrderIdList:
                    self.cancelOrder(oId)
                self.tradeState = 0
                self.remainLot = 0
                self.writeLog('got stoploss,cancel all order and restart')  

            else:
                self.MAX_Stop_Orders_Per_Day_Counter = self.MAX_Stop_Orders_Per_Day_Counter-self.ReduceY
                self.MAX_Stop_Orders_Per_Hour_Counter =self.MAX_Stop_Orders_Per_Hour_Counter-self.ReduceY
                if(self.MAX_Stop_Orders_Per_Day_Counter<0):
                    self.MAX_Stop_Orders_Per_Day_Counter = 0
                if(self.MAX_Stop_Orders_Per_Hour_Counter<0):
                    self.MAX_Stop_Orders_Per_Hour_Counter = 0
                self.remainLot = self.remainLot-execution.shares
                self.writeLog(f'got tp level lot:{execution.shares}')  
                self.cancelOrder(self.stoplossId)
                if(self.remainLot==0.0):
                    self.writeLog(f'Closed all tp orders.')  
                    self.tradeState = 0
                    self.remainLot = 0
                else:
                    self.writeLog(f'Modifying stoploss with remain lot:{self.remainLot}')  
                    self.nextOrderId = self.nextOrderId +1
                    order = Order()
                    order.orderType = "STP";
                    order.auxPrice = self.openPrice
                    order.totalQuantity = self.remainLot
                    if self.tradeDirection==1:
                        order.action = "SELL";
                    else:                    
                        order.action = "BUY";
                    self.writeLog(f'Pending {order.orderType} {order.totalQuantity}@{order.auxPrice}:{self.nextOrderId}')
                    self.placeOrder(self.nextOrderId, self.contract, order)
                    self.stoplossId = self.nextOrderId 
            return

    def start(self):
        print("Started.")
        self.reqMktData(1, self.contract, "", False, False, [])
        return
    
app = IBapi()
app.connect('127.0.0.1', 7497, 123)
# app.connect('95.168.191.114', 7497, 123)
app.start()
app.run()

