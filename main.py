import requests
import datetime
from ics import Calendar, Event
import json
import os
import pytz
import time

# ================= 配置区域 =================
# 抓取未来多少天的数据
DAYS_TO_FETCH = 14

# 两个 API 的基础地址
URL_DATA = "https://qhcal-api.jin10.com/data"   # 经济数据
URL_EVENT = "https://qhcal-api.jin10.com/event" # 财经大事

# 统一的请求头 (两个接口通用)
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
    """安全转换为字符串，处理 None"""
    return str(val) if val is not None else "--"

def get_star_icon(star_num):
    """根据数字生成星星图标"""
    try:
        return "★" * int(star_num)
    except:
        return ""

def process_economic_data(date_str, date_display, calendar, tz):
    """处理【经济数据】接口 (/data)"""
    url = f"{URL_DATA}?date={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"  [数据] 请求失败: {resp.status_code}")
            return

        data_list = resp.json().get('data', [])
        if not data_list:
            print(f"  [数据] 无内容")
            return
        
        print(f"  [数据] 解析到 {len(data_list)} 条")

        for item in data_list:
            # 1. 提取字段
            title_text = item.get('title') or item.get('name') or '未命名数据'
            country = item.get('country', '')
            actual = safe_str(item.get('actual'))
            consensus = safe_str(item.get('consensus'))
            previous = safe_str(item.get('previous'))
            unit = safe_str(item.get('unit'))
            star = item.get('star', 0)
            affect = item.get('qh_affect_text', '')
            
            # 2. 构建显示内容
            star_icon = get_star_icon(star)
            affect_str = f"[{affect}]" if affect else ""
            
            # 标题: ★★★ [原油] 美国EIA原油库存
            full_title = f"{star_icon} {affect_str} {title_text}".strip()
            
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

            # 3. 创建事件
            e = Event()
            e.name = full_title
            e.description = description
            
            # 4. 时间处理 (使用 publictime: "2026-01-22 05:30:00")
            pub_time = item.get('publictime')
            try:
                if pub_time and len(pub_time) > 10:
                    dt = datetime.datetime.strptime(pub_time, "%Y-%m-%d %H:%M:%S")
                    dt = tz.localize(dt)
                    e.begin = dt
                    e.duration = {"minutes": 15}
                else:
                    e.begin = date_display
                    e.make_all_day()
                calendar.events.add(e)
            except Exception as err:
                print(f"    跳过数据条目(时间错误): {err}")

    except Exception as e:
        print(f"  [数据] 异常: {e}")

def process_financial_events(date_str, date_display, calendar, tz):
    """处理【财经大事】接口 (/event)"""
    url = f"{URL_EVENT}?date={date_str}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            print(f"  [大事] 请求失败: {resp.status_code}")
            return

        event_list = resp.json().get('data', [])
        if not event_list:
            print(f"  [大事] 无内容")
            return

        print(f"  [大事] 解析到 {len(event_list)} 条")

        for item in event_list:
            # 1. 提取字段 (根据你提供的 /event JSON 结构)
            # 核心内容在 eventcontent 字段
            content = item.get('eventcontent', '未命名事件')
            country = item.get('country', '')
            people = item.get('people') # 可能为 null
            star = item.get('star', 0)
            
            # 2. 构建显示内容
            star_icon = get_star_icon(star)
            
            # 标题: [大事] ★★ 欧洲央行公布会议纪要
            # 如果内容太长，标题截取前20字
            short_title = content if len(content) < 30 else content[:28] + "..."
            people_str = f"人物: {people}\n" if people else ""
            
            full_title = f"[大事] {star_icon} {country} {short_title}".strip()
            
            description = (
                f"【财经大事】\n"
                f"内容: {content}\n"
                f"国家: {country}\n"
                f"{people_str}"
                f"重要性: {star}星"
            )

            # 3. 创建事件
            e = Event()
            e.name = full_title
            e.description = description
            
            # 4. 时间处理 (使用 dateTimeStr: "2026-01-22 09:20:00")
            time_str = item.get('dateTimeStr')
            try:
                if time_str and len(time_str) > 10:
                    dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    dt = tz.localize(dt)
                    e.begin = dt
                    e.duration = {"minutes": 30} # 大事通常持续时间长一点，设为30分钟
                else:
                    e.begin = date_display
                    e.make_all_day()
                calendar.events.add(e)
            except Exception as err:
                print(f"    跳过大事条目(时间错误): {err}")

    except Exception as e:
        print(f"  [大事] 异常: {e}")

def main():
    # 初始化日历
    c = Calendar()
    tz = pytz.timezone('Asia/Shanghai')
    
    print(f"====== 开始执行 (抓取未来 {DAYS_TO_FETCH} 天) ======")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")   # 20260122
        date_str_display = target_date.strftime("%Y-%m-%d") # 2026-01-22
        
        print(f"\n处理日期: {date_str_display} ...")
        
        # 步骤 1: 抓取经济数据
        process_economic_data(date_str_api, date_str_display, c, tz)
        
        # 步骤 2: 抓取财经大事 (休息 0.5秒防止请求太快)
        time.sleep(0.5)
        process_financial_events(date_str_api, date_str_display, c, tz)

    # 保存文件
    output_file = 'calendar.ics'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    # 检查文件大小
    try:
        size = os.path.getsize(output_file)
        print(f"\n====== 完成 ======")
        print(f"文件 {output_file} 已生成，大小: {size} 字节")
    except:
        print("文件生成失败")

if __name__ == "__main__":
    main()
