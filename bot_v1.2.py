import random
import subprocess
import threading
import time
import numpy as np
from subprocess import DEVNULL, STDOUT
import pandas as pd
import ta
from binance import Client
from binance.enums import HistoricalKlinesType
from termcolor import colored

# Path to your config
config_live_path = "configs/live/test/live_config.json"

# Leverage
leverage = "12"

# Wallet Exposure Long | Short
we_long = "0.1"
we_short = "0.1"

# Interval to Trade Whatever
interval = "1m"
time_wait_ask = random.randint(30, 50)

# Limit for Indicators
# limit = 69

class Bot_Stoch_RSI_MACD:
    def __init__(self, binance_client, symbol, interval, limit):
        self.binance_client = binance_client
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        print(colored(f"Bot {symbol} initiated", "cyan"))

    def dfall(self):
        bars = binance_client.get_historical_klines(
            self.symbol, interval=self.interval, limit=self.limit, klines_type=HistoricalKlinesType.FUTURES)

        df = pd.DataFrame(bars)
        df = df.iloc[:, 0:5]
        df.columns = ["Time", "Open", "High", "Low", "Close"]
        df.set_index("Time", inplace=True)
        df.index = pd.to_datetime(df.index, unit="ms")
        df = df.astype(float)


        # Indicators
        df[f"K_{self.symbol}"] = ta.momentum.stochrsi_k(df.Close, window=14, smooth1=3, smooth2=3)
        df[f"D_{self.symbol}"] = ta.momentum.stochrsi_d(df.Close, window=14, smooth1=3, smooth2=3)
        df[f"RSI_{self.symbol}"] = ta.momentum.rsi(df.Close, window=14)
        df[f"MACD_{self.symbol}"] = ta.trend.macd_diff(df.Close, window_slow=52, window_fast=24, window_sign=18)
        df.dropna(inplace=True)

        # Long Signal
        df["Long"] = (
            (df[f"K_{self.symbol}"].between(0.2,0.8)) & 
            (df[f"D_{self.symbol}"].between(0.2,0.8)) &
            (df[f"K_{self.symbol}"] > df[f"D_{self.symbol}"]) &
            (df[f"RSI_{self.symbol}"] > 51) &
            (df[f"MACD_{self.symbol}"] > 0)
            )

        # #Sell Signal
        df["Short"] = (
            (df[f"K_{self.symbol}"].between(0.2,0.8)) & 
            (df[f"D_{self.symbol}"].between(0.2,0.8)) &
            (df[f"K_{self.symbol}"] < df[f"D_{self.symbol}"]) &
            (df[f"RSI_{self.symbol}"] < 49) &
            (df[f"MACD_{self.symbol}"] < 0)
            )


        # print(df)

        # Start Passivbot
        if df.Long.values.any():
            print(colored(f"Started Long on {self.symbol}...", "green"))
            startlong = subprocess.Popen([
                "python3",
                "passivbot.py",
                "bybit_01",
                self.symbol,
                config_live_path,
                "-lm",
                "n",
                "-sm",
                "gs",
                "-lw",
                we_long,
                "-sw",
                we_short,
                '-lev',
                leverage
                ],
                stdout=DEVNULL,
                stderr=STDOUT,
                )
            time.sleep(time_wait_ask)
            startlong.kill()

        elif df.Short.values.any():
            print(colored(f"Start Short on {self.symbol}...", "red"))
            startshort = subprocess.Popen([
                "python3",
                "passivbot.py",
                "bybit_01",
                self.symbol,
                config_live_path,
                "-lm",
                "gs",
                "-sm",
                "n",
                "-lw",
                we_long,
                "-sw",
                we_short,
                '-lev',
                leverage
                ],
                stdout=DEVNULL,
                stderr=STDOUT,
                )
            time.sleep(time_wait_ask)
            startshort.kill()

        else:
            print(colored(f"Waiting signal for {self.symbol}...", "yellow"))
            stopbot = subprocess.Popen([
                "python3",
                "passivbot.py",
                "bybit_01",
                self.symbol,
                config_live_path,
                "-lm",
                "gs",
                "-sm",
                "gs",
                "-lw",
                we_long,
                "-sw",
                we_short,
                '-lev',
                leverage
                ],
                stdout=DEVNULL,
                stderr=STDOUT,
                )
            time.sleep(time_wait_ask)
            stopbot.kill()

        return df

    def run_dfall(self):
        while True:
            self.dfall()

def read_config():
    import json

    file_api_key = open("api-key.json")
    api_key_config = json.load(file_api_key)
    file_api_key.close()
    file_config = open("config.json")
    symbols_config = json.load(file_config)
    file_config.close()
    return api_key_config, symbols_config


api_key_config, symbols_config = read_config()
binance_client = Client(
    api_key=api_key_config["binance_api_key"],
    api_secret=api_key_config["binance_api_secret"],
)


def main():
    threads = []
    for symbol in symbols_config["symbols"]:
        bot = Bot_Stoch_RSI_MACD(
            binance_client, symbol["symbol"], symbol["interval"], symbol["limit"]
        )
        symbol_thread = threading.Thread(target=bot.run_dfall, daemon=True)
        symbol_thread.start()
        threads.append(symbol_thread)

    for thread in threads:
        thread.join()

    while True:
        time.sleep(1)


main()
