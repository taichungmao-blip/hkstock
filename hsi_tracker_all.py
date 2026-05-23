import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
import os
import time
import warnings
from deep_translator import GoogleTranslator

# 忽略 pandas 未來版本的警告
warnings.simplefilter(action='ignore', category=FutureWarning)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

SECTOR_MAP = {
    'Technology': '科技', 'Financial Services': '金融服務', 'Consumer Defensive': '必需消費',
    'Consumer Cyclical': '非必需消費', 'Healthcare': '醫療保健', 'Industrials': '工業',
    'Basic Materials': '原物料', 'Energy': '能源', 'Utilities': '公用事業',
    'Real Estate': '房地產', 'Communication Services': '通訊服務'
}

def get_company_details(ticker, close_price):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        company_name = info.get('shortName', info.get('longName', ticker))
        sector = info.get('sector', 'Unknown')
        pe = f"{info.get('trailingPE', 0):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else "N/A"
        raw_yield = info.get('dividendYield')
        div = f"{raw_yield * 100:.2f}%" if isinstance(raw_yield, (int, float)) else "N/A"
        summary_en = info.get('longBusinessSummary', '')[:300]
        summary_zh = GoogleTranslator(source='auto', target='zh-TW').translate(summary_en) + "..."
        return summary_zh, pe, div, company_name, sector
    except:
        return "暫無簡介", "N/A", "N/A", ticker, "Unknown"

def send_to_discord(ticker, name, sector, price, pct, img, summary, pe, div):
    emoji, trend = ("📈", "漲幅") if pct > 0 else ("📉", "跌幅")
    msg = (f"{emoji} **{ticker} - {name}**\n🏢 版塊: {SECTOR_MAP.get(sector, sector)}\n"
           f"📊 本益比: {pe} | 💰 股息率: {div}\n📝 簡介: {summary}\n"
           f"🔹 收盤價: HK${price:.2f}\n{emoji} {trend}: **{pct * 100:.2f}%**")
    img.seek(0)
    requests.post(WEBHOOK_URL, data={"content": msg}, files={"file": (f"{ticker}.png", img, "image/png")})

def process_and_send_list(series, title, color):
    requests.post(WEBHOOK_URL, json={"content": f"📊 **{title}** 📊"})
    for ticker, pct in series.items():
        try:
            data = yf.download(ticker, period="9mo", progress=False)
            if data.empty: continue
            
            # 單一股票下載時，確保正確抓取收盤價序列
            if isinstance(data.columns, pd.MultiIndex):
                close_series = data['Close'][ticker] if 'Close' in data.columns else data.iloc[:, 0]
            else:
                close_series = data['Close'] if 'Close' in data.columns else data.iloc[:, 0]

            plt.figure(figsize=(10, 5))
            plt.plot(close_series.index, close_series, color=color, linewidth=1.5)
            plt.title(f"{ticker} Trend", fontsize=14)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            
            sum_zh, pe, div, name, sec = get_company_details(ticker, close_series.iloc[-1])
            send_to_discord(ticker, name, sec, close_series.iloc[-1], pct, buf, sum_zh, pe, div)
            time.sleep(2)
        except Exception as e:
            print(f"處理 {ticker} 發生錯誤: {e}")
            continue

def main():
    HK_TICKERS = [
        "0001.HK", "0002.HK", "0003.HK", "0005.HK", "0006.HK", "0008.HK", "0012.HK", "0016.HK", "0017.HK", "0019.HK",
        "0027.HK", "0066.HK", "0069.HK", "0101.HK", "0151.HK", "0175.HK", "0241.HK", "0267.HK", "0288.HK", "0386.HK",
        "0388.HK", "0669.HK", "0688.HK", "0700.HK", "0762.HK", "0823.HK", "0857.HK", "0883.HK", "0939.HK", "0941.HK",
        "0960.HK", "0968.HK", "0981.HK", "0992.HK", "1038.HK", "1044.HK", "1088.HK", "1093.HK", "1113.HK", "1211.HK",
        "1299.HK", "1398.HK", "1810.HK", "1928.HK", "2015.HK", "2269.HK", "2318.HK", "2319.HK", "2331.HK", "2382.HK",
        "2388.HK", "2628.HK", "3690.HK", "3968.HK", "3988.HK", "6098.HK", "6690.HK", "6862.HK", "9618.HK", "9633.HK",
        "9888.HK", "9988.HK", "9999.HK", "0235.HK", "0384.HK", "0493.HK", "0670.HK", "0753.HK", "0772.HK", "0836.HK",
        "0868.HK", "0880.HK", "0902.HK", "0914.HK", "0916.HK", "1066.HK", "1109.HK", "1177.HK", "1209.HK", "1336.HK",
        "1347.HK", "1378.HK", "1548.HK", "1579.HK", "1772.HK", "1801.HK", "1888.HK", "1929.HK", "1958.HK", "1997.HK",
        "2018.HK", "2202.HK", "2313.HK", "2333.HK", "2380.HK", "2618.HK", "2899.HK", "3692.HK", "3808.HK", "6060.HK"
    ]
    
    print(f"正在下載 {len(HK_TICKERS)} 檔港股股價...")
    data = yf.download(HK_TICKERS, period="10d", progress=False)
    
    if data.empty:
        return

    # 確保正確解析 Yahoo Finance 格式
    try:
        close_data = data['Close']
    except KeyError:
        try:
            close_data = data.xs('Close', level=0, axis=1)
        except KeyError:
            close_data = data

    last_two = close_data.dropna(how='all').tail(2)
    if len(last_two) < 2:
        requests.post(WEBHOOK_URL, json={"content": "⚠️ 目前市場休市，無最新漲跌資料可計算。"})
        return
        
    returns = last_two.pct_change(fill_method=None).iloc[-1].dropna()
    
    if returns.empty:
        requests.post(WEBHOOK_URL, json={"content": "⚠️ 無法計算漲跌幅，可能是因為資料缺失。"})
        return
    
    process_and_send_list(returns.nlargest(10), "今日 港股漲幅前十名", '#1f77b4')
    process_and_send_list(returns.nsmallest(10), "今日 港股跌幅最重前十名", 'green')

if __name__ == "__main__":
    main()
