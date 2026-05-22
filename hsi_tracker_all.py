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

# 忽略 pandas 未來版本的警告[cite: 1]
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
        sector_en = info.get('sector', 'Unknown')
        pe_ratio = f"{info.get('trailingPE', 0):.2f}" if isinstance(info.get('trailingPE'), (int, float)) else "N/A"
        
        raw_yield = info.get('dividendYield')
        div_yield_str = f"{raw_yield * 100:.2f}%" if isinstance(raw_yield, (int, float)) else "N/A"
        
        summary_en = info.get('longBusinessSummary', '')[:300]
        summary_zh = GoogleTranslator(source='auto', target='zh-TW').translate(summary_en) + "..."
        return summary_zh, pe_ratio, div_yield_str, company_name, sector_en
    except:
        return "暫無簡介", "N/A", "N/A", ticker, "Unknown"

def send_to_discord(ticker, company_name, sector_en, close_price, pct_change, image_buffer, summary, pe_ratio, div_yield):
    trend_emoji, trend_text = ("📈", "漲幅") if pct_change > 0 else ("📉", "跌幅")
    message = (f"{trend_emoji} **{ticker} - {company_name}**\n"
               f"🏢 版塊: {SECTOR_MAP.get(sector_en, sector_en)}\n"
               f"📊 本益比: {pe_ratio} | 💰 股息率: {div_yield}\n"
               f"📝 簡介: {summary}\n"
               f"🔹 收盤價: HK${close_price:.2f}\n"
               f"{trend_emoji} {trend_text}: **{pct_change * 100:.2f}%**")
    
    image_buffer.seek(0)
    requests.post(WEBHOOK_URL, data={"content": message}, files={"file": (f"{ticker}.png", image_buffer, "image/png")})

def process_and_send_list(stock_series, title_msg, line_color):
    requests.post(WEBHOOK_URL, json={"content": f"📊 **{title_msg}** 📊"})
    for ticker, pct in stock_series.items():
        try:
            stock_data = yf.download(ticker, period="9mo", progress=False)['Close']
            if stock_data.empty: continue
            
            plt.figure(figsize=(10, 5))
            plt.plot(stock_data.index, stock_data, color=line_color)
            plt.title(f"{ticker} Trend", fontsize=14)
            buf = io.BytesIO()
            plt.savefig(buf, format='png'); plt.close()
            
            summary, pe, div, name, sector = get_company_details(ticker, stock_data.iloc[-1])
            send_to_discord(ticker, name, sector, stock_data.iloc[-1], pct, buf, summary, pe, div)
            time.sleep(2)
        except: continue

def main():
    hk_codes = ['0001', '0002', '0003', '0005', '0006', '0008', '0010', '0012', '0016', '0017', '0019', '0020', '0023', '0027', '0066', '0069', '0101', '0151', '0175', '0241', '0267', '0288', '0386', '0388', '0700', '0762', '0823', '0857', '0883', '0939', '0941', '0981', '0992', '1038', '1044', '1088', '1093', '1113', '1211', '1299', '1398', '1810', '1928', '2015', '2269', '2318', '2388', '2628', '3690', '3988', '6098', '6690', '9618', '9633', '9888', '9988', '9999']
    tickers = [f"{code}.HK" for code in hk_codes]
    
    data = yf.download(tickers, period="10d", progress=False)['Close']
    if data.empty: return

    # 抓取最後兩個有效交易日計算[cite: 1]
    last_two_days = data.dropna(how='all').tail(2)
    if len(last_two_days) < 2: return
        
    returns = last_two_days.pct_change(fill_method=None).iloc[-1].dropna()
    process_and_send_list(returns.nlargest(10), "今日 港股漲幅前十名", '#1f77b4')
    process_and_send_list(returns.nsmallest(10), "今日 港股跌幅最重前十名", 'green')

if __name__ == "__main__":
    main()
