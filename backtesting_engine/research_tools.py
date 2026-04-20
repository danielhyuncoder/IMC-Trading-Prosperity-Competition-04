import pandas as pd
import numpy as np 

def get_synthetic_basket_prices(prices_df: pd.DataFrame, items: list[tuple[str | float]]) -> np.array:
    item_matrix = []
    if "mid_price" not in prices_df.columns or "product" not in prices_df.columns:
        raise Exception("Prices DataFrame MUST include mid_price as a column.")
    for item in items:
        item_matrix.append(prices_df.loc[prices_df["product"] == item[0]]["mid_price"].to_numpy().astype(float) * item[1])
    
    base_arr: np.array = item_matrix[0]
    for i in range(1, len(item_matrix)):
        base_arr+=item_matrix[i]
    return base_arr