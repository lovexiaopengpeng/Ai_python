from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
from playwright.sync_api import sync_playwright
import requests
import datetime
import sqlite3
import os
import json
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(__file__), "user_database.db")
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4ef6e7f3-b7d5-437f-940c-213fd6733be9"

scheduler = None

class WeChatMessageRequest(BaseModel):
    is_daily: bool
    send_time: str
    content: str

class WeChatMessage(BaseModel):
    id: int
    is_daily: bool
    send_time: str
    content: str
    status: str
    created_at: str
    updated_at: str

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def db_execute(cursor, query, params=()):
    query = query.replace("%s", "?")
    cursor.execute(query, params)

def send_wechat_message(content: str) -> dict:
    """
    发送企业微信消息
    
    Args:
        content: 消息内容
    
    Returns:
        dict: 发送结果
    """
    try:
        payload = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        result = response.json()
        
        if result.get("errcode") == 0:
            return {
                "success": True,
                "message": "消息发送成功"
            }
        else:
            return {
                "success": False,
                "error": result.get("errmsg", "未知错误")
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def execute_scheduled_message(message_id: int):
    """
    执行定时发送的消息
    
    Args:
        message_id: 消息ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        db_execute(
            cursor,
            "SELECT id, is_daily, send_time, content, status FROM wechat_messages WHERE id = ?",
            (message_id,)
        )
        
        message = cursor.fetchone()
        
        if not message:
            print(f"消息 {message_id} 不存在")
            return
        
        message_id, is_daily, send_time, content, status = message
        
        if status == "cancelled":
            print(f"消息 {message_id} 已取消")
            return
        
        print(f"开始发送消息 {message_id}: {content[:50]}...")
        
        result = send_wechat_message(content)
        
        if result["success"]:
            db_execute(
                cursor,
                "UPDATE wechat_messages SET status = 'sent', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (message_id,)
            )
            print(f"消息 {message_id} 发送成功")
        else:
            db_execute(
                cursor,
                "UPDATE wechat_messages SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (message_id,)
            )
            print(f"消息 {message_id} 发送失败: {result['error']}")
        
        conn.commit()
        
    except Exception as e:
        print(f"发送消息 {message_id} 时发生错误: {e}")
        conn.rollback()
    finally:
        conn.close()

def init_scheduler():
    """
    初始化定时任务调度器
    """
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            jobstores={
                'default': SQLAlchemyJobStore(url='sqlite:///scheduler_jobs.db')
            }
        )
        scheduler.start()
        
        print("✅ 定时任务调度器已启动 (时区: Asia/Shanghai)")
        
        load_scheduled_messages()

def load_scheduled_messages():
    """
    加载数据库中已有的定时消息
    """
    if scheduler is None:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        db_execute(
            cursor,
            "SELECT id, is_daily, send_time, content FROM wechat_messages WHERE status = 'scheduled'"
        )
        
        messages = cursor.fetchall()
        
        for message in messages:
            message_id, is_daily, send_time, content = message
            schedule_message_task(message_id, is_daily, send_time)
        
        print(f"✅ 已加载 {len(messages)} 个定时消息")
        
    except Exception as e:
        print(f"加载定时消息时发生错误: {e}")
    finally:
        conn.close()

def schedule_message_task(message_id: int, is_daily: bool, send_time: str):
    """
    添加定时任务
    
    Args:
        message_id: 消息ID
        is_daily: 是否每日定时发送
        send_time: 发送时间（格式：HH:MM）
    """
    if scheduler is None:
        init_scheduler()
    
    try:
        hour, minute = map(int, send_time.split(":"))
        
        if is_daily:
            trigger = CronTrigger(hour=hour, minute=minute)
            scheduler.add_job(
                execute_scheduled_message,
                trigger=trigger,
                id=f"daily_{message_id}",
                args=[message_id],
                replace_existing=True
            )
            print(f"✅ 已添加每日定时任务: 消息 {message_id}, 时间 {send_time}")
        else:
            now = datetime.datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time <= now:
                target_time += datetime.timedelta(days=1)
            
            trigger = DateTrigger(run_date=target_time)
            scheduler.add_job(
                execute_scheduled_message,
                trigger=trigger,
                id=f"once_{message_id}",
                args=[message_id],
                replace_existing=True
            )
            print(f"✅ 已添加单次定时任务: 消息 {message_id}, 时间 {target_time}")
            
    except Exception as e:
        print(f"添加定时任务时发生错误: {e}")

def cancel_message_task(message_id: int, is_daily: bool):
    """
    取消定时任务
    
    Args:
        message_id: 消息ID
        is_daily: 是否每日定时发送
    """
    if scheduler is None:
        return
    
    try:
        job_id = f"daily_{message_id}" if is_daily else f"once_{message_id}"
        scheduler.remove_job(job_id)
        print(f"✅ 已取消定时任务: 消息 {message_id}")
    except Exception as e:
        print(f"取消定时任务时发生错误: {e}")

def init_database():
    """
    初始化数据库表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS wechat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                is_daily INTEGER NOT NULL DEFAULT 0,
                send_time TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        cursor.execute(create_table_sql)
        
        conn.commit()
        print("✅ 企业微信消息表初始化完成")
        
    except Exception as e:
        print(f"初始化数据库时发生错误: {e}")
    finally:
        conn.close()

@router.post("/wechat/send", summary="发送企业微信消息（支持定时）")
def send_message(request: WeChatMessageRequest):
    """
    发送企业微信消息，支持定时发送
    
    Args:
        request: 消息请求
            - is_daily: 是否每日定时发送
            - send_time: 发送时间（格式：HH:MM）
            - content: 发送内容
    
    Returns:
        dict: 发送结果
    """
    try:
        if not request.send_time or len(request.send_time.split(":")) != 2:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "invalid_time",
                    "message": "发送时间格式错误，应为 HH:MM"
                }
            )
        
        if not request.content or not request.content.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_content",
                    "message": "发送内容不能为空"
                }
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            db_execute(
                cursor,
                "INSERT INTO wechat_messages (is_daily, send_time, content, status) VALUES (?, ?, ?, 'scheduled')",
                (1 if request.is_daily else 0, request.send_time, request.content)
            )
            
            message_id = cursor.lastrowid
            conn.commit()
            
            schedule_message_task(message_id, request.is_daily, request.send_time)
            
            return {
                "success": True,
                "message": "定时消息已创建" if request.is_daily else "单次定时消息已创建",
                "data": {
                    "id": message_id,
                    "is_daily": request.is_daily,
                    "send_time": request.send_time,
                    "content": request.content
                }
            }
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "database_error",
                    "message": f"数据库错误: {str(e)}"
                }
            )
        finally:
            conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "server_error",
                "message": f"服务器错误: {str(e)}"
            }
        )

@router.post("/wechat/send-now", summary="立即发送企业微信消息")
def send_message_now(content: str):
    """
    立即发送企业微信消息
    
    Args:
        content: 发送内容
    
    Returns:
        dict: 发送结果
    """
    try:
        if not content or not content.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_content",
                    "message": "发送内容不能为空"
                }
            )
        
        result = send_wechat_message(content)
        
        if result["success"]:
            return {
                "success": True,
                "message": "消息发送成功"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "send_failed",
                    "message": result["error"]
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "server_error",
                "message": f"服务器错误: {str(e)}"
            }
        )

@router.get("/wechat/messages", summary="获取企业微信消息列表")
def get_messages(status: str = None):
    """
    获取企业微信消息列表
    
    Args:
        status: 状态筛选（可选：scheduled, sent, failed, cancelled）
    
    Returns:
        dict: 消息列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if status:
            db_execute(
                cursor,
                "SELECT id, is_daily, send_time, content, status, created_at, updated_at FROM wechat_messages WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            db_execute(
                cursor,
                "SELECT id, is_daily, send_time, content, status, created_at, updated_at FROM wechat_messages ORDER BY created_at DESC"
            )
        
        messages = cursor.fetchall()
        
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg[0],
                "is_daily": bool(msg[1]),
                "send_time": msg[2],
                "content": msg[3],
                "status": msg[4],
                "created_at": str(msg[5]),
                "updated_at": str(msg[6])
            })
        
        return {
            "success": True,
            "total": len(message_list),
            "messages": message_list
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

@router.get("/wechat/messages/{message_id}", summary="获取单个企业微信消息")
def get_message(message_id: int):
    """
    获取单个企业微信消息
    
    Args:
        message_id: 消息ID
    
    Returns:
        dict: 消息详情
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        db_execute(
            cursor,
            "SELECT id, is_daily, send_time, content, status, created_at, updated_at FROM wechat_messages WHERE id = ?",
            (message_id,)
        )
        
        msg = cursor.fetchone()
        
        if not msg:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "not_found",
                    "message": "消息不存在"
                }
            )
        
        return {
            "success": True,
            "message": {
                "id": msg[0],
                "is_daily": bool(msg[1]),
                "send_time": msg[2],
                "content": msg[3],
                "status": msg[4],
                "created_at": str(msg[5]),
                "updated_at": str(msg[6])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

@router.delete("/wechat/messages/{message_id}", summary="取消企业微信消息")
def cancel_message(message_id: int):
    """
    取消企业微信消息（只能取消待发送的消息）
    
    Args:
        message_id: 消息ID
    
    Returns:
        dict: 取消结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        db_execute(
            cursor,
            "SELECT id, is_daily, status FROM wechat_messages WHERE id = ?",
            (message_id,)
        )
        
        msg = cursor.fetchone()
        
        if not msg:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "not_found",
                    "message": "消息不存在"
                }
            )
        
        msg_id, is_daily, status = msg
        
        if status != "scheduled":
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "invalid_status",
                    "message": f"只能取消待发送的消息，当前状态: {status}"
                }
            )
        
        db_execute(
            cursor,
            "UPDATE wechat_messages SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (message_id,)
        )
        
        conn.commit()
        
        cancel_message_task(message_id, bool(is_daily))
        
        return {
            "success": True,
            "message": "消息已取消"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "database_error",
                "message": f"数据库错误: {str(e)}"
            }
        )
    finally:
        conn.close()

init_database()
init_scheduler()

def crawl_weather_from_website(location: str) -> dict:
    """
    从百度爬取天气信息
    
    Args:
        location: 地点名称
    
    Returns:
        dict: 天气信息
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            """)
            
            try:
                url = f"https://www.baidu.com/s?wd={location}天气"
                print(f'访问: {url}')
                
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(10000)
                
                title = page.title()
                print(f'页面标题: {title}')
                
                webdriver_status = page.evaluate("""() => {
                    return {
                        webdriver: navigator.webdriver,
                        plugins: navigator.plugins.length,
                        languages: navigator.languages
                    };
                }""")
                print(f'navigator.webdriver: {webdriver_status["webdriver"]}')
                
                weather_info = page.evaluate("""() => {
                    const result = {
                        location: "",
                        temperature: "未知",
                        weather: "未知",
                        humidity: "未知",
                        wind: "未知",
                        temperature_range: "未知",
                        aqi: "未知",
                        update_time: ""
                    };
                    
                    const mainWeather = document.querySelector('[class*="weather-main"]');
                    if (mainWeather) {
                        const text = (mainWeather.innerText || '').trim();
                        console.log('Main weather text:', text);
                        
                        const tempMatch = text.match(/(\d+)°/);
                        if (tempMatch) {
                            result.temperature = tempMatch[1] + "°C";
                        }
                        
                        const rangeMatch = text.match(/(\d+)~(\d+)°C/);
                        if (rangeMatch) {
                            result.temperature_range = rangeMatch[1] + "°C ~ " + rangeMatch[2] + "°C";
                        }
                        
                        const weatherKeywords = ['晴', '阴', '多云', '小雨', '中雨', '大雨', '暴雨', '雷阵雨', '小雪', '中雪', '大雪', '雾', '霾'];
                        for (const keyword of weatherKeywords) {
                            if (text.includes(keyword)) {
                                result.weather = keyword;
                                break;
                            }
                        }
                        
                        const windMatch = text.match(/([东南西北]+风)(\d+级)?/);
                        if (windMatch) {
                            result.wind = windMatch[1] + (windMatch[2] || '');
                        }
                        
                        const aqiMatch = text.match(/(\d+)\s+(良|优|轻度污染|中度污染|重度污染)/);
                        if (aqiMatch) {
                            result.aqi = aqiMatch[1] + " " + aqiMatch[2];
                        }
                    }
                    
                    const humidityElements = document.querySelectorAll('*');
                    for (const el of humidityElements) {
                        const text = (el.innerText || '').trim();
                        if (text.includes('湿度')) {
                            const humidityMatch = text.match(/湿度[：:]?\s*(\d+)%?/);
                            if (humidityMatch) {
                                result.humidity = humidityMatch[1] + "%";
                                break;
                            }
                        }
                    }
                    
                    result.update_time = new Date().toLocaleString('zh-CN');
                    
                    return result;
                }""")
                
                print(f'提取的天气信息: {weather_info}')
                
                browser.close()
                
                return {
                    "success": True,
                    "location": location,
                    "temperature": weather_info["temperature"],
                    "temperature_range": weather_info["temperature_range"],
                    "weather": weather_info["weather"],
                    "humidity": weather_info["humidity"],
                    "wind": weather_info["wind"],
                    "aqi": weather_info["aqi"],
                    "update_time": weather_info["update_time"]
                }
                
            except Exception as e:
                browser.close()
                raise e
                
    except Exception as e:
        raise Exception(f"爬取天气信息失败: {str(e)}")

def init_weather_database():
    """
    初始化天气播报配置表
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS weather_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL DEFAULT '长沙',
                district TEXT NOT NULL DEFAULT '岳麓区',
                send_time TEXT NOT NULL DEFAULT '13:50',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        cursor.execute(create_table_sql)
        
        cursor.execute("SELECT COUNT(*) FROM weather_config")
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.execute("""
                INSERT INTO weather_config (city, district, send_time, enabled)
                VALUES (?, ?, ?, ?)
            """, ('长沙', '岳麓区', '13:50', 1))
        
        conn.commit()
        print("✅ 天气播报配置表初始化完成")
        
    except Exception as e:
        print(f"初始化天气播报配置表时发生错误: {e}")
    finally:
        conn.close()

def get_weather_config():
    """
    获取天气播报配置
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, city, district, send_time, enabled 
            FROM weather_config 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        config = cursor.fetchone()
        
        if config:
            return {
                "id": config[0],
                "city": config[1],
                "district": config[2],
                "send_time": config[3],
                "enabled": bool(config[4])
            }
        return None
        
    except Exception as e:
        print(f"获取天气播报配置时发生错误: {e}")
        return None
    finally:
        conn.close()

def update_weather_config(city: str, district: str, send_time: str, enabled: bool):
    """
    更新天气播报配置
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE weather_config 
            SET city = ?, district = ?, send_time = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (city, district, send_time, 1 if enabled else 0))
        
        conn.commit()
        print("✅ 天气播报配置已更新")
        return True
        
    except Exception as e:
        print(f"更新天气播报配置时发生错误: {e}")
        return False
    finally:
        conn.close()

def format_weather_message(weather_info: dict) -> str:
    """
    格式化天气消息
    
    Args:
        weather_info: 天气信息字典
    
    Returns:
        str: 格式化后的消息
    """
    message = "🌤️ 【每日天气播报】🌤️\n\n"
    message += f"📅 日期：{datetime.datetime.now().strftime('%Y-%m-%d')}\n"
    message += f"📍 地点：{weather_info.get('location', '长沙市岳麓区')}\n\n"
    message += f"🌡️ 天气：{weather_info.get('weather', '未知')}\n"
    message += f"🌡️ 温度：{weather_info.get('temperature', '未知')}\n"
    message += f"🌡️ 温度范围：{weather_info.get('temperature_range', '未知')}\n"
    message += f"💧 湿度：{weather_info.get('humidity', '未知')}\n"
    message += f"🌬️ 风向：{weather_info.get('wind', '未知')}\n"
    message += f"🌬️ 空气质量：{weather_info.get('aqi', '未知')}\n\n"
    message += f"⏰ 更新时间：{weather_info.get('update_time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n\n"
    message += "祝您今天心情愉快！😊"
    
    return message

def execute_weather_report():
    """
    执行天气播报任务
    """
    print(f"开始执行天气播报任务...")
    
    try:
        config = get_weather_config()
        
        if not config or not config.get("enabled"):
            print("天气播报功能未启用")
            return
        
        location = f"{config.get('city', '长沙')}{config.get('district', '岳麓区')}"
        
        print(f"爬取 {location} 的天气信息...")
        weather_info = crawl_weather_from_website(location)
        
        if weather_info.get("success"):
            message = format_weather_message(weather_info)
            
            print(f"发送天气消息到企业微信群...")
            result = send_wechat_message(message)
            
            if result.get("success"):
                print("✅ 天气消息发送成功")
            else:
                print(f"❌ 天气消息发送失败: {result.get('error')}")
        else:
            print(f"❌ 爬取天气信息失败")
            
    except Exception as e:
        print(f"执行天气播报任务时发生错误: {e}")

def init_weather_scheduler():
    """
    初始化天气播报定时任务
    """
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    try:
        config = get_weather_config()
        
        if config and config.get("enabled"):
            send_time = config.get("send_time", "13:50")
            hour, minute = map(int, send_time.split(":"))
            
            trigger = CronTrigger(hour=hour, minute=minute)
            scheduler.add_job(
                execute_weather_report,
                trigger=trigger,
                id="weather_report_daily",
                replace_existing=True
            )
            
            print(f"✅ 已添加每日天气播报任务: 时间 {send_time}")
        else:
            print("天气播报功能未启用，跳过定时任务")
            
    except Exception as e:
        print(f"初始化天气播报定时任务时发生错误: {e}")

class WeatherConfigRequest(BaseModel):
    city: str
    district: str
    send_time: str
    enabled: bool

@router.get("/weather/config", summary="获取天气播报配置")
def get_weather_config_api():
    """
    获取天气播报配置
    
    Returns:
        dict: 天气播报配置
    """
    try:
        config = get_weather_config()
        
        if config:
            return {
                "success": True,
                "data": config
            }
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": "not_found",
                    "message": "未找到天气播报配置"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "server_error",
                "message": f"服务器错误: {str(e)}"
            }
        )

@router.post("/weather/config", summary="更新天气播报配置")
def update_weather_config_api(request: WeatherConfigRequest):
    """
    更新天气播报配置
    
    Args:
        request: 天气播报配置请求
    
    Returns:
        dict: 更新结果
    """
    try:
        if not request.city or not request.city.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_city",
                    "message": "城市不能为空"
                }
            )
        
        if not request.district or not request.district.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_district",
                    "message": "区县不能为空"
                }
            )
        
        if not request.send_time or len(request.send_time.split(":")) != 2:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "invalid_time",
                    "message": "发送时间格式错误，应为 HH:MM"
                }
            )
        
        success = update_weather_config(
            request.city.strip(),
            request.district.strip(),
            request.send_time.strip(),
            request.enabled
        )
        
        if success:
            if scheduler is not None:
                try:
                    scheduler.remove_job("weather_report_daily")
                except:
                    pass
                
                if request.enabled:
                    hour, minute = map(int, request.send_time.strip().split(":"))
                    trigger = CronTrigger(hour=hour, minute=minute)
                    scheduler.add_job(
                        execute_weather_report,
                        trigger=trigger,
                        id="weather_report_daily",
                        replace_existing=True
                    )
                    print(f"✅ 已更新每日天气播报任务: 时间 {request.send_time}")
            
            return {
                "success": True,
                "message": "天气播报配置已更新"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "update_failed",
                    "message": "更新天气播报配置失败"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "server_error",
                "message": f"服务器错误: {str(e)}"
            }
        )

@router.post("/weather/send-now", summary="立即发送天气播报")
def send_weather_now():
    """
    立即发送天气播报
    
    Returns:
        dict: 发送结果
    """
    try:
        execute_weather_report()
        
        return {
            "success": True,
            "message": "天气播报已发送"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "send_failed",
                "message": f"发送天气播报失败: {str(e)}"
            }
        )

@router.get("/weather/current", summary="获取当前天气信息")
def get_current_weather(location: str = "长沙市岳麓区"):
    """
    获取当前天气信息
    
    Args:
        location: 地点名称（如：长沙市岳麓区）
    
    Returns:
        dict: 天气信息
    """
    try:
        if not location or not location.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_location",
                    "message": "地点不能为空"
                }
            )
        
        weather_info = crawl_weather_from_website(location.strip())
        
        return {
            "success": True,
            "message": "天气信息获取成功",
            "data": weather_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "crawl_failed",
                "message": f"获取天气信息失败: {str(e)}"
            }
        )

class WeatherScheduleRequest(BaseModel):
    send_time: str
    is_daily: bool = False

def schedule_weather_task(send_time: str, is_daily: bool):
    """
    安排天气播报任务
    
    Args:
        send_time: 发送时间（格式：HH:MM）
        is_daily: 是否每日发送
    """
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    try:
        hour, minute = map(int, send_time.split(":"))
        
        if is_daily:
            trigger = CronTrigger(hour=hour, minute=minute)
            job_id = f"weather_custom_daily_{send_time}"
            scheduler.add_job(
                execute_weather_report,
                trigger=trigger,
                id=job_id,
                replace_existing=True
            )
            print(f"✅ 已添加每日天气播报任务: 时间 {send_time}")
        else:
            now = datetime.datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time <= now:
                target_time += datetime.timedelta(days=1)
            
            trigger = DateTrigger(run_date=target_time)
            job_id = f"weather_custom_once_{send_time}_{target_time.strftime('%Y%m%d')}"
            scheduler.add_job(
                execute_weather_report,
                trigger=trigger,
                id=job_id,
                replace_existing=True
            )
            print(f"✅ 已添加单次天气播报任务: 时间 {target_time}")
        
        return True, job_id
        
    except Exception as e:
        print(f"安排天气播报任务时发生错误: {e}")
        return False, str(e)

"""
安排天气播报任务
{
  "send_time": "13:50",    // 发送时间（格式：HH:MM）
  "is_daily": false        // 是否每日发送（默认 false，只发送一次）
}
"""
@router.post("/weather/schedule", summary="安排天气播报任务")
def schedule_weather_report(request: WeatherScheduleRequest):
    """
    安排天气播报任务
    
    用户只需要传入触发时间，系统就会在指定时间查询长沙市岳麓区的天气信息，
    然后把信息发送到企业微信群聊。
    
    Args:
        request: 天气播报请求
            - send_time: 发送时间（格式：HH:MM）
            - is_daily: 是否每日发送（默认 false）
    
    Returns:
        dict: 安排结果
    """
    try:
        if not request.send_time or len(request.send_time.split(":")) != 2:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "invalid_time",
                    "message": "发送时间格式错误，应为 HH:MM（如：13:50）"
                }
            )
        
        success, result = schedule_weather_task(
            request.send_time.strip(),
            request.is_daily
        )
        
        if success:
            return {
                "success": True,
                "message": "天气播报任务已安排" if not request.is_daily else "每日天气播报任务已安排",
                "data": {
                    "send_time": request.send_time,
                    "is_daily": request.is_daily,
                    "job_id": result,
                    "location": "长沙市岳麓区",
                    "description": f"将在{request.send_time}查询长沙市岳麓区的天气信息并发送到群聊"
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "schedule_failed",
                    "message": f"安排天气播报任务失败: {result}"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "server_error",
                "message": f"服务器错误: {str(e)}"
            }
        )

init_weather_database()
init_weather_scheduler()
