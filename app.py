# app.py
import streamlit as st
import yfinance as yf
import ta
import pandas as pd

st.set_page_config(page_title="Stock Analysis Tool", page_icon="📊", layout="wide")

st.title("📊 Stock Analysis Tool (Swing / Positional)")

# ------ User Input ------
ticker_input = st.text_input("Enter Stock Symbol (e.g. RELIANCE, TCS, INFY)", "RELIANCE")

# Automatically append .NS for Indian stocks (if not already provided)
if ticker_input and not ticker_input.endswith(".NS") and "." not in ticker_input:
    ticker = ticker_input.upper() + ".NS"
else:
    ticker = ticker_input.upper()

st.write(f"Selected Ticker: **{ticker}**")

# ------ Fetch Data ------
if st.button("Analyze"):
    with st.spinner("Fetching data..."):
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo", interval="1d")

        if hist.empty:
            st.error("⚠️ No data found. Check ticker symbol.")
        else:
            # ----- Indicators -----
            hist["EMA10"] = hist["Close"].ewm(span=10).mean()
            hist["EMA20"] = hist["Close"].ewm(span=20).mean()
            hist["RSI"]   = ta.momentum.RSIIndicator(hist["Close"], window=14).rsi()
            
            macd = ta.trend.MACD(hist["Close"])
            hist["MACD"]        = macd.macd()
            hist["MACD_Signal"] = macd.macd_signal()
            
            atr = ta.volatility.AverageTrueRange(hist["High"], hist["Low"], hist["Close"], window=14)
            hist["ATR"] = atr.average_true_range()
            
            hist["Vol_Avg20"] = hist["Volume"].rolling(20).mean()

            latest = hist.iloc[-1]
            prev   = hist.iloc[-2]

            # ---- Pivot Points ----
            P = (latest["High"] + latest["Low"] + latest["Close"]) / 3
            R1 = 2*P - latest["Low"];  S1 = 2*P - latest["High"]
            R2 = P + (latest["High"] - latest["Low"]);  S2 = P - (latest["High"] - latest["Low"])
            R3 = latest["High"] + 2*(P - latest["Low"]); S3 = latest["Low"] - 2*(latest["High"] - P)

            # ---- Voting ----
            signals = []
            if latest["EMA10"] > latest["EMA20"]: signals.append("Buy")
            elif latest["EMA10"] < latest["EMA20"]: signals.append("Sell")

            if latest["RSI"] > 60: signals.append("Buy")
            elif latest["RSI"] < 40: signals.append("Sell")

            if latest["MACD"] > latest["MACD_Signal"]: signals.append("Buy")
            elif latest["MACD"] < latest["MACD_Signal"]: signals.append("Sell")

            if latest["Volume"] > latest["Vol_Avg20"]: signals.append("Buy")

            # Candle Pattern
            candle_signal = "None"
            if (latest["Close"] > latest["Open"] and prev["Close"] < prev["Open"] 
                and latest["Close"] > prev["Open"] and latest["Open"] < prev["Close"]):
                candle_signal = "Bullish Engulfing"; signals.append("Buy")
            elif (latest["Close"] < latest["Open"] and prev["Close"] > prev["Open"] 
                and latest["Close"] < prev["Open"] and latest["Open"] > prev["Close"]):
                candle_signal = "Bearish Engulfing"; signals.append("Sell")

            buy_votes  = signals.count("Buy")
            sell_votes = signals.count("Sell")
            total_votes = buy_votes + sell_votes

            if buy_votes > sell_votes: final_signal = "Buy"
            elif sell_votes > buy_votes: final_signal = "Sell"
            else: final_signal = "Hold"

            if final_signal == "Buy":
                strength = f"Strong Buy ({buy_votes}/{total_votes})" if total_votes and buy_votes>=0.75*total_votes else f"Weak Buy ({buy_votes}/{total_votes})"
            elif final_signal == "Sell":
                strength = f"Strong Sell ({sell_votes}/{total_votes})" if total_votes and sell_votes>=0.75*total_votes else f"Weak Sell ({sell_votes}/{total_votes})"
            else:
                strength = "Neutral"

            stoploss = None
            if final_signal=="Buy":
                stoploss = round(latest["Close"] - 1.5*latest["ATR"], 2)
            elif final_signal=="Sell":
                stoploss = round(latest["Close"] + 1.5*latest["ATR"], 2)

            # ---- Show Output ----
            st.subheader("📊 Latest Analysis Summary")
            st.write(f"**Open:** {round(latest['Open'],2)} | **High:** {round(latest['High'],2)} | **Low:** {round(latest['Low'],2)} | **Close:** {round(latest['Close'],2)}")
            st.write(f"**EMA10:** {round(latest['EMA10'],2)} | **EMA20:** {round(latest['EMA20'],2)}")
            st.write(f"**RSI:** {round(latest['RSI'],2)} | **MACD:** {round(latest['MACD'],2)} | **MACD_Signal:** {round(latest['MACD_Signal'],2)}")
            st.write(f"**ATR:** {round(latest['ATR'],2)} | **20d Avg Vol:** {round(latest['Vol_Avg20'],2)}")
            st.write(f"**Candle Pattern:** {candle_signal}")
            st.success(f"**Signal: {final_signal} | Strength: {strength}**")
            if stoploss: st.warning(f"**Suggested Stoploss:** {stoploss}")

            st.subheader("📌 Pivot Levels")
            st.write(f"Pivot: {round(P,2)} | R1: {round(R1,2)} | R2: {round(R2,2)} | R3: {round(R3,2)} | S1: {round(S1,2)} | S2: {round(S2,2)} | S3: {round(S3,2)}")

            # 📈 Chart
            st.subheader("📈 Price Chart (6 months)")
            chart_data = hist[["Close","EMA10","EMA20"]].round(2)
            st.line_chart(chart_data)

            # Raw Data Table (last 10 entries)
            st.subheader("📑 Recent Data")
            st.dataframe(hist.tail(10).round(2))