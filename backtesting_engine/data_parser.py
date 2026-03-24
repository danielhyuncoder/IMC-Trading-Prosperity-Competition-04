from datamodel import TradingState, Listing, OrderDepth, Observation
import pandas as pd
import os
from typing import Dict, List

IGNORE_COLS = {"mid_price", "product", "profit_and_loss"}

def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.iloc[:, 0].str.split(";", expand=True)
    df.columns = raw_df.columns[0].split(";")
    df = df.replace("", 0)
    for col in df.columns:
        if col not in IGNORE_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df

def csv_to_trading_states(file_path: str) -> List[TradingState]:
    try:
        raw_df = pd.read_csv(file_path)
    except Exception as e:
        raise Exception(f"File cannot be read: {e}")

    df = clean_df(raw_df)

    DENOMINATION = os.getenv("DENOMINATION", "USD")
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
                    order_depth.sell_orders[int(ask_price)] = int(ask_volume)

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