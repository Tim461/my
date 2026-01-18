import requests
import datetime
from ics import Calendar, Event
import json
import os
import pytz

# === 诊断配置 ===
DAYS_TO_FETCH = 3 # 先只抓3天，方便看日志
BASE_URL = "https://qhcal-api.jin10.com/data"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "x-app-id": "1coXNOi34tU5TDTl", 
    "x-version": "1.0",
    "Referer": "https://qihuo.jin10.com/",
    "Origin": "https://qihuo.jin10.com",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive"
}

def debug_run():
    c = Calendar()
    tz = pytz.timezone('Asia/Shanghai')
    
    print("====== 开始诊断模式运行 ======")
    
    # 1. 打印当前脚本运行的时间和 IP (检查是否被墙)
    print(f"脚本运行时间: {datetime.datetime.now(tz)}")
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
        print(f"GitHub Action 当前 IP: {ip}")
    except:
        print("无法获取 IP")

    for i in range(DAYS_TO_FETCH):
        target_date = datetime.datetime.now(tz) + datetime.timedelta(days=i)
        date_str = target_date.strftime("%Y%m%d")
        
        url = f"{BASE_URL}?date={date_str}"
        print(f"\n[{i+1}] 正在请求日期: {date_str}")
        print(f"请求 URL: {url}")
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"状态码: {resp.status_code}")
            
            # 【关键】如果状态码不是 200，打印报错信息
            if resp.status_code != 200:
                print(f"❌ 请求失败，响应头: {resp.headers}")
                print(f"❌ 响应内容: {resp.text[:500]}") # 只打印前500字
                continue
            
            # 【关键】强制打印服务器返回的前 1000 个字符
            # 这样我们就能看到是返回了空列表 [] 还是返回了 "Forbidden"
            raw_text = resp.text
            print(f"✅ 服务器返回原始内容 (前500字符):")
            print(raw_text[:500])
            
            try:
                json_data = resp.json()
                data_list = json_data.get('data', [])
                
                if not data_list:
                    print("⚠️ 警告: 'data' 字段为空列表 [] (当天可能无数据)")
                    continue
                    
                print(f"✨ 成功解析到 {len(data_list)} 条数据")
                
                # 开始添加事件
                for item in data_list:
                    title = item.get('title') or item.get('name')
                    publictime = item.get('publictime')
                    
                    e = Event()
                    e.name = f"{title}"
                    e.begin = datetime.datetime.now() # 临时占位，防止报错
                    # 只要能走到这里，说明解析没问题
                    c.events.add(e)
                    
            except json.JSONDecodeError:
                print("❌ JSON 解析失败 (返回的可能不是 JSON)")
                
        except Exception as e:
            print(f"❌ 发生异常: {e}")

    # 尝试保存文件
    with open('calendar.ics', 'w', encoding='utf-8') as f:
        f.writelines(c.serialize_iter())
    
    # 检查文件大小
    file_size = os.path.getsize('calendar.ics')
    print(f"\n====== 运行结束 ======")
    print(f"生成文件 calendar.ics 大小: {file_size} 字节")
    if file_size < 100:
        print("❌ 文件太小，说明日历是空的！")
    else:
        print("✅ 文件生成看似正常")

if __name__ == "__main__":
    debug_run()
