# app.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
import ta

# ------------------
# Function: Fundamentals Scraper
# ------------------
def screener_fundamentals(stock_code):
    url = f"https://www.screener.in/company/{stock_code}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    fundamentals = {}

    ratios_box = soup.find("div", class_="company-ratios")
    if ratios_box:
        rows = ratios_box.find_all("li")
        for row in rows:
            try:
                key = row.find("span", class_="name").get_text(strip=True)
                val = row.find("span", class_="value").get_text(strip=True)
                fundamentals[key] = val
            except:
                pass

    factoids = soup.find_all("li", class_="flex flex-space-between")
    for f in factoids:
        try:
            key = f.find("span", class_="name").get_text(strip=True)
            val = f.find("span", class_="value").get_text(strip=True)
            fundamentals[key] = val
        except:
            pass

    holding_section = soup.find("section", id="shareholding")
    if holding_section:
        rows = holding_section.find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 2:
                fundamentals[cols[0]] = cols[1]

    return fundamentals


# ------------------
# Function: Technicals (yfinance)
# ------------------
def technicals_analysis(ticker_input):
    if not ticker_input.endswith(".NS") and "." not in ticker_input:
        ticker = ticker_input + ".NS"
    else:
        ticker = ticker_input

    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo", interval="1d")

    if hist.empty:
        return None, None

    hist["EMA10"] = hist["Close"].ewm(span=10).mean()
    hist["EMA20"] = hist["Close"].ewm(span=20).mean()
    hist["RSI"]   = ta.momentum.RSIIndicator(hist["Close"], window=14).rsi()

    macd = ta.trend.MACD(hist["Close"])
    hist["MACD"]        = macd.macd()
    hist["MACD_Signal"] = macd.macd_signal()

    atr = ta.volatility.AverageTrueRange(hist["High"], hist["Low"], hist["Close"], window=14)
    hist["ATR"] = atr.average_true_range()

    latest = hist.iloc[-1]
    prev   = hist.iloc[-2]

    # Pivot
    P = (latest["High"] + latest["Low"] + latest["Close"]) / 3
    R1 = 2*P - latest["Low"];  S1 = 2*P - latest["High"]
    R2 = P + (latest["High"] - latest["Low"]);  S2 = P - (latest["High"] - latest["Low"])
    R3 = latest["High"] + 2*(P - latest["Low"]); S3 = latest["Low"] - 2*(latest["High"] - P)

    signals = []
    if latest["EMA10"] > latest["EMA20"]: signals.append("Buy")
    elif latest["EMA10"] < latest["EMA20"]: signals.append("Sell")

    if latest["RSI"] > 60: signals.append("Buy")
    elif latest["RSI"] < 40: signals.append("Sell")

    if latest["MACD"] > latest["MACD_Signal"]: signals.append("Buy")
    elif latest["MACD"] < latest["MACD_Signal"]: signals.append("Sell")

    if latest["Close"] > latest["EMA20"] and latest["Volume"] > hist["Volume"].rolling(20).mean().iloc[-1]:
        signals.append("Buy")

    candle_signal = "None"
    if (latest["Close"] > latest["Open"] and prev["Close"] < prev["Open"]
        and latest["Close"] > prev["Open"] and latest["Open"] < prev["Close"]):
        candle_signal = "Bullish Engulfing"; signals.append("Buy")
    elif (latest["Close"] < latest["Open"] and prev["Close"] > prev["Open"]
        and latest["Close"] < prev["Open"] and latest["Open"] > prev["Close"]):
        candle_signal = "Bearish Engulfing"; signals.append("Sell")

    buy_votes, sell_votes = signals.count("Buy"), signals.count("Sell")
    total = buy_votes + sell_votes

    if buy_votes > sell_votes: final_signal = "Buy"
    elif sell_votes > buy_votes: final_signal = "Sell"
    else: final_signal = "Hold"

    if final_signal == "Buy":
        strength = f"Strong Buy ({buy_votes}/{total})" if total and buy_votes>=0.75*total else f"Weak Buy ({buy_votes}/{total})"
    elif final_signal == "Sell":
        strength = f"Strong Sell ({sell_votes}/{total})" if total and sell_votes>=0.75*total else f"Weak Sell ({sell_votes}/{total})"
    else:
        strength = "Neutral"

    stoploss = None
    if final_signal=="Buy": stoploss = round(latest["Close"] - 1.5*latest["ATR"], 2)
    elif final_signal=="Sell": stoploss = round(latest["Close"] + 1.5*latest["ATR"], 2)

    tech = {
        "Open": round(latest["Open"],2), "High": round(latest["High"],2),
        "Low": round(latest["Low"],2), "Close": round(latest["Close"],2),
        "Volume": int(latest["Volume"]),
        "EMA10": round(latest["EMA10"],2), "EMA20": round(latest["EMA20"],2),
        "RSI": round(latest["RSI"],2), "MACD": round(latest["MACD"],2), "MACD_Signal": round(latest["MACD_Signal"],2),
        "ATR": round(latest["ATR"],2), "CandlePattern": candle_signal,
        "Signal": final_signal, "Strength": strength, "Stoploss": stoploss,
        "Pivot": round(P,2), "R1": round(R1,2), "R2": round(R2,2), "R3": round(R3,2),
        "S1": round(S1,2), "S2": round(S2,2), "S3": round(S3,2)
    }
    return tech, hist


# ------------------
# Streamlit UI
# ------------------
st.set_page_config(page_title="Swing Trading + Fundamentals", page_icon="📊", layout="wide")

st.title("📊 Swing Trading + Fundamentals Dashboard")

col1, col2 = st.columns([2,1])

with col1:
    user_input = st.text_input("Enter stock code (e.g., RELIANCE, TCS, INFY)", "RELIANCE").upper()
with col2:
    st.write(" ")  # spacing
    run = st.button("Run Analysis")

if run:
    # Fundamentals
    st.subheader("Company Fundamentals")
    funds = screener_fundamentals(user_input)
    if funds:
        df_fund = pd.DataFrame(list(funds.items()), columns=["Metric","Value"])
        st.table(df_fund)
    else:
        st.warning("No fundamental data found.")

    # Technicals
    st.subheader("Technical Swing Analysis")
    techs, hist = technicals_analysis(user_input)
    if techs:
        # Show key metrics like cards
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric("Close", techs["Close"])
        mcol2.metric("EMA10", techs["EMA10"])
        mcol3.metric("EMA20", techs["EMA20"])
        mcol4.metric("RSI", techs["RSI"])

        ncol1, ncol2, ncol3 = st.columns(3)
        ncol1.metric("MACD", techs["MACD"])
        ncol2.metric("ATR", techs["ATR"])
        ncol3.metric("Volume", techs["Volume"])

        # Signal
        st.success(f"**Signal:** {techs['Signal']} | **Strength:** {techs['Strength']}")
        st.info(f"Candle Pattern: {techs['CandlePattern']}")
        if techs["Stoploss"]:
            st.warning(f"Suggested Stoploss: {techs['Stoploss']}")

        # Pivot Table
        st.subheader("Pivot Levels")
        piv_df = pd.DataFrame({
            "Level":["Pivot","R1","R2","R3","S1","S2","S3"],
            "Value":[techs["Pivot"],techs["R1"],techs["R2"],techs["R3"],techs["S1"],techs["S2"],techs["S3"]]
        })
        st.table(piv_df)

        # Chart
        st.subheader("Price Chart (6 months)")
        st.line_chart(hist[["Close","EMA10","EMA20"]])
    else:
        st.error("No technical data found.")