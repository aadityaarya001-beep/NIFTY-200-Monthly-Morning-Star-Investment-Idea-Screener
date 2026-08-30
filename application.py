import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="NIFTY 200 | Monthly Morning Star Screener | Investment Ideas",
    page_icon="📊",
    layout="wide",
)

NIFTY200_CSV_URL = (
    "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
)
HISTORY_YEARS = 4
MAX_WORKERS = 4
RETRY_ROUNDS = 2


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(20,184,166,.12), transparent 25rem),
            radial-gradient(circle at 92% 5%, rgba(59,130,246,.09), transparent 28rem),
            #071018;
        color: #e7eef7;
    }
    .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 2.5rem; }
    #MainMenu, footer { visibility: hidden; }

    .topbar {
        display:flex; justify-content:space-between; align-items:center;
        margin-bottom:1.2rem; color:#8fa4b8; font-size:.78rem;
        letter-spacing:.08em; text-transform:uppercase; font-weight:700;
    }
    .brand-mark { color:#2dd4bf; }
    .live-pill {
        border:1px solid rgba(45,212,191,.28); background:rgba(13,148,136,.10);
        color:#5eead4; padding:.4rem .7rem; border-radius:999px;
    }
    .hero {
        border:1px solid rgba(148,163,184,.16); border-radius:22px;
        padding:2rem 2.1rem; margin-bottom:1.2rem;
        background:linear-gradient(135deg, rgba(15,32,44,.96), rgba(8,20,30,.92));
        box-shadow:0 24px 60px rgba(0,0,0,.28); position:relative; overflow:hidden;
    }
    .hero:after {
        content:''; position:absolute; width:260px; height:260px; right:-80px; top:-120px;
        border-radius:50%; background:rgba(45,212,191,.09); filter:blur(2px);
    }
    .eyebrow { color:#5eead4; font-size:.78rem; letter-spacing:.13em; font-weight:800; text-transform:uppercase; }
    .hero h1 { color:#f8fafc; font-size:2.35rem; line-height:1.12; margin:.65rem 0 .7rem; letter-spacing:-.04em; }
    .hero p { color:#9db0c2; max-width:780px; font-size:1rem; line-height:1.65; margin:0; }
    .hero-tags { display:flex; gap:.55rem; flex-wrap:wrap; margin-top:1.2rem; }
    .hero-tag { border:1px solid rgba(148,163,184,.18); color:#b9c8d6; border-radius:8px; padding:.38rem .62rem; font-size:.75rem; background:rgba(255,255,255,.025); }

    .section-label { color:#8fa4b8; font-size:.73rem; letter-spacing:.12em; text-transform:uppercase; font-weight:800; margin:1.5rem 0 .6rem; }
    .rule-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; margin-bottom:1rem; }
    .rule-card { border:1px solid rgba(148,163,184,.14); background:rgba(13,27,39,.72); border-radius:14px; padding:1rem; min-height:102px; }
    .rule-no { color:#2dd4bf; font-size:.72rem; font-weight:800; letter-spacing:.08em; }
    .rule-title { color:#f0f5fa; font-size:.9rem; font-weight:700; margin:.32rem 0; }
    .rule-text { color:#879daf; font-size:.77rem; line-height:1.45; }

    .metric-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.85rem; margin:1.1rem 0; }
    .metric-card { border:1px solid rgba(148,163,184,.14); border-radius:15px; padding:1.1rem 1.25rem; background:linear-gradient(145deg,rgba(16,34,47,.9),rgba(9,22,32,.9)); }
    .metric-label { color:#8da2b4; text-transform:uppercase; letter-spacing:.09em; font-size:.69rem; font-weight:800; }
    .metric-value { color:#f8fafc; font-size:2rem; font-weight:800; margin-top:.25rem; letter-spacing:-.04em; }
    .metric-note { color:#5eead4; font-size:.72rem; margin-top:.12rem; }

    .notice { border-left:3px solid #2dd4bf; background:rgba(13,148,136,.08); color:#a8bdca; padding:.8rem 1rem; border-radius:0 10px 10px 0; font-size:.82rem; margin:.7rem 0 1rem; }
    .result-head { display:flex; justify-content:space-between; align-items:end; margin:1.5rem 0 .65rem; }
    .result-head h3 { margin:0; color:#f3f7fb; font-size:1.15rem; }
    .result-head span { color:#8298aa; font-size:.75rem; }

    div.stButton > button, div.stDownloadButton > button {
        border-radius:11px; min-height:3rem; font-weight:800; letter-spacing:.01em;
        border:1px solid rgba(45,212,191,.40);
    }
    div.stButton > button[kind="primary"] {
        color:#04201d; background:linear-gradient(90deg,#2dd4bf,#5eead4); border:none;
        box-shadow:0 10px 28px rgba(45,212,191,.16);
    }
    div.stButton > button[kind="primary"]:hover { background:linear-gradient(90deg,#5eead4,#99f6e4); color:#03201d; }
    [data-testid="stDataFrame"] { border:1px solid rgba(148,163,184,.16); border-radius:14px; overflow:hidden; }
    [data-testid="stAlert"] { border-radius:12px; }
    [data-testid="stExpander"] { border:1px solid rgba(148,163,184,.14); border-radius:12px; background:rgba(13,27,39,.6); }
    hr { border-color:rgba(148,163,184,.13) !important; }
    .footer-note { text-align:center; color:#647b8e; font-size:.72rem; margin-top:2rem; }

    @media (max-width: 900px) {
        .rule-grid { grid-template-columns:repeat(2,1fr); }
        .metric-grid { grid-template-columns:1fr; }
        .hero h1 { font-size:1.85rem; }
    }
    @media (max-width: 560px) {
        .rule-grid { grid-template-columns:1fr; }
        .hero { padding:1.4rem; }
        .topbar { align-items:flex-start; gap:.5rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=86_400, show_spinner=False)
def get_nifty200_symbols():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,application/csv,text/plain,*/*",
        "Referer": "https://www.niftyindices.com/",
    }
    response = requests.get(NIFTY200_CSV_URL, headers=headers, timeout=30)
    response.raise_for_status()
    constituents = pd.read_csv(io.StringIO(response.text))

    symbol_col = next(
        (column for column in constituents.columns if column.strip().lower() == "symbol"),
        None,
    )
    if symbol_col is None:
        raise ValueError("The downloaded NIFTY 200 file has no Symbol column.")

    symbols = (
        constituents[symbol_col]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .tolist()
    )
    if not symbols:
        raise ValueError("No NIFTY 200 symbols were found.")
    return symbols


def get_monthly_data(symbol):
    try:
        data = yf.download(
            f"{symbol}.NS",
            period=f"{HISTORY_YEARS}y",
            interval="1mo",
            auto_adjust=False,
            progress=False,
            threads=False,
            timeout=25,
        )
        if data is None or data.empty:
            return None

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        required = ["Open", "High", "Low", "Close"]
        if not all(column in data.columns for column in required):
            return None

        data = data[required].dropna().copy()
        index = pd.to_datetime(data.index)
        try:
            index = index.tz_localize(None)
        except TypeError:
            pass
        data.index = index

        # Yahoo may include the current, still-forming monthly candle.
        current_month_start = pd.Timestamp.today().normalize().replace(day=1)
        return data[data.index < current_month_start]
    except Exception:
        return None


def is_custom_morning_star(candle1, candle2, candle3):
    return (
        float(candle1["Close"]) < float(candle1["Open"])
        and float(candle2["Low"]) < float(candle1["Low"])
        and float(candle2["High"]) < float(candle1["High"])
        and float(candle3["Close"]) > float(candle3["Open"])
        and float(candle3["Close"]) > float(candle1["High"])
    )


def scan_stock(symbol):
    data = get_monthly_data(symbol)
    if data is None or len(data) < 3:
        return None, symbol

    candle1, candle2, candle3 = data.iloc[-3], data.iloc[-2], data.iloc[-1]
    if not is_custom_morning_star(candle1, candle2, candle3):
        return None, None

    result = {
        "Symbol": symbol,
        "Pattern": "Custom Morning Star",
        "Candle 1 Month": data.index[-3].strftime("%Y-%m"),
        "Candle 2 Month": data.index[-2].strftime("%Y-%m"),
        "Candle 3 Month": data.index[-1].strftime("%Y-%m"),
    }
    for number, candle in enumerate((candle1, candle2, candle3), start=1):
        for field in ("Open", "High", "Low", "Close"):
            result[f"Candle {number} {field}"] = round(float(candle[field]), 2)
    return result, None


def run_scan(symbols, progress_bar, status_text):
    matches = []
    failed_symbols = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scan_stock, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                match, failed = future.result()
                if match:
                    matches.append(match)
                if failed:
                    failed_symbols.append(failed)
            except Exception:
                failed_symbols.append(symbol)

            completed += 1
            progress_bar.progress(completed / len(symbols))
            status_text.caption(f"Scanned {completed} of {len(symbols)} stocks")

    # Yahoo Finance can temporarily reject some simultaneous downloads.
    # Retry only those symbols, more slowly and one at a time.
    for retry_round in range(1, RETRY_ROUNDS + 1):
        if not failed_symbols:
            break

        symbols_to_retry = failed_symbols
        failed_symbols = []
        status_text.caption(
            f"Retrying {len(symbols_to_retry)} unavailable stock(s) "
            f"— attempt {retry_round} of {RETRY_ROUNDS}"
        )

        for symbol in symbols_to_retry:
            time.sleep(0.35 * retry_round)
            match, failed = scan_stock(symbol)
            if match:
                matches.append(match)
            if failed:
                failed_symbols.append(failed)

    return matches, failed_symbols


st.markdown(
    """
    <div class="topbar">
      <div><span class="brand-mark">ARYA MARKET LAB</span> &nbsp;/&nbsp; QUANT RESEARCH</div>
      <div class="live-pill">● LIVE MARKET DATA</div>
    </div>
    <section class="hero">
      <div class="eyebrow">NIFTY 200 · MONTHLY EQUITY SCREENER</div>
      <h1>NIFTY 200 <span style="color:#526a7d;font-weight:500">|</span> Monthly Morning Star Screener <span style="color:#526a7d;font-weight:500">|</span> <span style="color:#5eead4">Investment Ideas</span></h1>
      <p>A rule-based research dashboard that scans India’s leading listed companies for a customized bullish Morning Star formation using only fully closed monthly candles.</p>
      <div class="hero-tags">
        <span class="hero-tag">NIFTY 200 UNIVERSE</span>
        <span class="hero-tag">MONTHLY TIMEFRAME</span>
        <span class="hero-tag">CLOSED CANDLES ONLY</span>
        <span class="hero-tag">LATEST MONTH</span>
      </div>
    </section>
    <div class="section-label">Strategy framework</div>
    <div class="rule-grid">
      <div class="rule-card"><div class="rule-no">01 · CANDLE ONE</div><div class="rule-title">Bearish initiation</div><div class="rule-text">Red candle with close below open. Candle size is unrestricted.</div></div>
      <div class="rule-card"><div class="rule-no">02 · CANDLE TWO</div><div class="rule-title">Lower price probe</div><div class="rule-text">Low and high must both form below Candle 1. Colour and size are unrestricted.</div></div>
      <div class="rule-card"><div class="rule-no">03 · CANDLE THREE</div><div class="rule-title">Bullish confirmation</div><div class="rule-text">Green candle with its closing price above Candle 1 high.</div></div>
      <div class="rule-card"><div class="rule-no">04 · VALIDATION</div><div class="rule-title">Latest closed month</div><div class="rule-text">Only patterns completed on the most recent fully closed monthly candle qualify.</div></div>
    </div>
    <div class="notice"><b>Research purpose:</b> Results are potential investment ideas for deeper technical and fundamental analysis—not recommendations to buy or sell.</div>
    """,
    unsafe_allow_html=True,
)

if st.button("RUN LATEST NIFTY 200 SCAN  →", type="primary", use_container_width=True):
    try:
        with st.spinner("Loading the current NIFTY 200 constituent list..."):
            symbols = get_nifty200_symbols()

        progress = st.progress(0.0)
        status = st.empty()
        matches, failed_symbols = run_scan(symbols, progress, status)
        progress.empty()
        status.empty()

        result = pd.DataFrame(matches)
        if not result.empty:
            result = result.sort_values("Symbol").reset_index(drop=True)

        st.markdown(
            f"""
            <div class="section-label">Scan intelligence</div>
            <div class="metric-grid">
              <div class="metric-card"><div class="metric-label">Universe scanned</div><div class="metric-value">{len(symbols)}</div><div class="metric-note">NIFTY 200 constituents</div></div>
              <div class="metric-card"><div class="metric-label">Qualified ideas</div><div class="metric-value">{len(result)}</div><div class="metric-note">Latest monthly pattern</div></div>
              <div class="metric-card"><div class="metric-label">Data integrity</div><div class="metric-value">{len(failed_symbols)}</div><div class="metric-note">Unresolved data errors</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result.empty:
            st.warning("No customized Morning Star pattern was found in the latest closed month.")
        else:
            completion_month = result["Candle 3 Month"].iloc[0]
            st.markdown(
                f"""
                <div class="result-head">
                  <h3>Qualified Investment Ideas</h3>
                  <span>{len(result)} MATCHES · COMPLETED {completion_month}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            summary_columns = [
                "Symbol", "Pattern", "Candle 1 Month", "Candle 2 Month", "Candle 3 Month",
                "Candle 1 Close", "Candle 2 Low", "Candle 3 Close",
            ]
            st.dataframe(
                result[summary_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Symbol": st.column_config.TextColumn("SYMBOL", width="small"),
                    "Pattern": st.column_config.TextColumn("SETUP", width="medium"),
                    "Candle 1 Month": "C1 MONTH",
                    "Candle 2 Month": "C2 MONTH",
                    "Candle 3 Month": "C3 MONTH",
                    "Candle 1 Close": st.column_config.NumberColumn("C1 CLOSE", format="%.2f"),
                    "Candle 2 Low": st.column_config.NumberColumn("C2 LOW", format="%.2f"),
                    "Candle 3 Close": st.column_config.NumberColumn("C3 CLOSE", format="%.2f"),
                },
            )
            with st.expander("View complete three-candle OHLC data"):
                st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button(
                "DOWNLOAD FULL RESULTS · CSV",
                data=result.to_csv(index=False).encode("utf-8"),
                file_name="NIFTY_200_Monthly_Morning_Star_Latest_Month.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if failed_symbols:
            with st.expander(f"⚠️ {len(failed_symbols)} stock(s) with unavailable data"):
                st.write(", ".join(sorted(failed_symbols)))
    except Exception as error:
        st.error(f"The scan could not start: {error}")

st.markdown(
    """
    <div class="footer-note">ARYA MARKET LAB · PYTHON × PANDAS × YAHOO FINANCE × STREAMLIT<br><br>Educational and research use only. Always perform independent analysis before making an investment decision.</div>
    """,
    unsafe_allow_html=True,
)
