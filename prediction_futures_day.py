# -*- coding: utf-8 -*-
"""
prediction_futures_day.py

Description:
    Predicts future daily K-line (1D) data for Chinese futures markets using Kronos model and akshare.
    The script automatically downloads the latest historical data, cleans it, and runs model inference.

Usage:
    python prediction_futures_day.py --symbol RB0
    python prediction_futures_day.py --symbol AU0 --pred_len 20
    python prediction_futures_day.py --symbol SC0 --no_limit

Arguments:
    --symbol     Futures contract code. Use suffix '0' for dominant contract, e.g.:
                   RB0  螺纹钢主力   AU0  黄金主力   CU0  铜主力
                   IF0  沪深300股指  SC0  原油       M0   豆粕主力
    --pred_len   Number of trading days to predict (default: 30)
    --lookback   Number of historical days as context (default: 200)
    --no_limit   Disable price limit clamping (useful for crypto or foreign futures)

Output:
    - Saves prediction results to ./outputs/pred_<symbol>_data.csv
    - Saves chart to ./outputs/pred_<symbol>_chart.png

Example:
    python3 prediction_futures_day.py --symbol RB0
    python3 prediction_futures_day.py --symbol IF0 --pred_len 15
"""

import os
import re
import sys
import time
import argparse

import pandas as pd
import akshare as ak
import matplotlib.pyplot as plt

sys.path.append("../")
from model import Kronos, KronosTokenizer, KronosPredictor

# ── Model settings ───────────────────────────────────────────────────────────
TOKENIZER_PRETRAINED = "NeoQuasar/Kronos-Tokenizer-base"
MODEL_PRETRAINED = "NeoQuasar/Kronos-small"
DEVICE = "cpu"          # Change to "cuda:0" if GPU is available
MAX_CONTEXT = 512
T = 1.0
TOP_P = 0.9
SAMPLE_COUNT = 1

# ── Price limit table (涨跌停幅度) ────────────────────────────────────────────
# None means no limit (crypto, foreign futures, etc.)
LIMIT_RATE_MAP = {
    # 股指/国债期货 CFFEX
    "IF": 0.10, "IH": 0.10, "IC": 0.10, "IM": 0.10,
    "T":  0.02, "TF": 0.015, "TS": 0.005,
    # 金属 SHFE
    "CU": 0.05, "AL": 0.05, "ZN": 0.05, "PB": 0.05,
    "AU": 0.05, "AG": 0.05, "SN": 0.05, "NI": 0.06,
    "RB": 0.05, "HC": 0.05, "SS": 0.06, "BC": 0.05, "WR": 0.05,
    # 能源化工 SHFE/INE
    "FU": 0.06, "RU": 0.05, "BU": 0.06, "SP": 0.06,
    "SC": 0.05, "LU": 0.05, "NR": 0.06,
    # 农产品 DCE
    "C":  0.04, "CS": 0.04, "A":  0.04, "B":  0.04,
    "M":  0.04, "Y":  0.04, "P":  0.04, "JD": 0.04,
    "L":  0.05, "PP": 0.06, "I":  0.06, "J":  0.06,
    "JM": 0.06, "EG": 0.06, "EB": 0.06, "PG": 0.06, "LH": 0.05,
    # 郑商所 CZCE
    "SR": 0.05, "CF": 0.05, "WH": 0.04, "PM": 0.04, "RI": 0.04,
    "RS": 0.05, "RM": 0.04, "OI": 0.05, "TA": 0.05, "FG": 0.06,
    "MA": 0.05, "SA": 0.05, "ZC": 0.05, "AP": 0.05, "CJ": 0.05, "PF": 0.06,
    # 广期所 GFEX
    "SI": 0.05, "LC": 0.05,
}

save_dir = "./outputs"
os.makedirs(save_dir, exist_ok=True)


def get_product_code(symbol: str) -> str:
    """Extract product letters from a contract code, e.g. 'RB2501' -> 'RB', 'RB0' -> 'RB'."""
    m = re.match(r'^([A-Za-z]+)', symbol)
    return m.group(1).upper() if m else symbol.upper()


def load_data(symbol: str) -> pd.DataFrame:
    print(f"Fetching {symbol} daily data from akshare ...")

    df = None
    for attempt in range(1, 4):
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df is not None and not df.empty:
                break
        except Exception as e:
            print(f"  Attempt {attempt}/3 failed: {e}")
        time.sleep(1.5)

    if df is None or df.empty:
        print(f"Failed to fetch data for {symbol}. Exiting.")
        sys.exit(1)

    # Normalize column names
    df.rename(columns={
        "date":   "date",
        "open":   "open",
        "high":   "high",
        "low":    "low",
        "close":  "close",
        "volume": "volume",
        "hold":   "amount",    # open interest as amount proxy
    }, inplace=True)

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    numeric_cols = ["open", "high", "low", "close", "volume", "amount"]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
            continue
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .replace({"--": None, "": None})
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fix invalid open values
    bad_open = (df["open"] == 0) | df["open"].isna()
    if bad_open.any():
        print(f"  Fixed {bad_open.sum()} invalid open values.")
        df.loc[bad_open, "open"] = df["close"].shift(1)
        df["open"].fillna(df["close"], inplace=True)

    # Fill missing amount with volume as fallback
    if df["amount"].isna().all() or (df["amount"] == 0).all():
        df["amount"] = df["volume"]

    df = df.dropna(subset=["close"]).reset_index(drop=True)

    print(f"Data loaded: {len(df)} rows, {df['date'].min().date()} ~ {df['date'].max().date()}")
    return df


def prepare_inputs(df: pd.DataFrame, lookback: int, pred_len: int):
    x_df = df.iloc[-lookback:][["open", "high", "low", "close", "volume", "amount"]]
    x_timestamp = df.iloc[-lookback:]["date"]
    y_timestamp = pd.bdate_range(
        start=df["date"].iloc[-1] + pd.Timedelta(days=1),
        periods=pred_len
    )
    return x_df, pd.Series(x_timestamp.values), pd.Series(y_timestamp)


def apply_price_limits(pred_df: pd.DataFrame, last_close: float, limit_rate: float) -> pd.DataFrame:
    pred_df = pred_df.reset_index(drop=True)
    cols = ["open", "high", "low", "close"]
    pred_df[cols] = pred_df[cols].astype("float64")

    for i in range(len(pred_df)):
        limit_up   = last_close * (1 + limit_rate)
        limit_down = last_close * (1 - limit_rate)
        for col in cols:
            v = pred_df.at[i, col]
            if pd.notna(v):
                pred_df.at[i, col] = float(max(min(v, limit_up), limit_down))
        last_close = float(pred_df.at[i, "close"])

    return pred_df


def plot_result(df_hist: pd.DataFrame, df_pred: pd.DataFrame, symbol: str):
    plt.figure(figsize=(12, 6))
    plt.plot(df_hist["date"], df_hist["close"], label="Historical", color="blue", linewidth=1.5)
    plt.plot(df_pred["date"], df_pred["close"],  label="Predicted",  color="red",  linewidth=1.5, linestyle="--")
    plt.title(f"Kronos Futures Prediction — {symbol}")
    plt.xlabel("Date")
    plt.ylabel("Close Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plot_path = os.path.join(save_dir, f"pred_{symbol}_chart.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"Chart saved: {plot_path}")


def predict_future(symbol: str, lookback: int, pred_len: int, no_limit: bool):
    print(f"Loading Kronos tokenizer:{TOKENIZER_PRETRAINED} model:{MODEL_PRETRAINED} ...")
    tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_PRETRAINED)
    model     = Kronos.from_pretrained(MODEL_PRETRAINED)
    predictor = KronosPredictor(model, tokenizer, device=DEVICE, max_context=MAX_CONTEXT)

    df = load_data(symbol)
    if len(df) < lookback:
        print(f"Warning: only {len(df)} rows available, reducing lookback to {len(df)}.")
        lookback = len(df)

    x_df, x_timestamp, y_timestamp = prepare_inputs(df, lookback, pred_len)

    print(f"Generating {pred_len}-day prediction for {symbol} ...")
    pred_df = predictor.predict(
        df=x_df,
        x_timestamp=x_timestamp,
        y_timestamp=y_timestamp,
        pred_len=pred_len,
        T=T,
        top_p=TOP_P,
        sample_count=SAMPLE_COUNT,
    )
    pred_df["date"] = y_timestamp.values

    # Apply price limits
    if no_limit:
        print("Price limit disabled (--no_limit).")
    else:
        product = get_product_code(symbol)
        limit_rate = LIMIT_RATE_MAP.get(product)
        if limit_rate is None:
            print(f"No price limit configured for {product}, skipping clamping.")
        else:
            print(f"Applying ±{limit_rate*100:.1f}% price limit for {product} ...")
            last_close = float(df["close"].iloc[-1])
            pred_df = apply_price_limits(pred_df, last_close, limit_rate)

    # Merge and save
    df_out = pd.concat([
        df[["date", "open", "high", "low", "close", "volume", "amount"]],
        pred_df[["date", "open", "high", "low", "close", "volume", "amount"]],
    ]).reset_index(drop=True)

    out_csv = os.path.join(save_dir, f"pred_{symbol}_data.csv")
    df_out.to_csv(out_csv, index=False)
    print(f"Prediction saved: {out_csv}")

    plot_result(df.tail(lookback).reset_index(drop=True), pred_df, symbol)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kronos futures daily prediction")
    parser.add_argument("--symbol",   type=str, default="RB0",
                        help="Futures contract code (e.g. RB0, AU0, IF0, SC0)")
    parser.add_argument("--pred_len", type=int, default=30,
                        help="Number of trading days to predict (default: 30)")
    parser.add_argument("--lookback", type=int, default=200,
                        help="Historical days as model context (default: 200)")
    parser.add_argument("--no_limit", action="store_true",
                        help="Disable price limit clamping")
    args = parser.parse_args()

    predict_future(
        symbol=args.symbol,
        lookback=args.lookback,
        pred_len=args.pred_len,
        no_limit=args.no_limit,
    )
