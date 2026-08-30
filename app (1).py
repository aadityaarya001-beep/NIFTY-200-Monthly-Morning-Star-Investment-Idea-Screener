import io
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="NIFTY 200 Monthly Morning Star Screener",
    page_icon="📊",
    layout="wide",
)

NIFTY200_CSV_URL = (
    "https://www.niftyindices.com/IndexConstituent/ind_nifty200list.csv"
)
HISTORY_YEARS = 4
MAX_WORKERS = 8


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

    return matches, failed_symbols


st.title("📊 NIFTY 200 Monthly Morning Star Screener")
st.caption("Customized bullish Morning Star pattern • Latest closed month only")

with st.expander("🔎 Customized screening conditions", expanded=True):
    st.markdown(
        """
        - **Universe:** NIFTY 200 stocks
        - **Timeframe:** Monthly; only closed candles are used
        - **Candle 1:** Red candle — close below open
        - **Candle 2:** Low below Candle 1 low and high below Candle 1 high
        - **Candle 2:** Colour, size and closing position can be anything
        - **Candle 3:** Green candle — close above open
        - **Confirmation:** Candle 3 close above Candle 1 high
        - **Result window:** Pattern must finish in the latest closed month
        """
    )

st.info(
    "The screener shortlists potential investment ideas for further analysis. "
    "It does not provide investment recommendations."
)

if st.button("🚀 Run latest NIFTY 200 scan", type="primary", use_container_width=True):
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

        col1, col2, col3 = st.columns(3)
        col1.metric("Stocks scanned", len(symbols))
        col2.metric("Potential ideas", len(result))
        col3.metric("Data errors", len(failed_symbols))

        if result.empty:
            st.warning("No customized Morning Star pattern was found in the latest closed month.")
        else:
            st.success(f"Found {len(result)} potential investment idea(s).")
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download results as CSV",
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

st.divider()
st.caption(
    "⚠️ Educational and research use only. Always perform independent analysis "
    "before making an investment decision."
)
