import pandas as pd
from datetime import datetime, timedelta, time
import pytz
import os
from skyfield import api

# --- 初始化天文引擎 ---
ts = api.load.timescale()
eph = api.load('de421.bsp')
sun, earth = eph['sun'], eph['earth']

# --- 常數與對照表定義 ---
STARS = {1: "一白", 2: "二黑", 3: "三碧", 4: "四綠", 5: "五黃", 6: "六白", 7: "七赤", 8: "八白", 9: "九紫"}

# 1. 九星五行對照
STAR_WUXING = {
    "一白": "水", "二黑": "土", "三碧": "木", "四綠": "木", 
    "五黃": "土", "六白": "金", "七赤": "金", "八白": "土", "九紫": "火"
}

GAN = list("甲乙丙丁戊己庚辛壬癸")
ZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 2. 干支五行陰陽對照
GAN_PROPS = {
    "甲": "陽木", "乙": "陰木", "丙": "陽火", "丁": "陰火", "戊": "陽土",
    "己": "陰土", "庚": "陽金", "辛": "陰金", "壬": "陽水", "癸": "陰水"
}
ZHI_PROPS = {
    "子": "陽水", "丑": "陰土", "寅": "陽木", "卯": "陰木", "辰": "陽土", "巳": "陰火",
    "午": "陽火", "未": "陰土", "申": "陽金", "酉": "陰金", "戌": "陽土", "亥": "陰水"
}

# 3. 24 節氣名稱
SOLAR_TERMS = [
    "春分", "清明", "穀雨", "立夏", "小滿", "芒種",
    "夏至", "小暑", "大暑", "立秋", "處暑", "白露",
    "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
    "冬至", "小寒", "大寒", "立春", "雨水", "驚蟄"
]

def get_solar_lon(dt_utc):
    t = ts.from_datetime(dt_utc)
    astrometric = earth.at(t).observe(sun)
    _, lon, _ = astrometric.ecliptic_latlon()
    return lon.degrees

def get_day_star(dt_utc, lon):
    """計算日飛星"""
    ref_date = datetime(2025, 12, 21, tzinfo=pytz.utc)
    diff = (dt_utc.date() - ref_date.date()).days
    is_yang = not (90 <= lon < 270)
    val = (1 + diff) % 9 if is_yang else (9 - diff) % 9
    return STARS[val if val > 0 else val + 9]

def get_gz_prop(gz_str):
    """獲取干支的五行陰陽描述"""
    if len(gz_str) != 2: return ""
    return f"{GAN_PROPS.get(gz_str[0], '')}{ZHI_PROPS.get(gz_str[1], '')}"

def get_ts_data(dt_date, tz_str):
    tz = pytz.timezone(tz_str)
    # 取當地中午 12:00 作為觀測點
    local_dt = tz.localize(datetime.combine(dt_date, time(12, 0)))
    utc_dt = local_dt.astimezone(pytz.utc)

    lon = get_solar_lon(utc_dt)
    term_idx = int(lon // 15) # 節氣索引

    # 1. 支月與術數年 (立春315為界)
    shifted_lon = (lon - 315) % 360
    zhi_yue = int(shifted_lon // 30) + 1

    logic_y = dt_date.year
    if lon < 315 and dt_date.month <= 3:
        logic_y -= 1

    # 2. 年月日干支
    y_idx = (logic_y - 4) % 12
    year_gz = GAN[(logic_y - 4) % 10] + ZHI[y_idx]
    m_gan_idx = (logic_y % 5 * 2 + zhi_yue + 1) % 10
    month_gz = GAN[m_gan_idx] + ZHI[(zhi_yue + 1) % 12]
    ref_day = datetime(2025, 12, 21).date()
    d_diff = (dt_date - ref_day).days
    day_gz = GAN[d_diff % 10] + ZHI[d_diff % 12]

    # 3. 九星
    year_star_val = (3 - (logic_y - 2024)) % 9
    y_star = STARS[year_star_val if year_star_val > 0 else year_star_val + 9]
    base = 8 if ZHI[y_idx] in "子午卯酉" else (2 if ZHI[y_idx] in "寅申巳亥" else 5)
    m_star_val = (base - (zhi_yue - 1)) % 9
    m_star = STARS[m_star_val if m_star_val > 0 else m_star_val + 9]
    d_star = get_day_star(utc_dt, lon)

    return {
        "term_idx": term_idx,
        "year_gz": year_gz, "month_gz": month_gz, "day_gz": day_gz,
        "year_star": y_star, "month_star": m_star, "day_star": d_star
    }

def run_comparison(start_str, days, input_tz):
    start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
    rows = []
    
    for i in range(days):
        curr = start_d + timedelta(days=i)
        d = get_ts_data(curr, input_tz)
        
        # 節氣顯示邏輯：比對前一天，若索引改變則顯示節氣名稱
        prev_d = get_ts_data(curr - timedelta(days=1), input_tz)
        display_term = SOLAR_TERMS[d["term_idx"]] if d["term_idx"] != prev_d["term_idx"] else ""

        rows.append({
            "日期": curr,
            "節氣": display_term,
            "年柱": d["year_gz"], "年屬性": get_gz_prop(d["year_gz"]),
            "月柱": d["month_gz"], "月屬性": get_gz_prop(d["month_gz"]),
            "日柱": d["day_gz"], "日屬性": get_gz_prop(d["day_gz"]),
            "年星": d["year_star"], "年星五行": STAR_WUXING[d["year_star"]],
            "月星": d["month_star"], "月星五行": STAR_WUXING[d["month_star"]],
            "日星": d["day_star"], "日星五行": STAR_WUXING[d["day_star"]]
        })
    return pd.DataFrame(rows)

# --- 執行與匯出 ---
if __name__ == "__main__":
    # 設定參數
    START_DATE = "2025-01-01"
    DAYS_COUNT = 600
    TZ = "Asia/Hong_Kong"

    df = run_comparison(START_DATE, DAYS_COUNT, TZ)

    # 1. 匯出 CSV (utf_8_sig 確保 Excel 中文不亂碼)
    csv_file = "calendar_output.csv"
    df.to_csv(csv_file, index=False, encoding='utf_8_sig')
    
    # 2. 匯出 Excel
    excel_file = "calendar_output.xlsx"
    df.to_excel(excel_file, index=False, engine='openpyxl')

    print(f"--- 數據計算完成 ---")
    print(f"1. CSV 已儲存至: {os.path.abspath(csv_file)}")
    print(f"2. Excel 已儲存至: {os.path.abspath(excel_file)}")
    print("-" * 30)
    print(df.head(10).to_string())