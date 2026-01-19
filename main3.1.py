import pandas as pd
from datetime import datetime, timedelta, time
import pytz
from skyfield import api
from lunar_python import Lunar  # 需安裝: pip install lunar_python

# --- 初始化天文引擎 ---
# 請確保目錄下有 'de421.bsp' 文件
ts = api.load.timescale()
try:
    eph = api.load('de421.bsp')
except:
    print("❌ 找不到 de421.bsp 文件，請確保該文件在同一目錄下。")
    exit()
    
sun, earth = eph['sun'], eph['earth']

# --- 1. 基礎字典與對照表 ---
STARS = {1: "一白", 2: "二黑", 3: "三碧", 4: "四綠", 5: "五黃", 6: "六白", 7: "七赤", 8: "八白", 9: "九紫"}
STAR_WUXING = {"一白": "水", "二黑": "土", "三碧": "木", "四綠": "木", "五黃": "土", "六白": "金", "七赤": "金", "八白": "土", "九紫": "火"}

GAN = list("甲乙丙丁戊己庚辛壬癸")
ZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 五行屬性字典
GAN_PROPS = {"甲": "陽木", "乙": "陰木", "丙": "陽火", "丁": "陰火", "戊": "陽土", "己": "陰土", "庚": "陽金", "辛": "陰金", "壬": "陽水", "癸": "陰水"}
ZHI_PROPS = {"子": "陽水", "丑": "陰土", "寅": "陽木", "卯": "陰木", "辰": "陽土", "巳": "陰火", "午": "陽火", "未": "陰土", "申": "陽金", "酉": "陰金", "戌": "陽土", "亥": "陰水"}

SOLAR_TERMS = ["春分", "清明", "穀雨", "立夏", "小滿", "芒種", "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒", "立春", "雨水", "驚蟄"]

# 納音表
NAYIN = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "爐中火", "丁卯": "爐中火", "戊辰": "大林木", "己巳": "大林木",
    "庚午": "路旁土", "辛未": "路旁土", "壬申": "劍鋒金", "癸酉": "劍鋒金", "甲戌": "山頭火", "乙亥": "山頭火",
    "丙子": "澗下水", "丁丑": "澗下水", "戊寅": "城頭土", "己卯": "城頭土", "庚辰": "白蠟金", "辛巳": "白蠟金",
    "壬午": "楊柳木", "癸未": "楊柳木", "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹靂火", "己丑": "霹靂火", "庚寅": "松柏木", "辛卯": "松柏木", "壬辰": "長流水", "癸巳": "長流水",
    "甲午": "砂中金", "乙未": "砂中金", "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金", "甲辰": "覆燈火", "乙巳": "覆燈火",
    "丙午": "天河水", "丁未": "天河水", "戊申": "大驛土", "己酉": "大驛土", "庚戌": "釵釧金", "辛亥": "釵釧金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水", "丙辰": "沙中土", "丁巳": "沙中土",
    "戊午": "天上火", "己未": "天上火", "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
}

# --- 2. 核心計算函數 ---

def get_solar_lon(dt_utc):
    t = ts.from_datetime(dt_utc)
    astrometric = earth.at(t).observe(sun)
    _, lon, _ = astrometric.ecliptic_latlon()
    return lon.degrees

def get_gz_prop(gz_str):
    """獲取干支屬性 (如: 陽木陽水)"""
    if not gz_str or len(gz_str) < 2: return ""
    return f"{GAN_PROPS.get(gz_str[0], '')}{ZHI_PROPS.get(gz_str[1], '')}"

def get_lunar_str(dt_date):
    """(新增) 獲取農曆字串，如 '正月初一'"""
    try:
        # 將 date 轉為 datetime 以避免庫報錯
        dt_val = datetime.combine(dt_date, time(12, 0))
        lunar = Lunar.fromDate(dt_val)
        return f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    except Exception as e:
        return ""

def get_tai_yuan(m_gz):
    """胎元：月干進一，月支配三"""
    if not m_gz: return ""
    g_idx = (GAN.index(m_gz[0]) + 1) % 10
    z_idx = (ZHI.index(m_gz[1]) + 3) % 12
    return GAN[g_idx] + ZHI[z_idx]

def get_ming_gong(zhi_yue, h_zhi):
    """命宮：(14 或 26) - (月支數 + 時支數)"""
    m_val = (ZHI.index(ZHI[(zhi_yue + 1) % 12]) + 1) 
    h_val = ZHI.index(h_zhi) + 1
    mg_idx = (14 - (m_val + h_val)) % 12
    if mg_idx <= 0: mg_idx += 12
    return ZHI[mg_idx-1] + "宮"

def get_hour_gz_detailed(day_gan, hour_name, is_late_rat=False, next_day_gan=None):
    """時柱計算 (含早晚子時邏輯)"""
    offset = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
    target_gan = next_day_gan if is_late_rat else day_gan
    start_gan_idx = offset.get(target_gan, 0)
    zhi_idx = ZHI.index(hour_name[0]) if "子" not in hour_name else 0
    h_gan = GAN[(start_gan_idx + zhi_idx) % 10]
    return h_gan + ZHI[zhi_idx]

def get_hour_star_pro(is_yang, day_zhi, hour_idx, is_late_rat=False, next_day_is_yang=None, next_day_zhi=None):
    """時星計算 (含晚子時隔日邏輯)"""
    u_yang = next_day_is_yang if is_late_rat else is_yang
    u_zhi = next_day_zhi if is_late_rat else day_zhi
    u_h_idx = 0 if is_late_rat else hour_idx
    
    if u_yang: # 陽遁
        start_val = 1 if u_zhi in "子午卯酉" else (7 if u_zhi in "寅申巳亥" else 4)
        val = (start_val + u_h_idx - 1) % 9 + 1
    else: # 陰遁
        start_val = 9 if u_zhi in "子午卯酉" else (3 if u_zhi in "寅申巳亥" else 6)
        val = (start_val - u_h_idx - 1) % 9 + 1
    return STARS[val]

def get_day_basic_data(dt_date, tz_info):
    """計算當日基礎參數，需傳入時區以轉換UTC計算節氣"""
    # 構造當日中午時間，並轉為UTC以獲取精確太陽黃經
    local_noon = datetime.combine(dt_date, time(12, 0))
    local_dt = tz_info.localize(local_noon)
    utc_dt = local_dt.astimezone(pytz.utc)
    
    lon = get_solar_lon(utc_dt)
    term_idx = int(lon // 15)
    is_yang = not (90 <= lon < 270)
    
    # 1. 計算邏輯年 (立春分界)
    logic_y = dt_date.year
    if lon < 315 and dt_date.month <= 3: logic_y -= 1
    
    # 年柱 (年干支)
    y_gan_idx = (logic_y - 4) % 10 # 獲取年干索引 (甲=0)
    y_gz = GAN[y_gan_idx] + ZHI[(logic_y - 4) % 12]
    
    # 2. 月柱計算 (修正版)
    # 立春 315 度 = 寅月 (1)
    shifted_lon = (lon - 315) % 360
    zhi_yue = int(shifted_lon // 30) + 1
    
    # 五虎遁：甲己之年丙作首。即 (年干索引 % 5) * 2 + 2 = 寅月天干索引
    # zhi_yue 為 1 (寅), 2 (卯)...
    # 公式：(年干索引 % 5 * 2 + 2 + (zhi_yue - 1)) % 10
    # 簡化後：(年干索引 % 5 * 2 + zhi_yue + 1) % 10
    m_gan_idx = (y_gan_idx % 5 * 2 + zhi_yue + 1) % 10
    m_gz = GAN[m_gan_idx] + ZHI[(zhi_yue + 1) % 12]
    
    # 日柱
    ref_day = datetime(2025, 12, 21).date()
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

    return {
        "y_gz": y_gz, "m_gz": m_gz, "d_gz": day_gz, 
        "y_s": y_s, "m_s": m_s, "d_s": d_s, 
        "is_yang": is_yang, "term_idx": term_idx, 
        "day_gan": day_gz[0], "day_zhi": day_gz[1],
        "zhi_yue": zhi_yue
    }

def get_tz_label(dt_date, tz_info):
    """判斷該日期在該時區的顯示名稱 (BST/GMT/HKT)"""
    # 取當日中午做判斷
    dt = datetime.combine(dt_date, time(12, 0))
    localized = tz_info.localize(dt)
    return localized.tzname()

def run_final_calendar(start_str, days, tz_name="Europe/London"):
    start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
    target_tz = pytz.timezone(tz_name)
    rows = []
    
    for i in range(days):
        curr_date = start_d + timedelta(days=i)
        next_date = curr_date + timedelta(days=1)
        
        # 獲取基礎數據
        d = get_day_basic_data(curr_date, target_tz)
        d_next = get_day_basic_data(next_date, target_tz)
        
        # 獲取農曆 (新增)
        lunar_str = get_lunar_str(curr_date)
        
        # 獲取時區標籤 (如 BST, GMT, HKT)
        tz_label = get_tz_label(curr_date, target_tz)

        # 節氣顯示
        prev_d_data = get_day_basic_data(curr_date - timedelta(days=1), target_tz)
        display_term = SOLAR_TERMS[d["term_idx"]] if d["term_idx"] != prev_d_data["term_idx"] else ""

        # 定義 13 個時段
        time_slots = [
            (0, "早子時", "00:00-01:00", False), (1, "丑時", "01:00-03:00", False), 
            (2, "寅時", "03:00-05:00", False), (3, "卯時", "05:00-07:00", False), 
            (4, "辰時", "07:00-09:00", False), (5, "巳時", "09:00-11:00", False), 
            (6, "午時", "11:00-13:00", False), (7, "未時", "13:00-15:00", False), 
            (8, "申時", "15:00-17:00", False), (9, "酉時", "17:00-19:00", False), 
            (10, "戌時", "19:00-21:00", False), (11, "亥時", "21:00-23:00", False),
            (0, "晚子時", "23:00-24:00", True)
        ]

        for idx, name, period, is_late in time_slots:
            # 時柱
            h_gz = get_hour_gz_detailed(d["day_gan"], name, is_late, d_next["day_gan"])
            # 時星
            h_s = get_hour_star_pro(d["is_yang"], d["day_zhi"], idx, is_late, d_next["is_yang"], d_next["day_zhi"])
            
            rows.append({
                "日期": curr_date,
                "農曆": lunar_str, # 加入農曆欄位
                "時段": name,
                "時間": period,
                "時區": tz_label,
                "節氣": display_term if name == "早子時" else "",
                
                "年柱": d["y_gz"], "年屬性": get_gz_prop(d["y_gz"]), "年納音": NAYIN.get(d["y_gz"]),
                "月柱": d["m_gz"], "月屬性": get_gz_prop(d["m_gz"]), "月納音": NAYIN.get(d["m_gz"]),
                "日柱": d["d_gz"], "日屬性": get_gz_prop(d["d_gz"]), "日納音": NAYIN.get(d["d_gz"]),
                "時柱": h_gz,      "時屬性": get_gz_prop(h_gz),      "時納音": NAYIN.get(h_gz),
                
                "胎元": get_tai_yuan(d["m_gz"]), "胎元屬性": get_gz_prop(get_tai_yuan(d["m_gz"])),
                "命宮": get_ming_gong(d["zhi_yue"], h_gz[1]),
                
                "年星": d["y_s"], "年星五行": STAR_WUXING[d["y_s"]],
                "月星": d["m_s"], "月星五行": STAR_WUXING[d["m_s"]],
                "日星": d["d_s"], "日星五行": STAR_WUXING[d["d_s"]],
                "時星": h_s,      "時星五行": STAR_WUXING[h_s]
            })
            
    return pd.DataFrame(rows)

# --- 執行設定 ---
if __name__ == "__main__":
    # --- 設定區域 1: 英國 (自動切換 GMT/BST) ---
    print("正在生成英國 (UK) 曆法...")
    df_uk = run_final_calendar("1976-01-01", 365*70, tz_name="Europe/London")
    df_uk.to_excel("3.1Calendar_1976_UK_Full.xlsx", index=False)
    
    # --- 設定區域 2: 香港 (HKT) ---
    print("正在生成香港 (HK) 曆法...")
    df_hk = run_final_calendar("1976-01-01", 365*70, tz_name="Asia/Hong_Kong")
    df_hk.to_excel("3.1Calendar_1976_HK_Full.xlsx", index=False)
    
    print("✅ 完成！已生成兩份檔案 (包含修正後的農曆顯示與月柱計算)：")
    print("1. 3.1Calendar_1976_UK_Full.xlsx")
    print("2. 3.1Calendar_1976_HK_Full.xlsx")
    
    # 預覽檢查
    print("\n--- 預覽數據 (包含農曆與修正的月柱) ---")
    print(df_hk[["日期", "農曆", "時段", "年柱", "月柱", "日柱"]].head(13).to_string())