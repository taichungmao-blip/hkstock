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
