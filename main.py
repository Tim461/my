import requests
import datetime
from ics import Calendar, Event
import json
import os
import pytz
import time

# ================= 配置区域 =================
DAYS_TO_FETCH = 30
URL_DATA = "https://qhcal-api.jin10.com/data"
URL_EVENT = "https://qhcal-api.jin10.com/event"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-app-id": "1coXNOi34tU5TDTl", 
    "x-version": "1.0",
    "Referer": "https://qihuo.jin10.com/",
    "Origin": "https://qihuo.jin10.com",
    "Accept-Encoding": "gzip, deflate"
}
# ===========================================

def safe_str(val):
    return str(val) if val is not None else "--"

def get_star_icon(star_num):
    try:
        return "★" * int(star_num)
    except:
        return ""

def process_economic_data(date_str, date_display, calendar, tz):
    """处理【经济数据】"""
    url = f"{URL_DATA}?date={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return

        data_list = resp.json().get('data', [])
        if not data_list: return
        
        print(f"  [数据] 解析到 {len(data_list)} 条")

        for item in data_list:
            title_text = item.get('title') or item.get('name') or '未命名数据'
            country = item.get('country', '')
            actual = safe_str(item.get('actual'))
            consensus = safe_str(item.get('consensus'))
            previous = safe_str(item.get('previous'))
            unit = safe_str(item.get('unit'))
            star = item.get('star', 0)
            affect = item.get('qh_affect_text', '')
            
            star_icon = get_star_icon(star)
            affect_str = f"[{affect}]" if affect else ""
            
            e = Event()
            
            # --- 时间与标题处理逻辑 ---
            pub_time = item.get('publictime')
            time_prefix = "" # 用于标题显示的时间前缀
            
            try:
                if pub_time and len(pub_time) > 10:
                    dt = datetime.datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    dt = tz.localize(dt)
                    e.begin = dt
                    e.duration = {"minutes": 0} # 瞬时事件，防止重叠
                    # 提取 20:30 这种格式
                    time_prefix = dt.strftime("%H:%M")
                else:
                    e.begin = date_display
                    e.make_all_day()
            except:
                continue # 时间解析失败则跳过

            # 【视觉优化】标题格式：20:30 ★★★ [原油] 美国EIA原油库存
            # 把时间写在标题最前面，强制按顺序阅读
            full_title = f"{time_prefix} {star_icon} {affect_str} {title_text}".strip()
            e.name = full_title
            
            description = (
                f"【经济数据】\n"
                f"项目: {title_text}\n"
                f"国家: {country}\n"
                f"重要性: {star}星\n"
                f"----------------\n"
                f"今值: {actual}\n"
                f"预测: {consensus}\n"
                f"前值: {previous} {unit}"
            )
            e.description = description
            
            calendar.events.add(e)

    except Exception as e:
        print(f"  [数据] 异常: {e}")

def process_financial_events(date_str, date_display, calendar, tz):
    """处理【财经大事】"""
    url = f"{URL_EVENT}?date={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return

        event_list = resp.json().get('data', [])
        if not event_list: return

        print(f"  [大事] 解析到 {len(event_list)} 条")

        for item in event_list:
            content = item.get('eventcontent', '未命名事件')
            country = item.get('country', '')
            people = item.get('people')
            star = item.get('star', 0)
            
            star_icon = get_star_icon(star)
            short_title = content if len(content) < 30 else content[:28] + "..."
            
            e = Event()
            
            # --- 时间与标题处理逻辑 ---
            time_str = item.get('dateTimeStr')
            time_prefix = ""
            
            try:
                if time_str and len(time_str) > 10:
                    dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    dt = tz.localize(dt)
                    e.begin = dt
                    e.duration = {"minutes": 0} # 瞬时事件
                    time_prefix = dt.strftime("%H:%M")
                else:
                    e.begin = date_display
                    e.make_all_day()
            except:
                continue

            # 【视觉优化】标题格式：09:00 [大事] ★★ 欧洲央行...
            full_title = f"{time_prefix} [大事] {star_icon} {country} {short_title}".strip()
            e.name = full_title
            
            description = (
                f"【财经大事】\n"
                f"内容: {content}\n"
                f"国家: {country}\n"
                f"人物: {people if people else '--'}\n"
                f"重要性: {star}星"
            )
            e.description = description
            
            calendar.events.add(e)

    except Exception as e:
        print(f"  [大事] 异常: {e}")

def main():
    c = Calendar()
    tz = pytz.timezone('Asia/Shanghai')
    
    print(f"====== 开始执行 (抓取未来 {DAYS_TO_FETCH} 天) ======")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")
        date_str_display = target_date.strftime("%Y-%m-%d")
        
        print(f"处理日期: {date_str_display} ...")
        process_economic_data(date_str_api, date_str_display, c, tz)
        time.sleep(0.5)
        process_financial_events(date_str_api, date_str_display, c, tz)

    output_file = 'calendar.ics'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    if os.path.exists(output_file):
        print(f"\n====== 完成 ======")
        print(f"文件 {output_file} 已生成，大小: {os.path.getsize(output_file)} 字节")
    else:
        print("\n❌ 错误: 文件生成失败")

if __name__ == "__main__":
    main()
