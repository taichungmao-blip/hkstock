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

# 忽略 pandas 未來版本的警告
warnings.simplefilter(action='ignore', category=FutureWarning)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# (SECTOR_MAP 與 get_company_details 邏輯與之前相同，此處略過以節省篇幅)
# 請保留原版程式碼中的這兩個函式

def main():
    # 簡化後的清單 (建議刪除那些已知會報錯的代號)
    hk_codes = [
        '0001', '0002', '0003', '0005', '0006', '0008', '0010', '0012', '0016', '0017',
        '0019', '0020', '0023', '0027', '0066', '0069', '0101', '0151', '0175', '0241',
        '0267', '0288', '0386', '0388', '0700', '0762', '0823', '0857', '0883', '0939',
        '0941', '0981', '0992', '1038', '1044', '1088', '1093', '1113', '1211', '1299',
        '1398', '1810', '1928', '2015', '2269', '2318', '2388', '2628', '3690', '3988',
        '6098', '6690', '9618', '9633', '9888', '9988', '9999'
    ]
    tickers = [f"{code}.HK" for code in hk_codes]
    
    print(f"正在下載 {len(tickers)} 檔港股股價...")
    
    # 關鍵修改：分批下載並只抓取近 2 天資料以確保穩定
    data = yf.download(tickers, period="2d", progress=False)['Close']
    
    if data.empty:
        print("錯誤：無法下載任何資料")
        return

    # 明確指定 fill_method=None 以解決未來棄用警告
    returns = data.pct_change(fill_method=None).iloc[-1].dropna()
    
    if returns.empty:
        print("沒有計算出漲跌幅資料")
        return

    top_10_gainers = returns.nlargest(10)
    top_10_losers = returns.nsmallest(10)
    
    # 呼叫你原本的 process_and_send_list 函式即可
    process_and_send_list(top_10_gainers, "今日 港股漲幅前十名", '#1f77b4')
    process_and_send_list(top_10_losers, "今日 港股跌幅最重前十名", 'green')

if __name__ == "__main__":
    main()
