from datamodel import TradingState, Listing, OrderDepth, Observation, Symbol, Trade, Position
import pandas as pd
import os
from typing import Dict, List
from data_parser import csv_to_trading_states, csv_to_trades, get_all_symbols, group_to_trades, group_to_trading_states
from trader import Trader
from dotenv import load_dotenv
from position_limits import position_limits_dict
from visualizer import BacktestingResult
import math
import numpy as np
import random
import copy
load_dotenv()


class Backtester:
    def __init__(self, order_book_csv_name: list | str, trades_csv_name: list | str):
        if type(order_book_csv_name) == list:
            if type(trades_csv_name) != list:
                raise Exception("If one parameter is a list, the other must be too. Prevents double counting liquidity.")
            if len(order_book_csv_name) != len(trades_csv_name):
                raise Exception("Both the number of order book csv files and trades csv files must be the same.")
            self.trading_states: List[TradingState] = group_to_trading_states(order_book_csv_name)
            self.trades: List[Trade] = group_to_trades(trades_csv_name, 1000000)
            self.symbols= get_all_symbols(order_book_csv_name[0])
        else:
            self.trading_states = csv_to_trading_states(order_book_csv_name)
            self.trades = csv_to_trades(trades_csv_name)
            self.symbols= get_all_symbols(order_book_csv_name)
        self.trades.sort(key=lambda t: t.timestamp)

        # Probabilistic fill settings
        self.edge_limit: int = 2
        self.k: float = 0.8
        self.fill_min: float = 0.1
        self.fill_max: float = 0.2
        self.shifter: float = 1.5
        self.default_tick: int = 1
        self.tick_sizes: Dict[str, int] = {
            "EMERALDS": 1,
            "TOMATOES": 1
        }
        self.custom_shifter: Dict[str, float] ={
            "EMERALDS": 1,
            "TOMATOES": 1.5
        
        }
        self.alpha: float = 0.2
        self.p: float = 0.2
        self.new_weight: float = 0.1
        self.microvol: Dict[str, float] = {}
        self.ema_per_symbol: Dict[str, float] = {}
        
        for symbol in self.symbols:
            self.ema_per_symbol[symbol]=-1
            self.microvol[symbol]=1
    def include_observations(self, observation_csv_name:str):
        pass
    def get_fill_probability(self, edge: int, symbol: str, obi_ratio: float) -> float:
        return (1 / (1 + math.exp(-(self.k * (min(5, edge)-self.custom_shifter.get(symbol, self.shifter)))))) * obi_ratio
    def get_def_probability(self, edge:int, symbol: str) -> float:
        return (1 / (1 + math.exp(-(self.k * (min(5, edge)-self.custom_shifter.get(symbol, self.shifter))))))
    def get_fill_amount(self, edge: int, symbol: str, obi_ratio: float) -> float:
        rng: float = random.uniform(self.fill_min, self.fill_max)
        edge_aspect: float = self.get_def_probability(edge, symbol)
        return rng*edge_aspect
    def get_predicted_volume(self, fill_fraction: float) ->int:
        return int(fill_fraction*np.random.geometric(p=self.p))
    def run_trader(self, trader: Trader, enable_probabilistic_fills: bool = False, enable_market_trades: bool = True) -> BacktestingResult:
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
            # Update microvolatility
            
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
                
                long_denominator: float = 0.0
                short_denominator: float = 0.0

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
                buy_side_qty: int = 0
                asks_side_qty: int = 0
                for price_level in state.order_depths[symbol].sell_orders:
                    asks_sorted.append([price_level, state.order_depths[symbol].sell_orders[price_level]])
                    asks_side_qty+=abs(state.order_depths[symbol].sell_orders[price_level])

                for price_level in state.order_depths[symbol].buy_orders:
                    bids_sorted.append([price_level, state.order_depths[symbol].buy_orders[price_level]])
                    buy_side_qty += state.order_depths[symbol].buy_orders[price_level]
                
                market_trades_bids_sorted=[]
                market_trades_asks_sorted=[]
                if enable_market_trades:
                    for m_t in state.market_trades[symbol]:
                        market_trades_bids_sorted.append([m_t.price, m_t.quantity])
                        market_trades_asks_sorted.append([m_t.price, -m_t.quantity])
                    market_trades_asks_sorted.sort()
                    market_trades_bids_sorted.sort(reverse=True)
                
                asks_sorted.sort()
                bids_sorted.sort(reverse=True)
                old_quantity = position[symbol]
                
                # Update microvolatility for taker behavior
                mid_price:float = (bids_sorted[0][0]+asks_sorted[0][0])/2
                OBI:float = (buy_side_qty-asks_side_qty) / (buy_side_qty+asks_side_qty)
                if self.ema_per_symbol[symbol]==-1:
                    self.ema_per_symbol[symbol]=mid_price
                else:
                    self.ema_per_symbol[symbol] = self.alpha * mid_price + (1 - self.alpha) * self.ema_per_symbol[symbol]
                
                self.microvol[symbol]=(1-self.new_weight) * self.microvol[symbol] + self.new_weight * abs(mid_price - self.ema_per_symbol[symbol])
                

                for order in result[symbol]:
                    if order.quantity < 0: #short
                        #check limit enforcement
                        
                        if old_quantity - short_sum < -position_limits_dict.get(symbol, 80):
                            continue
                        total_request = abs(order.quantity)
                        ratio_denominator+=total_request

                        
                        # aggressive fills
                        while total_request > 0 and len(bids_sorted) != 0 and bids_sorted[0][0] >= order.price:
                             delta = min(bids_sorted[0][1], total_request)
                             total_request-=delta
                             bids_sorted[0][1]-=delta
                             position[symbol]-=delta 
                             own_trades[symbol].append(Trade(symbol, bids_sorted[0][0], -delta, "", "SUBMISSION", state.timestamp))
                             if bids_sorted[0][1] <= 0:
                                del bids_sorted[0]
                        # passive fills
                        for mt in market_trades_bids_sorted:
                            
                            if mt[0] >= order.price and mt[1]>0:
          
                                delta = min(total_request, mt[1])
                                total_request -= delta
                                mt[1] -= delta
                                position[symbol] -= delta
                                own_trades[symbol].append(Trade(symbol, mt[0], -delta, "", "SUBMISSION", state.timestamp))
                            else:
                                break

                        fill_ratios[symbol]+=abs(order.quantity)-total_request
                        short_denominator+=abs(order.quantity)-total_request

                        # short probablistic fill
                        if enable_probabilistic_fills and len(asks_sorted) != 0 and total_request >0:
                            best_ask = asks_sorted[0][0]
                            edge = (best_ask-order.price) / self.tick_sizes.get(symbol, self.default_tick)
                            
                            if edge <= -self.edge_limit: # too far
                                continue
                            #apply norm on edge:
                            edge/=max(self.microvol[symbol], 1)
                            # probability (shifted logistic)
                            fill_prob = self.get_fill_probability(edge, symbol, 0.5-(OBI/2))
                            if random.random() < fill_prob:
                                fill_fraction = self.get_fill_amount(edge, symbol, 0.5-(OBI/2))
                                reaching_volume = self.get_predicted_volume(fill_fraction)
        
                                delta = min(abs(reaching_volume), total_request)
                                total_request -= delta
                                position[symbol] -= delta

                                own_trades[symbol].append(
                                    Trade(symbol, order.price, -delta, "", "SUBMISSION", state.timestamp)
                                )
                                short_denominator+=delta
                                fill_ratios[symbol] += delta
                    else: #long
                        #check limit enforcement
                        if old_quantity + long_sum > position_limits_dict.get(symbol, 80):
                            continue
                        
                        total_request = order.quantity
                        ratio_denominator+=total_request
                        
            

                        # aggressive fills
                        while total_request > 0 and len(asks_sorted) != 0 and asks_sorted[0][0] <= order.price:
                             delta = min(abs(asks_sorted[0][1]), total_request)
                             total_request-=delta
                             asks_sorted[0][1]+=delta
                             position[symbol]+=delta 
                             own_trades[symbol].append(Trade(symbol, asks_sorted[0][0], delta, "SUBMISSION", "", state.timestamp))
                             if asks_sorted[0][1] >= 0:
                                del asks_sorted[0]
                        #passive fills
                        for mt in market_trades_asks_sorted:
                            if mt[0] <= order.price and mt[1] < 0:
                                delta = min(total_request, abs(mt[1]))
                                total_request -= delta
                                mt[1] += delta
                                position[symbol] += delta
                                own_trades[symbol].append(Trade(symbol, mt[0], delta, "SUBMISSION", "", state.timestamp))
                                
                            else:
                                break
                        
                        fill_ratios[symbol]+=order.quantity-total_request
                        long_denominator+=order.quantity-total_request
                        # long probablistic fill
                        if enable_probabilistic_fills and len(bids_sorted) != 0 and total_request >0:

                            best_bid = bids_sorted[0][0]
                            edge = (order.price - best_bid) / self.tick_sizes.get(symbol, self.default_tick)

                            if edge <= -self.edge_limit: # too far
                                continue
                            #apply norm on edge:
                            edge/=max(1,self.microvol[symbol])
                            fill_prob = self.get_fill_probability(edge, symbol, 0.5+(OBI/2))

                            if random.random() < fill_prob:
                                fill_fraction = self.get_fill_amount(edge, symbol, 0.5+(OBI/2))
                                reaching_volume = self.get_predicted_volume(fill_fraction)
   
                                #if reaching_volume
                                delta = min(reaching_volume, total_request)
                                total_request -= delta
                                position[symbol] += delta

                                own_trades[symbol].append(
                                    Trade(symbol, order.price, delta, "SUBMISSION", "", state.timestamp)
                                )
                                long_denominator+=delta

                                fill_ratios[symbol] += delta
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
            

            

