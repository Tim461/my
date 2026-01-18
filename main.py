import requests
import datetime
from ics import Calendar, Event
import json
import os
import pytz

# === 配置 ===
DAYS_TO_FETCH = 14 # 抓取未来14天
BASE_URL = "https://qhcal-api.jin10.com/data"

# 经过验证可用的 Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-app-id": "1coXNOi34tU5TDTl", 
    "x-version": "1.0",
    "Referer": "https://qihuo.jin10.com/",
    "Origin": "https://qihuo.jin10.com",
    "Accept-Encoding": "gzip, deflate"
}

def run_calendar_gen():
    c = Calendar()
    tz = pytz.timezone('Asia/Shanghai')
    
    print(f"开始抓取期货日历 (未来 {DAYS_TO_FETCH} 天)...")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")
        date_str_display = target_date.strftime("%Y-%m-%d")
        
        url = f"{BASE_URL}?date={date_str_api}"
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                print(f"[{date_str_display}] 请求失败: {resp.status_code}")
                continue
                
            json_resp = resp.json()
            data_list = json_resp.get('data', [])
            
            if not data_list:
                print(f"[{date_str_display}] 无数据 (可能是周末)")
                continue

            print(f"[{date_str_display}] 抓取到 {len(data_list)} 条数据")

            for item in data_list:
                # 1. 提取标题
                title_text = item.get('title') or item.get('name') or '未命名事件'
                country = item.get('country', '')
                
                # 2. 提取数值
                def safe_str(val): return str(val) if val is not None else "--"
                actual = safe_str(item.get('actual'))
                consensus = safe_str(item.get('consensus'))
                previous = safe_str(item.get('previous'))
                unit = safe_str(item.get('unit'))
                
                # 3. 处理星星和关联
                star = item.get('star', 0)
                star_icon = "★" * int(star) if str(star).isdigit() else ""
                affect = item.get('qh_affect_text', '')
                affect_str = f"[{affect}]" if affect else ""

                # 4. 组合内容
                full_title = f"{star_icon} {affect_str} {title_text}".strip()
                
                description = (
                    f"国家: {country}\n"
                    f"重要性: {star}\n"
                    f"----------------\n"
                    f"今值: {actual}\n"
                    f"预测: {consensus}\n"
                    f"前值: {previous} {unit}"
                )

                e = Event()
                e.name = full_title
                e.description = description
                
                # 5. 时间处理
                pub_time = item.get('publictime')
                try:
                    if pub_time and len(pub_time) > 10:
                        dt = datetime.datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                        dt = tz.localize(dt)
                        e.begin = dt
                        e.duration = {"minutes": 15}
                    else:
                        e.begin = date_str_display
                        e.make_all_day()
                    c.events.add(e)
                except:
                    continue

        except Exception as e:
            print(f"错误: {e}")

    # 保存
    with open('calendar.ics', 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    print("日历生成完成！")

if __name__ == "__main__":
    run_calendar_gen()
