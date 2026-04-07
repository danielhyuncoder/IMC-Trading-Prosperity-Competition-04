from datamodel import TradingState, Listing, OrderDepth, Observation, Symbol, Trade, Position
import pandas as pd
import os
from typing import Dict, List
from data_parser import csv_to_trading_states, csv_to_trades, get_all_symbols
from trader import Trader
from dotenv import load_dotenv
from position_limits import position_limits_dict
import matplotlib.pyplot as plt

load_dotenv()


class BacktestingResult:
    def __init__(self, position_history: List[Dict[str, int]], pnl_realized: List[Dict[str, float]], pnl_unrealized: List[Dict[str, float]], fill_rate_history: List[Dict[str, float]], drawdown_history: List[float]):
        self.position_history: List[Dict[str, int]]=position_history
        self.pnl_realized: List[Dict[str, float]]=pnl_realized
        self.pnl_unrealized: List[Dict[str, float]]=pnl_unrealized
        self.currency_medium: str = os.getenv("DENOMINATION", "XIRECS")
        self.fill_ratios = fill_rate_history
        self.drawdown_history=drawdown_history
        self.timestamps: List[int] = [i for i in range(len(self.position_history))]
        # graphing dictionary
        self.graphing_functions = {
            "inventory": self.graph_inventory
        }
        self.available_colors: List[str] =["orange", "green", "purple", "red", "blue", "black", "gray", "cyan"]
        self.colors: Dict[str, str] = {}
        for i, symbol in enumerate(position_history[0]):
            self.colors[symbol]=self.available_colors[i]
        
        self.symbols: List[str] = []
        for symbol in position_history[0]:
            self.symbols.append(symbol)
        
    def set_symbol_colors(self, colors: Dict[str, str]) -> None:
        self.colors=colors
    def graph_inventory(self, graph_alone_flag: bool = True, units: tuple[str] = ("TIMESTAMP", "POSITION AMOUNT"))->None:
        for symbol in self.symbols:
            arr: List[float] = []
            for t in range(len(self.position_history)):
                arr.append(self.position_history[t][symbol])
            plt.plot(self.timestamps, arr, color=self.colors[symbol], label=symbol)
        if graph_alone_flag == True:
            plt.legend()
            plt.xlabel(units[0])
            plt.ylabel(units[1])
            plt.show()
    def graph_fill_ratios(self, graph_alone_flag: bool = True, units: tuple[str] = ("TIMESTAMP", "RATIO"))->None:
        for symbol in self.symbols:
            arr: List[float] = []
            for t in range(len(self.fill_ratios)):
                arr.append(self.fill_ratios[t][symbol])
            plt.plot(self.timestamps, arr, color=self.colors[symbol], label=symbol)
        if graph_alone_flag == True:
            plt.legend()
            plt.xlabel(units[0])
            plt.ylabel(units[1])
            plt.show()
    def graph_drawdown(self, graph_alone_flag: bool = True) -> None:
        plt.plot(self.timestamps, self.drawdown_history, color="red", label="Drawdown in " + self.currency_medium + "")
        if graph_alone_flag == True:
            plt.legend()
            plt.xlabel("TIMESTAMP")
            plt.ylabel(self.currency_medium)
            plt.show()
    def graph_pnl(self, exclude_other_pnl: bool = True, colors: tuple[str] = ("green", "purple", "blue"), graph_alone_flag: bool = True)->None:
        r_pnl: List[float] = []
        t_pnl: List[float] = []
        u_pnl: List[float] = []
        for t in range(len(self.position_history)):
            r_pnl_sum: float = 0
            u_pnl_sum: float = 0
            for symbol in self.symbols:
               r_pnl_sum+=self.pnl_realized[t][symbol]
               u_pnl_sum+=self.pnl_unrealized[t][symbol]
            r_pnl.append(r_pnl_sum)
            u_pnl.append(u_pnl_sum)
            t_pnl.append(r_pnl_sum+u_pnl_sum)
        
        
        plt.plot(self.timestamps, t_pnl, color=colors[1], label="Total PNL")
        if exclude_other_pnl == False:
            plt.plot(self.timestamps, r_pnl, color=colors[0], label="Total Realized PNL")
            plt.plot(self.timestamps, u_pnl, color=colors[2], label="Total Unrealized PNL")
        if graph_alone_flag == True:
            plt.legend()
            plt.xlabel("TIMESTAMP")
            plt.ylabel(self.currency_medium)
            plt.show()
    
    def output_graphs(self, func_list: List[str]) -> None:
        pass
    def __str__(self) -> str:
        return "BACKTESTING RESULT OF " + str(len(self.position_history)) + " UNIQUE TIMESTAMPS."