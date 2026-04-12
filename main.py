import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# ==========================================
# 1. 獲取美股 GOLF (Acushnet) 存貨周轉天數 (DIO)
# ==========================================
def get_golf_dio():
    try:
        print("🔍 正在獲取 GOLF 財報數據...")
        golf = yf.Ticker("GOLF")
        bs = golf.quarterly_balance_sheet
        inc = golf.quarterly_income_stmt
        
        latest_inventory = bs.loc['Inventory'].iloc[0]
        latest_cogs = inc.loc['Cost Of Revenue'].iloc[0]
        
        # DIO 計算公式：(存貨 / 營業成本) * 90天
        dio = (latest_inventory / latest_cogs) * 90
        print(f"✅ 取得 GOLF 最新 DIO: {round(dio, 1)} 天")
        return round(dio, 1)
    except Exception as e:
        print(f"❌ 獲取 GOLF 財報失敗: {e}")
        return None

# ==========================================
# 2. 解析財政部高爾夫微觀出口數據 (HS 95063900006)
# ==========================================
def get_golf_export_yoy():
    # ⚠️ 實務提醒：由於財政部「綜合查詢」的網址帶有會過期的 Session
    # 若掛在雲端排程，建議您每月初手動下載此 CSV 後，推送到同一個 GitHub 資料夾覆蓋舊檔。
    file_path = '綜合查詢_20260412214015.csv'
    
    try:
        print("🔍 正在解析海關微觀數據...")
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # 篩選美國終端市場
        df_us = df[df['國家'] == '美國'].copy()
        
        # 清除 "(初步值)" 等干擾字眼
        df_us['純日期'] = df_us['日期'].str.replace(r'\(.*?\)', '', regex=True).str.strip()
        
        # 將民國年月轉為 Pandas Datetime，以利對齊去年同月
        def to_datetime(roc_date):
            parts = roc_date.replace('年', '-').replace('月', '').split('-')
            if len(parts) == 2:
                return pd.Timestamp(year=int(parts[0]) + 1911, month=int(parts[1]), day=1)
            return None
            
        df_us['Date'] = df_us['純日期'].apply(to_datetime)
        df_us = df_us.sort_values('Date', ascending=False).reset_index(drop=True)
        
        latest = df_us.iloc[0]
        # 精準尋找正好前一年的那個月份
        last_year_df = df_us[df_us['Date'] == (latest['Date'] - pd.DateOffset(years=1))]
        
        if last_year_df.empty:
            print("❌ 找不到去年同月的基期資料。")
            return None, None
            
        last_year = last_year_df.iloc[0]
        
        latest_val = float(latest['美元(千元)'])
        last_year_val = float(last_year['美元(千元)'])
        
        yoy = ((latest_val - last_year_val) / last_year_val) * 100
        latest_month_str = latest['純日期']
        
        print(f"✅ 成功計算 {latest_month_str} YoY: {round(yoy, 2)}%")
        return round(yoy, 2), latest_month_str
        
    except Exception as e:
        print(f"❌ 解析海關資料發生錯誤: {e}")
        return None, None

# ==========================================
# 3. 法人策略分析矩陣
# ==========================================
def analyze_strategy(dio, yoy):
    status = "未知狀態"
    action = "持續觀察"
    
    if yoy > 0 and dio < 100:
        status = "🟢 【情境 A：黃金爆發期】"
        action = "終端需求強勁，拉貨為真。建議佈局台灣代工廠 (復盛、明安)。"
    elif yoy > 0 and dio >= 110:
        status = "🔴 【情境 B：塞貨陷阱期】"
        action = "代工廠出貨大增，但品牌端庫存堆積嚴重。警惕未來砍單風險！"
    elif yoy < 0 and dio >= 110:
        status = "⚫ 【情境 C：庫存去化期】"
        action = "產業寒冬，品牌廠消化庫存中。避開高爾夫代工族群。"
    elif yoy < 0 and dio < 100:
        status = "🟡 【情境 D：復甦前夕期】"
        action = "品牌廠庫存見底，隨時準備重啟拉貨。準備迎接補庫存週期。"
        
    return status, action

# ==========================================
# 4. 觸發 Discord 警報
# ==========================================
def send_discord_alert(dio, yoy, month_str, status, action):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ 未設定 DISCORD_WEBHOOK_URL，僅於終端機輸出。")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    content = f"""
**📊 【法人級：台美股高爾夫產業量化監控】**
> **執行日期：** {today_str}

**1. 終端庫存指標 (美股 GOLF)**
* 最新存貨周轉天數 (DIO)：**{dio} 天** (健康水位: 90-110天)

**2. 供應鏈出貨指標 (HS 950639 高爾夫設備)**
* 最新數據月份：**{month_str}**
* 台灣出口美國 YoY：**{yoy}%**

**3. 量化策略判定**
* **當前狀態：** {status}
* **執行建議：** {action}

*以上內容由自動化程式生成，僅供研究參考，不構成投資建議。*
"""
    try:
        response = requests.post(webhook_url, json={"content": content})
        if response.status_code == 204:
            print("✅ Discord 警報發送成功！")
        else:
            print(f"❌ Discord 發送失敗，錯誤碼: {response.status_code}")
    except Exception as e:
        print(f"❌ Discord 連線發生錯誤: {e}")

# ==========================================
# 主程式執行
# ==========================================
if __name__ == "__main__":
    print("啟動台美股連動分析引擎...")
    dio_val = get_golf_dio()
    yoy_val, data_month = get_golf_export_yoy()
    
    if dio_val is not None and yoy_val is not None:
        status, action = analyze_strategy(dio_val, yoy_val)
        send_discord_alert(dio_val, yoy_val, data_month, status, action)
    else:
        print("⚠️ 數據獲取不完整，取消發送警報。")
