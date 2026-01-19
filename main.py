import requests
import datetime
# 【改回 Event】因为绝大多数日历不支持订阅 Todo
from ics import Calendar, Event
import json
import os
import pytz
import time

# ================= 配置区域 =================
# 抓取未来 60 天
DAYS_TO_FETCH = 60

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

# 起始显示时间：每天早上 08:00
START_HOUR = 8
START_MINUTE = 0
# 间隔时间：10分钟 (列表式排列的核心)
INTERVAL_MINUTES = 10
# ===========================================

def safe_str(val):
    return str(val) if val is not None else "--"

def get_star_icon(star_num):
    try:
        return "★" * int(star_num)
    except:
        return ""

def fetch_economic_data(date_str):
    url = f"{URL_DATA}?date={date_str}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return []
        data_list = resp.json().get('data', [])
        
        for item in data_list:
            title_text = item.get('title') or item.get('name') or '未命名数据'
            country = item.get('country', '')
            actual = safe_str(item.get('actual'))
            consensus = safe_str(item.get('consensus'))
            previous = safe_str(item.get('previous'))
            unit = safe_str(item.get('unit'))
            star = item.get('star', 0)
            affect = item.get('qh_affect_text', '')
            
            pub_time = item.get('publictime')
            sort_dt = None 
            time_str_display = "" 

            if pub_time and len(pub_time) > 10:
                try:
                    sort_dt = datetime.datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    time_str_display = sort_dt.strftime("%H:%M")
                except:
                    pass
            
            results.append({
                'type': 'data',
                'sort_dt': sort_dt, 
                'time_display': time_str_display,
                'star': star,
                'country': country,
                'title': title_text,
                'affect': affect,
                'desc': (
                    f"【经济数据】\n"
                    f"真实时间: {time_str_display}\n"
                    f"项目: {title_text}\n"
                    f"国家: {country}\n"
                    f"重要性: {star}星\n"
                    f"----------------\n"
                    f"今值: {actual}\n"
                    f"预测: {consensus}\n"
                    f"前值: {previous} {unit}"
                )
            })
    except Exception as e:
        print(f"  [数据抓取错] {e}")
    return results

def fetch_financial_events(date_str):
    url = f"{URL_EVENT}?date={date_str}"
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200: return []
        event_list = resp.json().get('data', [])

        for item in event_list:
            content = item.get('eventcontent', '未命名事件')
            country = item.get('country', '')
            people = item.get('people')
            star = item.get('star', 0)
            short_title = content if len(content) < 30 else content[:28] + "..."
            
            time_str = item.get('dateTimeStr')
            sort_dt = None
            time_str_display = ""

            if time_str and len(time_str) > 10:
                try:
                    sort_dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    time_str_display = sort_dt.strftime("%H:%M")
                except:
                    pass

            results.append({
                'type': 'event',
                'sort_dt': sort_dt,
                'time_display': time_str_display,
                'star': star,
                'country': country,
                'title': short_title,
                'people': people,
                'desc': (
                    f"【财经大事】\n"
                    f"真实时间: {time_str_display}\n"
                    f"内容: {content}\n"
                    f"国家: {country}\n"
                    f"人物: {people if people else '--'}\n"
                    f"重要性: {star}星"
                )
            })
    except Exception as e:
        print(f"  [大事抓取错] {e}")
    return results

def main():
    c = Calendar()
    tz = pytz.timezone('Asia/Shanghai')
    
    print(f"====== 开始执行 (抓取未来 {DAYS_TO_FETCH} 天) - 伪装任务列表模式 ======")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")
        date_str_display = target_date.strftime("%Y-%m-%d")
        
        print(f"处理日期: {date_str_display} ...")
        
        list_data = fetch_economic_data(date_str_api)
        time.sleep(0.1)
        list_event = fetch_financial_events(date_str_api)
        
        all_items = list_data + list_event
        
        if not all_items:
            continue
            
        print(f"  -> 共 {len(all_items)} 条，正在排版...")

        def sort_key(x):
            if x['sort_dt'] is None:
                return datetime.datetime(1970,1,1)
            return x['sort_dt']
            
        all_items.sort(key=sort_key)
        
        # 虚拟时间起点
        current_virtual_time = target_date.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
        
        for item in all_items:
            # 【核心改回 Event】
            e = Event()
            
            star_icon = get_star_icon(item['star'])
            
            if item['type'] == 'data':
                affect_str = f"[{item['affect']}]" if item['affect'] else ""
                e.name = f"{item['time_display']} {star_icon} {affect_str} {item['title']}".strip()
            else:
                e.name = f"{item['time_display']} [大事] {star_icon} {item['country']} {item['title']}".strip()
            
            e.description = item['desc']
            
            # 设定时间点
            e.begin = current_virtual_time
            # 【关键】设为0分钟，这样在日历里它就是一条线，看起来像 Task
            e.duration = {"minutes": 0}
            
            c.events.add(e)
            
            # 时间递增 10 分钟
            current_virtual_time += datetime.timedelta(minutes=INTERVAL_MINUTES)

    output_file = 'calendar.ics'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    if os.path.exists(output_file):
        print(f"\n====== 完成 ======")
        print(f"文件已生成，Event 伪装为列表，间隔 {INTERVAL_MINUTES} 分钟。")
    else:
        print("\n❌ 错误: 文件生成失败")

if __name__ == "__main__":
    main()
