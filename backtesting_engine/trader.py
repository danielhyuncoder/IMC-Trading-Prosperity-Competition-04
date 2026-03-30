from datamodel import TradingState, Listing, OrderDepth, Observation, Order
import pandas as pd
import os
from typing import Dict, List
from data_parser import csv_to_trading_states
from dotenv import load_dotenv

load_dotenv()

class Trader:
    def bid(self):
        return 0
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        return {}, 0, ""
