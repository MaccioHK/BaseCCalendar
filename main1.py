import pandas as pd
from datetime import datetime, timedelta, time
import pytz
import os
from skyfield import api

# --- 初始化天文引擎 ---
ts = api.load.timescale()
eph = api.load('de421.bsp')
sun, earth = eph['sun'], eph['earth']

# --- 常數與對照表 ---
STARS = {1: "一白", 2: "二黑", 3: "三碧", 4: "四綠", 5: "五黃", 6: "六白", 7: "七赤", 8: "八白", 9: "九紫"}
STAR_WUXING = {"一白": "水", "二黑": "土", "三碧": "木", "四綠": "木", "五黃": "土", "六白": "金", "七赤": "金", "八白": "土", "九紫": "火"}
GAN = list("甲乙丙丁戊己庚辛壬癸")
ZHI = list("子丑寅卯辰巳午未申酉戌亥")
GAN_PROPS = {"甲": "陽木", "乙": "陰木", "丙": "陽火", "丁": "陰火", "戊": "陽土", "己": "陰土", "庚": "陽金", "辛": "陰金", "壬": "陽水", "癸": "陰水"}
ZHI_PROPS = {"子": "陽水", "丑": "陰土", "寅": "陽木", "卯": "陰木", "辰": "陽土", "巳": "陰火", "午": "陽火", "未": "陰土", "申": "陽金", "酉": "陰金", "戌": "陽土", "亥": "陰水"}
SOLAR_TERMS = ["春分", "清明", "穀雨", "立夏", "小滿", "芒種", "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒", "立春", "雨水", "驚蟄"]

def get_solar_lon(dt_utc):
    t = ts.from_datetime(dt_utc)
    astrometric = earth.at(t).observe(sun)
    _, lon, _ = astrometric.ecliptic_latlon()
    return lon.degrees

def get_gz_prop(gz_str):
    if not gz_str or len(gz_str) < 2: return ""
    return f"{GAN_PROPS.get(gz_str[0], '')}{ZHI_PROPS.get(gz_str[1], '')}"

# --- 改進：時柱計算 (考慮早晚子時) ---
def get_hour_gz_detailed(day_gan, hour_name, is_late_rat=False, next_day_gan=None):
    # 五鼠遁開頭
    offset = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
    
    # 晚子時使用「隔日」的日干來遁干
    target_gan = next_day_gan if is_late_rat else day_gan
    start_gan_idx = offset.get(target_gan, 0)
    
    # 找到時支的索引
    zhi_idx = ZHI.index(hour_name[0]) if "子" not in hour_name else 0
    h_gan = GAN[(start_gan_idx + zhi_idx) % 10]
    return h_gan + ZHI[zhi_idx]

# --- 時星計算 ---
def get_hour_star(is_yang, day_zhi, hour_idx):
    # 子午卯酉日: 陽遁147, 陰遁963 (子時起點)
    if is_yang:
        start_val = 1 if day_zhi in "子午卯酉" else (7 if day_zhi in "寅申巳亥" else 4)
        val = (start_val + hour_idx - 1) % 9 + 1
    else:
        start_val = 9 if day_zhi in "子午卯酉" else (3 if day_zhi in "寅申巳亥" else 6)
        val = (start_val - hour_idx - 1) % 9 + 1
    return STARS[val]

def get_day_basic_data(dt_date):
    # 這裡計算當天的基本年、月、日柱與順逆
    # 為簡化邏輯，假設中午 12:00 為基準點
    utc_noon = pytz.utc.localize(datetime.combine(dt_date, time(12, 0)))
    lon = get_solar_lon(utc_noon)
    term_idx = int(lon // 15)
    is_yang = not (90 <= lon < 270)
    
    # 年、月柱 (立春換年)
    logic_y = dt_date.year
    if lon < 315 and dt_date.month <= 3: logic_y -= 1
    y_gz = GAN[(logic_y - 4) % 10] + ZHI[(logic_y - 4) % 12]
    
    shifted_lon = (lon - 315) % 360
    zhi_yue = int(shifted_lon // 30) + 1
    m_gz = GAN[(logic_y % 5 * 2 + zhi_yue + 1) % 10] + ZHI[(zhi_yue + 1) % 12]
    
    # 日柱
    ref_day = datetime(2025, 12, 21).date() # 基準日
    d_diff = (dt_date - ref_day).days
    day_gz = GAN[d_diff % 10] + ZHI[d_diff % 12]
    
    # 飛星
    y_s_val = (3 - (logic_y - 2024)) % 9
    y_s = STARS[y_s_val if y_s_val > 0 else y_s_val + 9]
    base = 8 if ZHI[(logic_y - 4) % 12] in "子午卯酉" else (2 if ZHI[(logic_y - 4) % 12] in "寅申巳亥" else 5)
    m_s_val = (base - (zhi_yue - 1)) % 9
    m_s = STARS[m_s_val if m_s_val > 0 else m_s_val + 9]
    d_s_val = (1 + d_diff) % 9 if is_yang else (9 - d_diff) % 9
    d_s = STARS[d_s_val if d_s_val > 0 else d_s_val + 9]

    return {"y_gz":y_gz, "m_gz":m_gz, "d_gz":day_gz, "y_s":y_s, "m_s":m_s, "d_s":d_s, "is_yang":is_yang, "term_idx":term_idx, "day_gan":day_gz[0]}

def run_pro_calendar(start_str, days):
    start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
    rows = []
    
    for i in range(days):
        curr_date = start_d + timedelta(days=i)
        next_date = curr_date + timedelta(days=1)
        
        d = get_day_basic_data(curr_date)
        d_next = get_day_basic_data(next_date)
        
        # 節氣顯示
        prev_d_data = get_day_basic_data(curr_date - timedelta(days=1))
        display_term = SOLAR_TERMS[d["term_idx"]] if d["term_idx"] != prev_d_data["term_idx"] else ""

        # 定義 13 個時段
        time_slots = [
            (0, "早子時", "00:00-01:00", False),
            (1, "丑時", "01:00-03:00", False),
            (2, "寅時", "03:00-05:00", False),
            (3, "卯時", "05:00-07:00", False),
            (4, "辰時", "07:00-09:00", False),
            (5, "巳時", "09:00-11:00", False),
            (6, "午時", "11:00-13:00", False),
            (7, "未時", "13:00-15:00", False),
            (8, "申時", "15:00-17:00", False),
            (9, "酉時", "17:00-19:00", False),
            (10, "戌時", "19:00-21:00", False),
            (11, "亥時", "21:00-23:00", False),
            (0, "晚子時", "23:00-24:00", True) # 晚子時 flag 為 True
        ]

        for idx, name, period, is_late in time_slots:
            # 計算時柱：晚子時需要用到明天的日干
            h_gz = get_hour_gz_detailed(d["day_gan"], name, is_late, d_next["day_gan"])
            h_s = get_hour_star(d["is_yang"], d["d_gz"][1], idx)
            
            rows.append({
                "日期": curr_date,
                "時段名稱": name,
                "具體時間": period,
                "節氣": display_term if name == "早子時" else "",
                "年柱": d["y_gz"], "年屬性": get_gz_prop(d["y_gz"]),
                "月柱": d["m_gz"], "月屬性": get_gz_prop(d["m_gz"]),
                "日柱": d["d_gz"], "日屬性": get_gz_prop(d["d_gz"]),
                "時柱": h_gz, "時屬性": get_gz_prop(h_gz),
                "年星": d["y_s"], "年星五行": STAR_WUXING[d["y_s"]],
                "月星": d["m_s"], "月星五行": STAR_WUXING[d["m_s"]],
                "日星": d["d_s"], "日星五行": STAR_WUXING[d["d_s"]],
                "時星": h_s, "時星五行": STAR_WUXING[h_s]
            })
            
    return pd.DataFrame(rows)

# --- 執行 ---
if __name__ == "__main__":
    df = run_pro_calendar("1978-01-01", 365) # 測試 5 天，每天 13 行
    
    # 匯出
    df.to_csv("calendar_early_late_rat.csv", index=False, encoding='utf_8_sig')
    df.to_excel("calendar_early_late_rat.xlsx", index=False, engine='openpyxl')
    
    print("✅ 已修正早子時、晚子時邏輯並匯出檔案。")
    print(df.head(13).to_string()) # 預覽第一天的完整 13 個時段