from datamodel import TradingState, Listing, OrderDepth, Observation, Trade
import pandas as pd
import os
from typing import Dict, List
from dotenv import load_dotenv
IGNORE_COLS = {"mid_price", "product", "profit_and_loss", "buyer", "seller", "symbol"}
load_dotenv()

def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.iloc[:, 0].str.split(";", expand=True)
    df.columns = raw_df.columns[0].split(";")
    df = df.replace("", 0)
    
    if "buyer" in df.columns:
      DENOMINATION = os.getenv("DENOMINATION", "XIRECS")
      df["buyer"].replace(0, "", inplace=True)
      df["seller"].replace(0, "", inplace=True)
      df["currency"].replace(0, DENOMINATION, inplace=True)
    for col in df.columns:
        if col not in IGNORE_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df

def get_all_symbols(file_path: str) -> List[str]:
    try:
        raw_df = clean_df(pd.read_csv(file_path))
    except Exception as e:
        raise Exception(f"File cannot be read: {e}")
    return raw_df["product"].unique()

def csv_to_trades(file_path: str) -> List[Trade]:
    try:
        raw_df = pd.read_csv(file_path)
    except Exception as e:
        raise Exception(f"File cannot be read: {e}")

    df = clean_df(raw_df)

    ans: List[Trade] = []

    for timestamp, timestamp_df in df.groupby("timestamp", sort=True):
        row = timestamp_df.iloc[0]
        ans.append(Trade(row["symbol"], row["price"], row["quantity"], row["buyer"], row["seller"], timestamp))

    return ans

def csv_to_trading_states(file_path: str) -> List[TradingState]:
    try:
        raw_df = pd.read_csv(file_path)
    except Exception as e:
        raise Exception(f"File cannot be read: {e}")

    df = clean_df(raw_df)

    DENOMINATION = os.getenv("DENOMINATION", "XIRECS")
    OB_RANGE = int(os.getenv("OB_RANGE", 2))

    ans: List[TradingState] = []

    for timestamp, timestamp_df in df.groupby("timestamp", sort=True):
        listings: Dict[str, Listing] = {}
        order_depths: Dict[str, OrderDepth] = {}

        for symbol, row_df in timestamp_df.groupby("product"):
            row = row_df.iloc[0]

            listings[symbol] = Listing(symbol, symbol, DENOMINATION)
            order_depth = OrderDepth()

            for i in range(1, OB_RANGE + 1):
                bid_price = row.get(f"bid_price_{i}", 0)
                bid_volume = row.get(f"bid_volume_{i}", 0)
                ask_price = row.get(f"ask_price_{i}", 0)
                ask_volume = row.get(f"ask_volume_{i}", 0)

                if bid_price > 0 and bid_volume > 0:
                    order_depth.buy_orders[int(bid_price)] = int(bid_volume)
                if ask_price > 0 and ask_volume > 0:
                    order_depth.sell_orders[int(ask_price)] = -int(ask_volume)

            order_depths[symbol] = order_depth

        ans.append(
            TradingState(
                traderData="",
                timestamp=int(timestamp),
                listings=listings,
                order_depths=order_depths,
                own_trades={},
                market_trades={},
                position={},
                observations=Observation({}, {}),
            )
        )

    return ans

def group_to_trading_states(group: List[str]) -> List[TradingState]:
    trading_states: List[TradingState] = []
    last:int = 0
    
    for ix in range(len(group)):
        t_states: List[TradingState] = csv_to_trading_states(group[ix])
        last_ts: int = t_states[len(t_states)-1].timestamp
        for st in t_states:
            st.timestamp+=last
            trading_states.append(st)
        last+=last_ts+100
    return trading_states

def group_to_trades(group: List[str], inc: int) -> List[Trade]:
    trades: List[Trade] = []
    last:int = 0
    for ix in range(len(group)):
        t_trades: List[Trade] = csv_to_trades(group[ix])
        for st in t_trades:
            st.timestamp+=last
            trades.append(st)
        last+=inc
    return trades
