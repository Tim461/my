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

# 起始显示时间：每天早上 08:00
START_HOUR = 8
START_MINUTE = 0
# 【修改点】间隔时间：从 5 分钟改为 15 分钟
INTERVAL_MINUTES = 15
# ===========================================

def safe_str(val):
    return str(val) if val is not None else "--"

def get_star_icon(star_num):
    try:
        return "★" * int(star_num)
    except:
        return ""

def fetch_economic_data(date_str):
    """获取经济数据，返回中间格式列表"""
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
    """获取财经大事，返回中间格式列表"""
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
    
    print(f"====== 开始执行 (抓取未来 {DAYS_TO_FETCH} 天) - 虚拟时间轴(15分钟间隔) ======")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")
        date_str_display = target_date.strftime("%Y-%m-%d")
        
        print(f"处理日期: {date_str_display} ...")
        
        list_data = fetch_economic_data(date_str_api)
        time.sleep(0.2)
        list_event = fetch_financial_events(date_str_api)
        
        all_items = list_data + list_event
        
        if not all_items:
            continue
            
        print(f"  -> 共获取 {len(all_items)} 条事件，正在按 15分钟 间隔重排...")

        def sort_key(x):
            if x['sort_dt'] is None:
                return datetime.datetime(1970,1,1)
            return x['sort_dt']
            
        all_items.sort(key=sort_key)
        
        current_virtual_time = target_date.replace(hour=START_HOUR, minute=START_MINUTE, second=0, microsecond=0)
        
        for item in all_items:
            e = Event()
            star_icon = get_star_icon(item['star'])
            
            if item['type'] == 'data':
                affect_str = f"[{item['affect']}]" if item['affect'] else ""
                e.name = f"{item['time_display']} {star_icon} {affect_str} {item['title']}".strip()
            else:
                e.name = f"{item['time_display']} [大事] {star_icon} {item['country']} {item['title']}".strip()
            
            e.description = item['desc']
            e.begin = current_virtual_time
            e.duration = {"minutes": 0} 
            c.events.add(e)
            
            # 【核心逻辑生效处】每次加 15 分钟
            current_virtual_time += datetime.timedelta(minutes=INTERVAL_MINUTES)

    output_file = 'calendar.ics'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    if os.path.exists(output_file):
        print(f"\n====== 完成 ======")
        print(f"文件已生成，按每隔 {INTERVAL_MINUTES} 分钟排列。")
    else:
        print("\n❌ 错误: 文件生成失败")

if __name__ == "__main__":
    main()
