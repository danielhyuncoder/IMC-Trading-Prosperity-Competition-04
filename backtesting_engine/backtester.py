from datamodel import TradingState, Listing, OrderDepth, Observation, Symbol, Trade, Position
import pandas as pd
import os
from typing import Dict, List
from data_parser import csv_to_trading_states, csv_to_trades, get_all_symbols
from trader import Trader
from dotenv import load_dotenv
from position_limits import position_limits_dict
from visualizer import BacktestingResult
load_dotenv()


class Backtester:
    def __init__(self, order_book_csv_name: str, trades_csv_name: str):
        self.trading_states = csv_to_trading_states(order_book_csv_name)
        self.symbols= get_all_symbols(order_book_csv_name)
        self.trades = csv_to_trades(trades_csv_name)
        self.trades.sort(key=lambda t: t.timestamp)
    def include_observations(self, observation_csv_name:str):
        pass
    def run_trader(self, trader: Trader) -> BacktestingResult:
        own_trades: Dict[Symbol, List[Trade]] = {}
        market_trades: Dict[Symbol, List[Trade]] = {}
        position: Dict[Symbol, Position] = {}
        traderData: str = ""
        trade_ptr: int = 0

        # BACKTESTER METRICS 
        pnl_realized: List[Dict[str: float]] = []
        pnl_unrealized: List[Dict[str: float]] = []
        position_history: List[Dict[str, int]] = []
        fill_rate_history: List[Dict[str, float]] = []
        drawdown_history: List[float] = []
        cash = {symbol: 0 for symbol in self.symbols}

        # BACKTESTER LOGIC
        peak_pnl: float = 0
        for symbol in self.symbols:
            own_trades[symbol] = []
            market_trades[symbol] = []
            position[symbol] = 0
        
        for trading_state in self.trading_states:
            state: TradingState = trading_state
            state.traderData = traderData
            state.position=position.copy()
            state.own_trades={k: v[:] for k, v in own_trades.items()}
            state.market_trades={k: v[:] for k, v in market_trades.items()}
            result, conversion, next_trader_data = trader.run(state)
            fill_ratios:Dict[str, float] = {}
            # Error catch result (make sure its in the proper return format, as listed in the IMC Prosperity docs)
            for symbol in self.symbols:
                try:
                    result[symbol]
                except:
                    raise Exception("Returned result from Trader.run() is in the incorrect format. (Potentially missing a symbol(s))")
            #Err check (check if orders placed)
            '''
            anyPlaced=False
            for symbol in self.symbols:
                if len(result[symbol])>0:
                    anyPlaced=True
            if anyPlaced:
                print("PLACED ORDERS @ " + str(trading_state.timestamp))
            '''
            # Update own_trades, Fill Orders, Update position, traderData
            traderData=next_trader_data
            # Reset own and market trades
            for symbol in self.symbols:
               own_trades[symbol] = []
               market_trades[symbol] = []
            # update market trades
            while trade_ptr<len(self.trades) and self.trades[trade_ptr].timestamp == state.timestamp:
                market_trades[self.trades[trade_ptr].symbol].append(self.trades[trade_ptr])
                trade_ptr+=1
            
            
            # Update positions & fill orders
            for symbol in self.symbols:
                # check position limits first
                fill_ratios[symbol]=0.0
                ratio_denominator: float = 0.0
                long_sum: float=0
                short_sum:float=0
                for order in result[symbol]:
                    if order.quantity>0:
                       long_sum+=order.quantity
                    else:
                       short_sum+=abs(order.quantity)
                # Create mini order book
                asks_sorted=[]
                bids_sorted=[]
                for price_level in state.order_depths[symbol].sell_orders:
                    asks_sorted.append([price_level, state.order_depths[symbol].sell_orders[price_level]])

                for price_level in state.order_depths[symbol].buy_orders:
                    bids_sorted.append([price_level, state.order_depths[symbol].buy_orders[price_level]])
             

                asks_sorted.sort()
                bids_sorted.sort(reverse=True)
                old_quantity = position[symbol]
                
                for order in result[symbol]:
                    if order.quantity < 0: #short
                        #check limit enforcement
                        if old_quantity + short_sum > position_limits_dict[symbol]:
                            continue
                        total_request = abs(order.quantity)
                        ratio_denominator+=total_request
                        while total_request > 0 and len(bids_sorted) != 0 and bids_sorted[0][0] >= order.price:
                             delta = min(bids_sorted[0][1], total_request)
                             total_request-=delta
                             bids_sorted[0][1]-=delta
                             position[symbol]-=delta 
                             own_trades[symbol].append(Trade(symbol, bids_sorted[0][0], -delta, "", "SUBMISSION", state.timestamp))
                             if bids_sorted[0][1] == 0:
                                del bids_sorted[0]
                        fill_ratios[symbol]+=abs(order.quantity)-total_request
                    else: #long
                        #check limit enforcement
                        if old_quantity + long_sum > position_limits_dict[symbol]:
                            continue
                        total_request = order.quantity
                        ratio_denominator+=total_request
                        while total_request > 0 and len(asks_sorted) != 0 and asks_sorted[0][0] <= order.price:
                             delta = min(abs(asks_sorted[0][1]), total_request)
                             total_request-=delta
                             asks_sorted[0][1]+=delta
                             position[symbol]+=delta 
                             own_trades[symbol].append(Trade(symbol, asks_sorted[0][0], delta, "SUBMISSION", "", state.timestamp))
                             if asks_sorted[0][1] == 0:
                                del asks_sorted[0]
                        fill_ratios[symbol]+=order.quantity-total_request
                fill_ratios[symbol]/=max(1,ratio_denominator) # div by zero err
            t_pnl:float = 0
            for symbol in self.symbols:
                for trade in own_trades[symbol]:
                    if trade.buyer == "SUBMISSION":
                        cash[symbol] -= trade.quantity * trade.price
                    else:
                        cash[symbol] += abs(trade.quantity) * trade.price
            
            for symbol in self.symbols:
                t_pnl+=cash[symbol]
            
                
            # Computing PNL (Going to change in the future)
            current_pnl = {}
            for symbol in self.symbols:
                mid_price = None
                bids = state.order_depths[symbol].buy_orders
                asks = state.order_depths[symbol].sell_orders
                if bids and asks:
                    mid_price = (max(bids) + min(asks)) / 2
                elif bids:
                    mid_price = max(bids)
                elif asks:
                    mid_price = min(asks)
                else:
                    mid_price = 0

                current_pnl[symbol] = position[symbol] * mid_price
                t_pnl+=current_pnl[symbol]
            # Push metrics
            pnl_unrealized.append(current_pnl)
            pnl_realized.append(cash.copy())
            position_history.append(position.copy())
            fill_rate_history.append(fill_ratios)
            peak_pnl = max(t_pnl, peak_pnl)
            drawdown_history.append(peak_pnl-t_pnl)
            
        return BacktestingResult(position_history, pnl_unrealized, pnl_realized, fill_rate_history, drawdown_history)
            

            

