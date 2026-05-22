import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
import os
import sys
import time
import warnings
from deep_translator import GoogleTranslator

# 忽略警告
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
        name = info.get('shortName', info.get('longName', ticker))
        sector = info.get('sector', 'Unknown')
        pe = f"{info.get('trailingPE', 0):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else "N/A"
        raw_yield = info.get('dividendYield')
        div = f"{raw_yield * 100:.2f}%" if isinstance(raw_yield, (int, float)) else "N/A"
        summary = GoogleTranslator(source='auto', target='zh-TW').translate(info.get('longBusinessSummary', '')[:300]) + "..."
        return summary, pe, div, name, sector
    except: return "暫無簡介", "N/A", "N/A", ticker, "Unknown"

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
            data = yf.download(ticker, period="9mo", progress=False)['Close']
            if data.empty: continue
            plt.figure(figsize=(10, 5)); plt.plot(data.index, data, color=color)
            plt.title(f"{ticker} Trend", fontsize=14); buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close()
            sum, pe, div, name, sec = get_company_details(ticker, data.iloc[-1])
            send_to_discord(ticker, name, sec, data.iloc[-1], pct, buf, sum, pe, div)
            time.sleep(2)
        except: continue

def main():
    # 擴展至 300 檔代表性港股 (此處簡化示意，實際使用時可填入完整代號清單)
    hk_codes = [str(i).zfill(4) for i in range(1, 301)] # 範例：生成 0001 到 0300
    tickers = [f"{code}.HK" for code in hk_codes]
    
    # 分批下載
    all_data = pd.DataFrame()
    for i in range(0, len(tickers), 50):
        batch = tickers[i:i+50]
        batch_data = yf.download(batch, period="10d", progress=False)['Close']
        all_data = pd.concat([all_data, batch_data], axis=1)
        
    if all_data.empty: return
    
    last_two = all_data.dropna(how='all').tail(2)
    if len(last_two) < 2:
        requests.post(WEBHOOK_URL, json={"content": "⚠️ 市場休市，無最新漲跌資料。"})
        return
        
    returns = last_two.pct_change(fill_method=None).iloc[-1].dropna()
    process_and_send_list(returns.nlargest(10), "今日 港股漲幅前十名", '#1f77b4')
    process_and_send_list(returns.nsmallest(10), "今日 港股跌幅最重前十名", 'green')

if __name__ == "__main__":
    main()
