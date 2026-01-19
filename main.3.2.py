import pandas as pd
from datetime import datetime, timedelta, time
import pytz
from skyfield import api
from lunar_python import Lunar

# --- 初始化天文引擎 ---
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

GAN_PROPS = {"甲": "陽木", "乙": "陰木", "丙": "陽火", "丁": "陰火", "戊": "陽土", "己": "陰土", "庚": "陽金", "辛": "陰金", "壬": "陽水", "癸": "陰水"}
ZHI_PROPS = {"子": "陽水", "丑": "陰土", "寅": "陽木", "卯": "陰木", "辰": "陽土", "巳": "陰火", "午": "陽火", "未": "陰土", "申": "陽金", "酉": "陰金", "戌": "陽土", "亥": "陰水"}

SOLAR_TERMS = ["春分", "清明", "穀雨", "立夏", "小滿", "芒種", "夏至", "小暑", "大暑", "立秋", "處暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至", "小寒", "大寒", "立春", "雨水", "驚蟄"]

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
    lon = earth.at(t).observe(sun).ecliptic_latlon()[1].degrees
    return lon

def get_gz_prop(gz_str):
    if not gz_str or len(gz_str) < 2: return ""
    return f"{GAN_PROPS.get(gz_str[0], '')}{ZHI_PROPS.get(gz_str[1], '')}"

def get_lunar_str(dt_date):
    try:
        dt_val = datetime.combine(dt_date, time(12, 0))
        lunar = Lunar.fromDate(dt_val)
        return f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    except: return ""

def get_hour_gz_detailed(day_gan, hour_name, is_late_rat=False, next_day_gan=None):
    offset = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4, "丁": 6, "壬": 6, "戊": 8, "癸": 8}
    target_gan = next_day_gan if is_late_rat else day_gan
    start_gan_idx = offset.get(target_gan, 0)
    zhi_idx = ZHI.index(hour_name[0]) if "子" not in hour_name else 0
    return GAN[(start_gan_idx + zhi_idx) % 10] + ZHI[zhi_idx]

def get_day_basic_data(dt_date, tz_info):
    utc_dt = tz_info.localize(datetime.combine(dt_date, time(12, 0))).astimezone(pytz.utc)
    lon = get_solar_lon(utc_dt)
    
    # 1. 邏輯年 (立春界定) 與 年納音修正
    logic_y = dt_date.year
    if lon < 315 and dt_date.month <= 3: logic_y -= 1
    y_gz = GAN[(logic_y - 4) % 10] + ZHI[(logic_y - 4) % 12]
    y_nayin = NAYIN.get(y_gz, "") # 2025年1月1日會得到甲辰年的覆燈火 (佛燈火)

    # 2. 月柱與月飛星修正
    shifted_lon = (lon - 315) % 360
    zhi_yue = int(shifted_lon // 30) + 1 # 1=寅, 2=卯... 11=子, 12=丑
    m_gz = GAN[((logic_y % 5 * 2) + zhi_yue + 1) % 10] + ZHI[(zhi_yue + 1) % 12]
    
    # 月飛星規則：子午卯酉年起8，辰戌丑未年起5，寅申巳亥年起2 (逆行)
    y_zhi = y_gz[1]
    m_base = 8 if y_zhi in "子午卯酉" else (5 if y_zhi in "辰戌丑未" else 2)
    m_s_idx = (m_base - (zhi_yue - 1) - 1) % 9 + 1
    m_s = STARS[m_s_idx]

    # 3. 日柱與其餘數據
    ref_day = datetime(2025, 12, 21).date()
    d_diff = (dt_date - ref_day).days
    day_gz = GAN[d_diff % 10] + ZHI[d_diff % 12]
    is_yang = not (90 <= lon < 270)
    
    return {
        "y_gz": y_gz, "y_nayin": y_nayin, "m_gz": m_gz, "m_s": m_s, 
        "m_s_wuxing": STAR_WUXING[m_s], "d_gz": day_gz, "zhi_yue": zhi_yue,
        "is_yang": is_yang, "day_gan": day_gz[0], "day_zhi": day_gz[1]
    }

def run_final_calendar(start_str, days, tz_name):
    start_d = datetime.strptime(start_str, "%Y-%m-%d").date()
    target_tz = pytz.timezone(tz_name)
    rows = []
    
    for i in range(days):
        curr_date = start_d + timedelta(days=i)
        d = get_day_basic_data(curr_date, target_tz)
        d_next = get_day_basic_data(curr_date + timedelta(days=1), target_tz)
        
        time_slots = [(0, "早子時", "00-01", False), (6, "午時", "11-13", False), (0, "晚子時", "23-24", True)] # 簡化範例，實際可補全13時段
        
        for idx, name, period, is_late in time_slots:
            h_gz = get_hour_gz_detailed(d["day_gan"], name, is_late, d_next["day_gan"])
            rows.append({
                "日期": curr_date, "農曆": get_lunar_str(curr_date), "時段": name,
                "年柱": d["y_gz"], "年納音": d["y_nayin"], 
                "月柱": d["m_gz"], "月飛星": d["m_s"], "月星五行": d["m_s_wuxing"],
                "日柱": d["d_gz"], "時柱": h_gz, "時區": tz_name
            })
    return pd.DataFrame(rows)

if __name__ == "__main__":
    # 輸出 1: 香港
    print("正在生成香港 (HK) 曆法...")
    df_hk = run_final_calendar("1976-01-01", 365*70, "Asia/Hong_Kong")
    df_hk.to_excel("3.2Calendar_1976_HK_Updated.xlsx", index=False)
    
    # 輸出 2: 英國
    print("正在生成英國 (UK) 曆法...")
    df_uk = run_final_calendar("1976-01-01", 365*70, "Europe/London")
    df_uk.to_excel("3.2Calendar_1976_UK_Updated.xlsx", index=False)
    
    print("✅ 重做完成！已生成 HK 與 UK 兩份檔案。")