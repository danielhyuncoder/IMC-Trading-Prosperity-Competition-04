import pandas as pd
import numpy as np 
from scipy.stats import norm

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

@np.vectorize
def norm_cdf_fast(x):

    k = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = k * (0.319381530 + k * (-0.356563782 +
           k * (1.781477937 + k * (-1.821255978 + 1.330274429 * k))))
    w = 1.0 - (1.0 / np.sqrt(2*np.pi)) * np.exp(-0.5 * x * x) * poly
    return w if x >= 0 else 1 - w

def black_scholes_call(spot, strike, t, vol, r=0.0):
    sqrt_t = np.sqrt(t)
    d1 = (np.log(spot/strike) + (r + 0.5*vol*vol)*t) / (vol*sqrt_t)
    d2 = d1 - vol*sqrt_t
    return spot * norm_cdf_fast(d1) - strike * np.exp(-r*t) * norm_cdf_fast(d2)


def implied_vol_bisection(spot, strike, price, t, tol=1e-6, max_iter=50):
    low, high = 0, 5.0

    for _ in range(max_iter):
        mid = (low + high)/2
        est = black_scholes_call(spot, strike, t, mid)

        if abs(est - price) < tol:
            return mid

        if est > price:
            high = mid
        else:
            low = mid

    return mid

def compute_iv_column(opt):
    strikes = opt["strike"].to_numpy()
    spots   = opt["spot_price"].to_numpy()
    mids    = opt["mid_price"].to_numpy()
    ttes    = opt["time_to_expiry"].to_numpy()

    ivs = np.empty(len(opt))

    for i in range(len(opt)):
        ivs[i] = implied_vol_bisection(spots[i], strikes[i], mids[i], ttes[i])

    return ivs

def get_options_df(prices_df: pd.DataFrame,
                   amount_of_days: int,
                   underlying_asset: str,
                   options_contracts: list[str]) -> pd.DataFrame:

    max_expiry = amount_of_days * 1_000_000

    opt = prices_df.loc[prices_df["product"].isin(options_contracts)].copy()

    opt["strike"] = opt["product"].str.rsplit("_", n=1).str[-1].astype(int)
    opt["time_to_expiry"] = (max_expiry - opt["timestamp"]) / 365e6
    
    under = (
        prices_df.loc[prices_df["product"] == underlying_asset,
                      ["timestamp", "mid_price"]]
        .rename(columns={"mid_price": "spot_price"})
    )

    opt = opt.merge(under, on="timestamp", how="left")


    opt["implied_volatility"] = compute_iv_column(opt)
    return opt[["timestamp", "time_to_expiry", "spot_price", "strike", "mid_price", "implied_volatility"]]
