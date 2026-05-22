import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import requests
import io
import os
import sys
import time
from deep_translator import GoogleTranslator

# ================= 設定區 =================
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Yahoo Finance 產業版塊中英對照表
SECTOR_MAP = {
    'Technology': '科技',
    'Financial Services': '金融服務',
    'Consumer Defensive': '必需消費',
    'Consumer Cyclical': '非必需消費',
    'Healthcare': '醫療保健',
    'Industrials': '工業',
    'Basic Materials': '原物料',
    'Energy': '能源',
    'Utilities': '公用事業',
    'Real Estate': '房地產',
    'Communication Services': '通訊服務'
}

if not WEBHOOK_URL:
    print("錯誤：找不到 DISCORD_WEBHOOK_URL 環境變數！")
    sys.exit(1)
# ==========================================

def get_company_details(ticker, close_price):
    """獲取簡介、精準股息率、公司名稱與產業別"""
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        company_name = info.get('shortName', info.get('longName', ticker))
        sector_en = info.get('sector', 'Unknown')
        
        pe_ratio = info.get('trailingPE', info.get('forwardPE', 'N/A'))
        if isinstance(pe_ratio, (int, float)):
            pe_ratio = f"{pe_ratio:.2f}"
            
        trailing_div_rate = info.get('trailingAnnualDividendRate')
        if isinstance(trailing_div_rate, (int, float)) and close_price > 0:
            div_yield = (trailing_div_rate / close_price) * 100
            div_yield_str = f"{div_yield:.2f}%" if div_yield > 0 else "0.00%"
        else:
            raw_yield = info.get('dividendYield')
            if isinstance(raw_yield, (int, float)):
                div_yield_str = f"{raw_yield:.2f}%" if raw_yield > 0.3 else f"{raw_yield * 100:.2f}%"
            else:
                div_yield_str = "N/A"

        summary_en = info.get('longBusinessSummary', '')
        if not summary_en:
            return "暫無簡介", pe_ratio, div_yield_str, company_name, sector_en
        if len(summary_en) > 300:
            summary_en = summary_en[:300]

        translator = GoogleTranslator(source='auto', target='zh-TW')
        summary_zh = translator.translate(summary_en) + "..."
        
        return summary_zh, pe_ratio, div_yield_str, company_name, sector_en
    except Exception as e:
        print(f"資料獲取或翻譯失敗 ({ticker}): {e}")
        return "無法獲取簡介", "N/A", "N/A", ticker, "Unknown"

def send_to_discord(ticker, company_name, sector_en, close_price, pct_change, image_buffer, summary, pe_ratio, div_yield):
    sector_cn = SECTOR_MAP.get(sector_en, sector_en)
    
    trend_emoji = "📈" if pct_change > 0 else "📉"
    trend_text = "漲幅" if pct_change > 0 else "跌幅"
    
    message_content = (
        f"{trend_emoji} **{ticker} - {company_name}**\n"
        f"🏢 版塊: {sector_cn} ({sector_en})\n"
        f"📊 本益比 (P/E): **{pe_ratio}** |  💰 股息率: **{div_yield}**\n"
        f"📝 簡介: {summary}\n"
        f"🔹 收盤價: HK${close_price:.2f}\n" 
        f"{trend_emoji} {trend_text}: **{pct_change * 100:.2f}%**" 
    )
    
    payload = {"content": message_content}
    image_buffer.seek(0)
    files = {"file": (f"{ticker}_1Y.png", image_buffer, "image/png")}
    requests.post(WEBHOOK_URL, data=payload, files=files)

def process_and_send_list(stock_series, title_msg, line_color):
    if stock_series.empty:
        print(f"{title_msg} 無符合資料")
        return
        
    print(f"\n--- {title_msg} ---")
    requests.post(WEBHOOK_URL, json={"content": f"📊 **{title_msg}** 📊"})
    time.sleep(1)
    
    for rank, (ticker, pct) in enumerate(stock_series.items(), start=1):
        try:
            stock_data = yf.download(ticker, period="9mo", progress=False)
            if stock_data.empty: continue
            
            close_price = stock_data['Close'].iloc[-1].item()
            
            summary, pe_ratio, div_yield, company_name, sector_en = get_company_details(ticker, close_price)
            
            plt.figure(figsize=(10, 5))
            plt.plot(stock_data.index, stock_data['Close'], color=line_color, linewidth=1.5)
            plt.title(f"{ticker} {company_name} - 1 Year Trend", fontsize=14)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            
            send_to_discord(ticker, company_name, sector_en, close_price, pct, buf, summary, pe_ratio, div_yield)
            time.sleep(2) 
        except Exception as e:
            print(f"處理 {ticker} 時發生錯誤: {e}")

def main():
    # 涵蓋恆生指數、國企指數、科技指數及大型中型股的約 260 檔名單
    hk_codes = [
        '0001', '0002', '0003', '0004', '0005', '0006', '0008', '0010', '0011', '0012',
        '0014', '0016', '0017', '0019', '0020', '0023', '0027', '0054', '0066', '0069',
        '0083', '0101', '0116', '0119', '0123', '0135', '0144', '0151', '0152', '0168',
        '0173', '0175', '0189', '0200', '0214', '0215', '0241', '0256', '0257', '0267',
        '0268', '0270', '0272', '0285', '0288', '0291', '0303', '0315', '0316', '0322',
        '0338', '0345', '0354', '0358', '0371', '0384', '0386', '0388', '0390', '0392',
        '0410', '0460', '0468', '0512', '0522', '0552', '0570', '0586', '0590', '0598',
        '0604', '0639', '0656', '0658', '0669', '0670', '0683', '0688', '0694', '0696',
        '0699', '0700', '0728', '0732', '0753', '0762', '0763', '0772', '0778', '0813',
        '0817', '0823', '0836', '0839', '0853', '0857', '0868', '0874', '0880', '0883',
        '0902', '0914', '0916', '0934', '0939', '0941', '0956', '0960', '0968', '0981',
        '0992', '0998', '1024', '1038', '1044', '1052', '1060', '1066', '1088', '1093',
        '1099', '1109', '1113', '1119', '1128', '1138', '1157', '1171', '1177', '1179',
        '1193', '1209', '1211', '1258', '1288', '1299', '1308', '1310', '1313', '1316',
        '1336', '1339', '1347', '1359', '1368', '1378', '1398', '1516', '1521', '1528',
        '1530', '1548', '1579', '1585', '1610', '1658', '1772', '1776', '1787', '1789',
        '1801', '1810', '1816', '1833', '1876', '1888', '1898', '1919', '1928', '1929',
        '1951', '1958', '1997', '1999', '2005', '2007', '2013', '2015', '2018', '2020',
        '2158', '2192', '2202', '2238', '2269', '2313', '2314', '2318', '2319', '2328',
        '2331', '2333', '2338', '2359', '2380', '2382', '2388', '2600', '2602', '2618',
        '2628', '2688', '2727', '2866', '2883', '2888', '2899', '3308', '3311', '3319',
        '3320', '3323', '3328', '3333', '3339', '3606', '3618', '3690', '3692', '3800',
        '3808', '3868', '3888', '3898', '3908', '3968', '3988', '3990', '6030', '6049',
        '6060', '6066', '6088', '6098', '6110', '6160', '6185', '6618', '6690', '6808',
        '6823', '6837', '6862', '6865', '6881', '6969', '6993', '9618', '9626', '9633',
        '9698', '9866', '9868', '9888', '9898', '9922', '9961', '9987', '9988', '9992',
        '9999'
    ]
    tickers = [f"{code}.HK" for code in hk_codes]
    
    print(f"共載入 {len(tickers)} 檔港股代表性權值股，正在下載股價資料...")
    data = yf.download(tickers, period="5d", progress=False)['Close']
    
    if data.empty:
        print("錯誤：無法下載資料")
        return

    returns = data.pct_change().iloc[-1].dropna()
    
    gainers = returns[returns > 0]
    losers = returns[returns < 0]
    
    top_10_gainers = gainers.nlargest(10)
    top_10_losers = losers.nsmallest(10)
    
    process_and_send_list(top_10_gainers, "今日 港股 (Top 260) 漲幅前十名個股報告", '#1f77b4')
    process_and_send_list(top_10_losers, "今日 港股 (Top 260) 跌幅最重個股報告", 'green')

if __name__ == "__main__":
    main()
