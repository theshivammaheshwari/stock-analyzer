import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
import ta

# --------- Scrape Fundamentals from Screener ---------
def screener_fundamentals(stock_code):
    url = f"https://www.screener.in/company/{stock_code}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    fundamentals = {}

    # Top ratios
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

    # Extra factoids (PEG, Altman etc.)
    factoids = soup.find_all("li", class_="flex flex-space-between")
    for f in factoids:
        try:
            key = f.find("span", class_="name").get_text(strip=True)
            val = f.find("span", class_="value").get_text(strip=True)
            fundamentals[key] = val
        except:
            pass

    # Shareholding pattern
    holding_section = soup.find("section", id="shareholding")
    if holding_section:
        rows = holding_section.find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 2:
                fundamentals[cols[0]] = cols[1]

    return fundamentals


# --------- Technical Analysis ---------
def technicals_analysis(ticker_input):
    if not ticker_input.endswith(".NS") and "." not in ticker_input:
        ticker = ticker_input + ".NS"
    else:
        ticker = ticker_input

    stock = yf.Ticker(ticker)
    hist = stock.history(period="6mo", interval="1d")

    if hist.empty:
        return None, None

    # Indicators
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

    # Pivot Points
    P = (latest["High"] + latest["Low"] + latest["Close"]) / 3
    R1 = 2*P - latest["Low"];  S1 = 2*P - latest["High"]
    R2 = P + (latest["High"] - latest["Low"]);  S2 = P - (latest["High"] - latest["Low"])
    R3 = latest["High"] + 2*(P - latest["Low"]); S3 = latest["Low"] - 2*(latest["High"] - P)

    # ---- Voting signals ----
    signals = []
    if latest["EMA10"] > latest["EMA20"]: signals.append("Buy")
    elif latest["EMA10"] < latest["EMA20"]: signals.append("Sell")

    if latest["RSI"] > 60: signals.append("Buy")
    elif latest["RSI"] < 40: signals.append("Sell")

    if latest["MACD"] > latest["MACD_Signal"]: signals.append("Buy")
    elif latest["MACD"] < latest["MACD_Signal"]: signals.append("Sell")

    # Current vs Avg Volume
    if latest["Volume"] > hist["Volume"].rolling(20).mean().iloc[-1]:
        signals.append("Buy")

    # Candle Pattern detection
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
    if final_signal=="Buy":
        stoploss = round(latest["Close"] - 1.5*latest["ATR"], 2)
    elif final_signal=="Sell":
        stoploss = round(latest["Close"] + 1.5*latest["ATR"], 2)

    tech = {
        "Open": round(latest["Open"],2), "High": round(latest["High"],2),
        "Low": round(latest["Low"],2), "Close": round(latest["Close"],2),
        "Volume": int(latest["Volume"]),
        "EMA10": round(latest["EMA10"],2), "EMA20": round(latest["EMA20"],2),
        "RSI": round(latest["RSI"],2), "MACD": round(latest["MACD"],2),
        "MACD_Signal": round(latest["MACD_Signal"],2),
        "ATR": round(latest["ATR"],2),
        "CandlePattern": candle_signal,
        "Signal": final_signal,
        "Strength": strength,
        "Stoploss": stoploss,
        "Pivot": round(P,2), "R1": round(R1,2), "R2": round(R2,2), "R3": round(R3,2),
        "S1": round(S1,2), "S2": round(S2,2), "S3": round(S3,2)
    }
    return tech, hist


# --------- Streamlit UI ---------
st.set_page_config(page_title="Swing Trading + Fundamentals Dashboard", page_icon="📊", layout="wide")
st.title("📊 Swing Trading + Fundamentals Dashboard")

# --- Sidebar Developer Info ---
with st.sidebar:
    st.markdown("### 👨‍💻 Developer Info")
    st.markdown("**Mr. Shivam Maheshwari**")
    st.write("🔗 [LinkedIn](https://www.linkedin.com/in/theshivammaheshwari)")
    st.write("📸 [Instagram](https://www.instagram.com/theshivammaheshwari)")
    st.write("📘 [Facebook](https://www.facebook.com/theshivammaheshwari)")
    st.write("✉️ theshivammaheshwari@gmail.com")
    st.write("📱 +91-9468955596")

# --- Input box ---
user_input = st.text_input("Enter stock symbol", "RELIANCE").upper()

if st.button("Analyze"):
    # -------- Swing Trading Analysis --------
    st.header("📈 Swing Trading Analysis")

    techs, hist = technicals_analysis(user_input)
    if techs:

        # ✅ Key Highlights as row table
        st.subheader("🔎 Key Trade Highlights")
        key_high_data = pd.DataFrame([{
            "Candle Pattern": techs["CandlePattern"],
            "Signal": techs["Signal"],
            "Strength": techs["Strength"],
            "Stoploss": techs["Stoploss"] if techs["Stoploss"] else "NA"
        }])
        st.table(key_high_data)   # Static clean table

        # Detailed Technicals
        st.subheader("📊 Detailed Technicals")
        tech_df = pd.DataFrame([
            ["Open", techs["Open"]],
            ["High", techs["High"]],
            ["Low", techs["Low"]],
            ["Close", techs["Close"]],
            ["Volume", techs["Volume"]],
            ["EMA10", techs["EMA10"]],
            ["EMA20", techs["EMA20"]],
            ["RSI", techs["RSI"]],
            ["MACD", techs["MACD"]],
            ["MACD Signal", techs["MACD_Signal"]],
            ["ATR", techs["ATR"]],
        ], columns=["Metric","Value"])

        st.dataframe(tech_df, use_container_width=True)   # no gradient, clean Volume

        # Pivot Levels
        piv_df = pd.DataFrame({
            "Level":["Pivot","R1","R2","R3","S1","S2","S3"],
            "Value":[techs["Pivot"],techs["R1"],techs["R2"],techs["R3"],
                     techs["S1"],techs["S2"],techs["S3"]]
        })
        st.subheader("Pivot Levels")
        st.dataframe(piv_df.style.background_gradient(cmap="Blues"), use_container_width=True)

        # Chart
        st.subheader("Price Chart (6 months)")
        st.line_chart(hist[["Close","EMA10","EMA20"]])

    else:
        st.error("❌ No technical data found.")

    # -------- Fundamentals --------
    st.header("🏦 Fundamentals")
    funds = screener_fundamentals(user_input)
    if funds:
        df_fund = pd.DataFrame(list(funds.items()), columns=["Metric","Value"])
        st.dataframe(df_fund.style.background_gradient(cmap="Oranges"), use_container_width=True)
    else:
        st.warning("No fundamentals found.")