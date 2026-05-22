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
    # ... (前面的代號清單保持不變) ...
    tickers = [f"{code}.HK" for code in hk_codes]
    
    print(f"正在下載 {len(tickers)} 檔港股股價...")
    # 改為抓取最近 10 天，確保一定能抓到有效的兩個交易日
    data = yf.download(tickers, period="10d", progress=False)['Close']
    
    if data.empty:
        print("錯誤：無法下載資料")
        return

    # 修正邏輯：抓取最後兩個有效的交易日來計算漲跌幅
    # 這樣即便在週末執行，也能算出最後一個交易日的漲跌
    last_two_days = data.dropna(how='all').tail(2)
    
    if len(last_two_days) < 2:
        print("目前沒有足夠的交易日資料來計算漲跌幅")
        return
        
    returns = last_two_days.pct_change(fill_method=None).iloc[-1].dropna()
    
    if returns.empty:
        print("沒有計算出漲跌幅資料")
        return
    
    # ... (後續的 top_10_gainers 與 process_and_send_list 保持不變) ...

    top_10_gainers = returns.nlargest(10)
    top_10_losers = returns.nsmallest(10)
    
    # 呼叫你原本的 process_and_send_list 函式即可
    process_and_send_list(top_10_gainers, "今日 港股漲幅前十名", '#1f77b4')
    process_and_send_list(top_10_losers, "今日 港股跌幅最重前十名", 'green')

if __name__ == "__main__":
    main()
