import requests
import datetime
from ics import Calendar, Event
import json
import os
import pytz

# ================= 配置区域 =================
# 抓取未来多少天的数据（建议 7-14 天）
DAYS_TO_FETCH = 14

# 金十数据 API 地址
BASE_URL = "https://qhcal-api.jin10.com/data"

# 必须的请求头 (基于你提供的抓包数据)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-app-id": "1coXNOi34tU5TDTl", 
    "x-version": "1.0",
    "Referer": "https://qihuo.jin10.com/",
    "Origin": "https://qihuo.jin10.com",
    # 强制使用 gzip，防止服务器返回 zstd 导致乱码
    "Accept-Encoding": "gzip, deflate"
}
# ===========================================

def fetch_and_generate():
    # 初始化日历
    c = Calendar()
    # 设定时区为北京时间
    tz = pytz.timezone('Asia/Shanghai')
    
    print(f"开始抓取未来 {DAYS_TO_FETCH} 天的数据...")

    for i in range(DAYS_TO_FETCH):
        # 计算日期
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str_api = target_date.strftime("%Y%m%d")   # API需要的格式: 20260122
        date_str_display = target_date.strftime("%Y-%m-%d") 
        
        url = f"{BASE_URL}?date={date_str_api}"
        print(f"[{i+1}/{DAYS_TO_FETCH}] 正在获取: {date_str_display} ...")
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            
            if resp.status_code != 200:
                print(f"  -> 请求失败，状态码: {resp.status_code}")
                continue
                
            json_resp = resp.json()
            
            # 根据你提供的 JSON，数据在 'data' 字段中
            data_list = json_resp.get('data', [])
            
            if not data_list:
                print("  -> 当日无数据")
                continue

            for item in data_list:
                # --- 1. 提取基础信息 ---
                # 使用 'title' 字段，因为它最完整 (例如: "美国至1月16日当周API原油库存(万桶)")
                title_text = item.get('title')
                if not title_text:
                    title_text = item.get('name', '未命名事件')
                
                country = item.get('country', '')
                
                # --- 2. 提取数值 (处理 null 情况) ---
                def safe_str(val):
                    return str(val) if val is not None else "--"

                previous = safe_str(item.get('previous'))
                consensus = safe_str(item.get('consensus'))
                actual = safe_str(item.get('actual'))
                unit = safe_str(item.get('unit'))
                
                # --- 3. 处理重要性 (star) ---
                star_count = item.get('star', 0)
                # 生成星星图标，例如 ★★★
                star_icon = "★" * int(star_count) if str(star_count).isdigit() else ""
                
                # 如果是 0 星或 1 星且没有重要影响，可以选择过滤掉（防止日历太乱）
                # if int(star_count) < 2: continue 

                # --- 4. 提取关联品种 ---
                # 你的数据中有 'qh_affect_text': '原油'
                affect_product = item.get('qh_affect_text')
                affect_str = f"[{affect_product}]" if affect_product else ""

                # --- 5. 组合日历标题 ---
                # 最终效果: ★★★ [原油] 美国至1月16日当周API原油库存(万桶)
                full_title = f"{star_icon} {affect_str} {title_text}".strip()

                # --- 6. 组合描述 (显示在日历备注里) ---
                description = (
                    f"事件: {title_text}\n"
                    f"国家: {country}\n"
                    f"重要性: {star_count}星\n"
                    f"----------------\n"
                    f"今值: {actual}\n"
                    f"预测: {consensus}\n"
                    f"前值: {previous}\n"
                    f"单位: {unit}"
                )

                # --- 7. 创建事件 ---
                e = Event()
                e.name = full_title
                e.description = description
                
                # --- 8. 处理时间 ---
                # 你的数据包含精准的 publictime: "2026-01-22 05:30:00"
                pub_time_str = item.get('publictime')
                
                try:
                    if pub_time_str and len(pub_time_str) > 10:
                        # 解析时间字符串
                        dt = datetime.datetime.strptime(pub_time_str, "%Y-%m-%d %H:%M:%S")
                        # 加上时区信息 (北京时间)
                        dt = tz.localize(dt)
                        
                        e.begin = dt
                        e.duration = {"minutes": 15} # 默认事件持续15分钟
                    else:
                        # 如果没有具体时间，设为全天事件
                        e.begin = date_str_display
                        e.make_all_day()
                        
                    c.events.add(e)
                    
                except Exception as err:
                    print(f"  -> 时间解析错误 '{title_text}': {err}")
                    continue

        except Exception as e:
            print(f"  -> 处理 {date_str_display} 时发生未知错误: {e}")

    # 保存文件
    with open('calendar.ics', 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    print("\n成功！calendar.ics 文件已生成。")

if __name__ == "__main__":
    fetch_and_generate()
