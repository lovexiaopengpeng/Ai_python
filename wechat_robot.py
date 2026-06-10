import array

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
import requests
import datetime
import os
import json
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pymysql
from requests.api import request

router = APIRouter()

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=4ef6e7f3-b7d5-437f-940c-213fd6733be9"

DEFAULT_MYSQL_URL = "mysql://user_db:user_db_mm@127.0.0.1:3306/user_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_MYSQL_URL)

DB_TYPE = "mysql"

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
    # 解析 MySQL URL，格式：mysql://user:password@host:port/dbname
    from urllib.parse import urlparse
    url = urlparse(DATABASE_URL)
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port or 3306
    dbname = url.path[1:]  # 去掉开头的/
    
    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=dbname,
        charset="utf8mb4"
    )

def db_execute(cursor, query, params=None):
    """
    执行数据库查询
    
    Args:
        cursor: 数据库游标
        query: SQL 查询语句，使用 %s 作为占位符
        params: 参数元组或列表
    """
    if params is None:
        cursor.execute(query)
    else:
        # 确保 params 是元组或列表
        if not isinstance(params, (tuple, list)):
            params = (params,)
        cursor.execute(query, params)

class UserInfo(BaseModel):
    userid: str

@router.post("/user_info", summary="查询用户信息")
def get_user_info(user_info: UserInfo) -> dict:
    """
    根据 userid 查询用户信息
    
    Args:
        user_info: 用户 ID 请求体
    
    Returns:
        dict: 用户信息
    """
    userDic = {}
    
    try:
        # 连接数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询用户数据
        db_execute(
            cursor,
            "SELECT * FROM users WHERE user_id = %s",
            (user_info.userid,)
        )
        
        # 获取结果
        result = cursor.fetchone()
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        if result:
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            # 转换为字典
            userDic = dict(zip(columns, result))
            userDic["success"] = True
            print(f"[DEBUG] 查询到用户数据：{userDic}")
        else:
            userDic = {
                "userid": user_info.userid,
                "username": None,
                "success": False,
                "error": "用户不存在"
            }
            print(f"[DEBUG] 用户不存在：{user_info.userid}")
            
    except Exception as e:
        print(f"[ERROR] 查询数据库失败：{e}")
        userDic = {
            "userid": user_info.userid,
            "success": False,
            "error": str(e)
        }
    
    return userDic
    


def send_wechat_message(content: str, msg_type: str = "text", payload: dict = None) -> dict:
    """
    发送企业微信消息
    
    Args:
        content: 消息内容（text/markdown类型使用）
        msg_type: 消息类型：text、markdown、image、news
        payload: 自定义消息体（用于发送复杂消息类型）
    
    Returns:
        dict: 发送结果
    """
    try:
        if payload:
            final_payload = payload
        else:
            if msg_type == "text":
                final_payload = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    }
                }
            elif msg_type == "markdown":
                final_payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": content
                    }
                }
            elif msg_type == "image":
                final_payload = {
                    "msgtype": "image",
                    "image": {
                        "base64": "",
                        "md5": ""
                    }
                }
                if content:
                    try:
                        import base64
                        import hashlib
                        if content.startswith("http"):
                            response = requests.get(content, timeout=10)
                            image_data = response.content
                        else:
                            with open(content, "rb") as f:
                                image_data = f.read()
                        final_payload["image"]["base64"] = base64.b64encode(image_data).decode("utf-8")
                        final_payload["image"]["md5"] = hashlib.md5(image_data).hexdigest()
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"处理图片失败: {str(e)}"
                        }
            elif msg_type == "news":
                final_payload = {
                    "msgtype": "news",
                    "news": {
                        "articles": []
                    }
                }
            else:
                final_payload = {
                    "msgtype": "text",
                    "text": {
                        "content": content
                    }
                }
        
        response = requests.post(
            WEBHOOK_URL,
            json=final_payload,
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
            "SELECT id, is_daily, send_time, content, status FROM wechat_messages WHERE id = %s",
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
                "UPDATE wechat_messages SET status = 'sent', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (message_id,)
            )
            print(f"消息 {message_id} 发送成功")
        else:
            db_execute(
                cursor,
                "UPDATE wechat_messages SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
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
            timezone="Asia/Shanghai"
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
            trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
            scheduler.add_job(
                execute_scheduled_message,
                trigger=trigger,
                id=f"daily_{message_id}",
                args=[message_id],
                replace_existing=True
            )
            print(f"✅ 已添加每日定时任务: 消息 {message_id}, 时间 {send_time} (北京时间)")
        else:
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time <= now:
                target_time += datetime.timedelta(days=1)
            
            trigger = DateTrigger(run_date=target_time, timezone="Asia/Shanghai")
            scheduler.add_job(
                execute_scheduled_message,
                trigger=trigger,
                id=f"once_{message_id}",
                args=[message_id],
                replace_existing=True
            )
            print(f"✅ 已添加单次定时任务: 消息 {message_id}, 时间 {target_time} (北京时间)")
            
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
                "INSERT INTO wechat_messages (is_daily, send_time, content, status) VALUES (%s, %s, %s, 'scheduled')",
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
                "SELECT id, is_daily, send_time, content, status, created_at, updated_at FROM wechat_messages WHERE status = %s ORDER BY created_at DESC",
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
            "SELECT id, is_daily, send_time, content, status, created_at, updated_at FROM wechat_messages WHERE id = %s",
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
            "SELECT id, is_daily, status FROM wechat_messages WHERE id = %s",
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
            "UPDATE wechat_messages SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
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

DASHSCOPE_API_KEY = "sk-26270c8bfdd74a59a59a3ccc4ff29429"
DASHSCOPE_APP_ID = "97488c47da5946c2b94c3a876b289a3d"

def crawl_weather_from_website(location: str) -> dict:
    """
    使用阿里云DashScope获取天气信息
    
    Args:
        location: 地点名称
    
    Returns:
        dict: 阿里云DashScope原始响应
    """
    print(f"[DEBUG] 使用DashScope获取天气: {location}")
    
    try:
        url = f"https://dashscope.aliyuncs.com/api/v1/apps/{DASHSCOPE_APP_ID}/completion"
        
        headers = {
            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": {
                "prompt": f"{location}天气"
            },
            "parameters": {}
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        print(f"[DEBUG] DashScope响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DEBUG] DashScope响应: {str(result)[:500]}...")
            
            return {
                "success": True,
                "location": location,
                "dashscope_response": result,
                "update_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            raise Exception(f"请求失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[DEBUG] DashScope获取天气失败: {e}")
        raise

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
                VALUES (%s, %s, %s, %s)
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
            SET city = %s, district = %s, send_time = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
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

def execute_weather_report(job_id: str = None):
    """
    执行天气播报任务
    
    Args:
        job_id: 任务 ID，如果为 None 则使用默认配置
    """
    print(f"[DEBUG] 开始执行天气播报任务... (job_id: {job_id})")
    
    try:
        # 如果指定了 job_id，从 weather_schedule_config 读取配置
        if job_id:
            config = get_weather_schedule_from_db(job_id)
            if config:
                location = config.get('location', '长沙市岳麓区')
                print(f"[DEBUG] 从 weather_schedule_config 读取配置：{location}")
            else:
                print(f"[DEBUG] 未找到任务配置 {job_id}，使用默认配置")
                location = "长沙市岳麓区"
        else:
            # 否则使用旧的 weather_config 表配置（向后兼容）
            config = get_weather_config()
            print(f"[DEBUG] 天气配置：{config}")
            
            if not config or not config.get("enabled"):
                print("[DEBUG] 天气播报功能未启用，跳过")
                return
            
            location = f"{config.get('city', '长沙')}{config.get('district', '岳麓区')}"
            print(f"[DEBUG] 获取 {location} 的天气信息...")
        
        weather_info = crawl_weather_from_website(location)
        
        print(f"[DEBUG] 天气信息: {weather_info}")
        
        if weather_info.get("success"):
            dashscope_response = weather_info.get("dashscope_response", {})
            if dashscope_response and dashscope_response.get("output") and dashscope_response["output"].get("text"):
                message = dashscope_response["output"]["text"]
                print(f"[DEBUG] 使用DashScope返回的完整文本")
            else:
                message = "🌤️ 【每日天气播报】🌤️\n\n"
                message += f"📅 日期：{datetime.datetime.now().strftime('%Y-%m-%d')}\n"
                message += f"📍 地点：{weather_info.get('location', '长沙市岳麓区')}\n\n"
                message += "祝您今天心情愉快！😊"
                print(f"[DEBUG] 使用默认消息")
            
            print(f"[DEBUG] 消息预览: {message[:150]}...")
            
            print(f"[DEBUG] 发送天气消息到企业微信群...")
            result = send_wechat_message(message)
            
            if result.get("success"):
                print("✅ [DEBUG] 天气消息发送成功")
            else:
                print(f"❌ [DEBUG] 天气消息发送失败: {result.get('error')}")
        else:
            print(f"❌ [DEBUG] 爬取天气信息失败")
            
    except Exception as e:
        print(f"❌ [DEBUG] 执行天气播报任务时发生错误: {e}")
        import traceback
        print(f"[DEBUG] 堆栈信息: {traceback.format_exc()}")

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
            
            trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
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
                    trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
                    scheduler.add_job(
                        execute_weather_report,
                        trigger=trigger,
                        id="weather_report_daily",
                        replace_existing=True
                    )
                    print(f"✅ 已更新每日天气播报任务: 时间 {request.send_time} (北京时间)")
            
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
    is_daily: bool

class WeatherQueryRequest(BaseModel):
    city: str = "长沙"
    district: str = "岳麓区"

def get_weather_schedule_from_db(job_id: str = None):
    """
    从数据库获取天气调度配置
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        if job_id:
            cursor.execute("SELECT * FROM weather_schedule_config WHERE job_id = %s", (job_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'job_id': row[1],
                    'send_time': row[2],
                    'is_daily': bool(row[3]),
                    'status': row[4],
                    'location': row[5],
                    'created_at': row[6],
                    'updated_at': row[7]
                }
            return None
        else:
            cursor.execute("SELECT * FROM weather_schedule_config WHERE status = 'active'")
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'job_id': row[1],
                'send_time': row[2],
                'is_daily': bool(row[3]),
                'status': row[4],
                'location': row[5],
                'created_at': row[6],
                'updated_at': row[7]
            } for row in rows]
    finally:
        conn.close()

def save_weather_schedule_to_db(job_id: str, send_time: str, is_daily: bool, location: str = "长沙市岳麓区"):
    """
    保存天气调度配置到数据库
    """
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO weather_schedule_config (job_id, send_time, is_daily, location)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                send_time = VALUES(send_time),
                is_daily = VALUES(is_daily),
                location = VALUES(location),
                updated_at = CURRENT_TIMESTAMP
        """, (job_id, send_time, is_daily, location))
        conn.commit()
        return True
    except Exception as e:
        print(f"保存天气调度配置失败：{e}")
        return False
    finally:
        conn.close()

def delete_weather_schedule_from_db(job_id: str):
    """
    从数据库删除天气调度配置
    """
    conn = get_db_connection()
    if not conn:
        print(f"❌ 删除失败：无法连接数据库")
        return False
    
    try:
        cursor = conn.cursor()
        print(f"[DEBUG] 准备删除任务：{job_id}")
        cursor.execute("DELETE FROM weather_schedule_config WHERE job_id = %s", (job_id,))
        conn.commit()
        affected_rows = cursor.rowcount
        print(f"[DEBUG] 删除任务 {job_id}，影响行数：{affected_rows}")
        return True
    except Exception as e:
        print(f"❌ 删除天气调度配置失败：{e}")
        return False
    finally:
        conn.close()

def restore_weather_schedule_from_db():
    """
    从数据库恢复天气调度任务
    """
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    configs = get_weather_schedule_from_db()
    if not configs:
        print("✅ 没有需要恢复的天气播报任务")
        return
    
    restored_count = 0
    for config in configs:
        try:
            send_time = config['send_time']
            is_daily = config['is_daily']
            job_id = config['job_id']
            
            hour, minute = map(int, send_time.split(":"))
            
            if is_daily:
                trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
                scheduler.add_job(
                    execute_weather_report,
                    trigger=trigger,
                    id=job_id,
                    replace_existing=True,
                    kwargs={'job_id': job_id}
                )
                print(f"✅ 已恢复每日天气播报任务：{job_id} (时间：{send_time})")
            else:
                now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
                target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if target_time <= now:
                    target_time += datetime.timedelta(days=1)
                
                trigger = DateTrigger(run_date=target_time, timezone="Asia/Shanghai")
                scheduler.add_job(
                    execute_weather_report,
                    trigger=trigger,
                    id=job_id,
                    replace_existing=True,
                    kwargs={'job_id': job_id}
                )
                print(f"✅ 已恢复单次天气播报任务：{job_id} (时间：{target_time})")
            
            restored_count += 1
        except Exception as e:
            print(f"恢复天气播报任务 {job_id} 失败：{e}")
    
    print(f"✅ 共恢复 {restored_count} 个天气播报任务")

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
            trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
            job_id = f"weather_custom_daily_{send_time}"
            scheduler.add_job(
                execute_weather_report,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                kwargs={'job_id': job_id}
            )
            print(f"✅ 已添加每日天气播报任务：时间 {send_time}")
        else:
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time <= now:
                target_time += datetime.timedelta(days=1)
            
            trigger = DateTrigger(run_date=target_time, timezone="Asia/Shanghai")
            job_id = f"weather_custom_once_{send_time}_{target_time.strftime('%Y%m%d')}"
            scheduler.add_job(
                execute_weather_report,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                kwargs={'job_id': job_id}
            )
            print(f"✅ 已添加单次天气播报任务：时间 {target_time}")
        
        # 保存到数据库
        save_weather_schedule_to_db(job_id, send_time, is_daily)
        print(f"✅ 天气播报任务已保存到数据库：{job_id}")
        
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

@router.post("/weather/query", summary="查询天气信息")
def query_weather(request: WeatherQueryRequest):
    """
    查询指定地区的天气信息
    
    Args:
        request: 查询请求
            - city: 城市名称（如：长沙、北京、上海）
            - district: 区县名称（如：岳麓区、朝阳区、浦东新区）
    
    Returns:
        dict: 天气信息查询结果
    """
    try:
        city = request.city
        district = request.district
        
        if not city or not city.strip():
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": "empty_city",
                    "message": "城市不能为空"
                }
            )
        
        location = f"{city.strip()}{district.strip() if district else ''}"
        print(f"[DEBUG] 查询天气: {location}")
        
        weather_info = crawl_weather_from_website(location)
        
        if weather_info.get("success"):
            dashscope_response = weather_info.get("dashscope_response", {})
            
            weather_text = None
            if dashscope_response and dashscope_response.get("output") and dashscope_response["output"].get("text"):
                weather_text = dashscope_response["output"]["text"]
            
            return {
                "success": True,
                "message": "天气信息查询成功",
                "data": {
                    "location": location,
                    "city": city.strip(),
                    "district": district.strip() if district else "",
                    "weather_text": weather_text,
                    "raw_response": dashscope_response,
                    "query_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "error": "query_failed",
                    "message": "获取天气信息失败"
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

@router.get("/weather/debug", summary="天气播报调试接口")
def debug_weather():
    """
    天气播报调试接口
    
    返回：
    - 调度器状态
    - 所有定时任务列表
    - 天气配置
    - 系统时间
    """
    try:
        jobs = []
        if scheduler is not None:
            for job in scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "trigger": str(job.trigger),
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                    "func": str(job.func)
                })
        
        config = get_weather_config()
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            "success": True,
            "data": {
                "scheduler_running": scheduler is not None and scheduler.running,
                "current_time": current_time,
                "timezone": "Asia/Shanghai",
                "weather_config": config,
                "jobs_count": len(jobs),
                "jobs": jobs
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/weather/jobs", summary="获取所有天气播报定时任务")
def get_all_weather_jobs():
    """
    获取所有天气播报定时任务
    
    Returns:
        dict: 任务列表
    """
    try:
        jobs = []
        if scheduler is not None:
            for job in scheduler.get_jobs():
                if "weather" in job.id:
                    jobs.append({
                        "id": job.id,
                        "type": "daily" if "daily" in job.id else "once",
                        "trigger": str(job.trigger),
                        "next_run_time": str(job.next_run_time) if job.next_run_time else None
                    })
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/weather/test", summary="测试天气播报功能")
def test_weather():
    """
    测试天气播报功能
    
    立即获取天气并发送到群聊
    """
    try:
        print("[DEBUG] === 开始测试天气播报 ===")
        execute_weather_report()
        print("[DEBUG] === 测试完成 ===")
        return {
            "success": True,
            "message": "测试完成，请查看日志",
            "note": "请检查企业微信群是否收到消息"
        }
    except Exception as e:
        print(f"[DEBUG] 测试失败: {e}")
        import traceback
        print(f"[DEBUG] 堆栈: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/weather/cancel-all", summary="取消所有天气播报定时任务")
def cancel_all_weather_jobs():
    """
    取消所有天气播报定时任务
    """
    try:
        removed_jobs = []
        
        if scheduler is not None:
            for job in scheduler.get_jobs():
                if "weather" in job.id:
                    try:
                        scheduler.remove_job(job.id)
                        removed_jobs.append(job.id)
                        print(f"✅ 已取消任务: {job.id}")
                    except Exception as e:
                        print(f"❌ 取消任务失败 {job.id}: {e}")
            
        # 删除 weather_schedule_config 表中的所有记录
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM weather_schedule_config")
        conn.commit()
        conn.close()
        print("✅ 已删除 weather_schedule_config 表中的所有记录")
        
        return {
            "success": True,
            "message": "已取消所有天气播报定时任务",
            "removed_count": len(removed_jobs),
            "removed_jobs": removed_jobs
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/weather/cancel/{job_id}", summary="取消指定的天气播报定时任务")
def cancel_weather_job(job_id: str):
    """
    取消指定的天气播报定时任务
    
    Args:
        job_id: 任务ID（如：weather_custom_daily_16:00、weather_report_daily）
    
    Returns:
        dict: 取消结果
    """
    try:
        if scheduler is None:
            return {
                "success": False,
                "error": "调度器未初始化"
            }
        
        # 尝试从调度器删除任务
        try:
            job = scheduler.get_job(job_id)
            if job:
                scheduler.remove_job(job_id)
                print(f"[DEBUG] 已从调度器删除任务：{job_id}")
            else:
                print(f"[DEBUG] 调度器中未找到任务：{job_id}，但仍会删除数据库记录")
        except Exception as e:
            print(f"[DEBUG] 从调度器删除任务失败：{e}")
        
        # 从数据库删除（无论如何都执行）
        delete_weather_schedule_from_db(job_id)
        
        print(f"✅ 已取消任务：{job_id}")
        
        return {
            "success": True,
            "message": f"任务 {job_id} 已取消"
        }
    except Exception as e:
        print(f"❌ 取消任务失败 {job_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============ 即时消息推送功能 ============

class InstantMessageRequest(BaseModel):
    """
    即时消息请求
    """
    content: str
    msg_type: str = "text"

@router.post("/message/send", summary="立即发送消息到群聊")
def send_instant_message(request: InstantMessageRequest):
    """
    立即发送一条消息推送到企业微信群聊
    
    Args:
        request: 消息请求
            - content: 消息内容
            - msg_type: 消息类型（text/markdown，默认 text）
    
    Returns:
        dict: 发送结果
    
    示例:
    ```json
    {
        "content": "你好，这是一条测试消息",
        "msg_type": "text"
    }
    ```
    """
    try:
        if not request.content or not request.content.strip():
            return {
                "success": False,
                "error": "消息内容不能为空"
            }
        
        result = send_wechat_message(
            content=request.content.strip(),
            msg_type=request.msg_type or "text"
        )
        
        if result.get("success"):
            print(f"✅ 即时消息发送成功：{request.content[:50]}...")
        else:
            print(f"❌ 即时消息发送失败：{result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ 发送即时消息时发生错误：{e}")
        return {
            "success": False,
            "error": str(e)
        }

# ============ 周报提醒功能 ============

def send_weekly_report_reminder():
    """
    发送周报提醒消息
    """
    try:
        content = "记得要写周报哦"
        
        print(f"[DEBUG] 开始发送周报提醒消息：{content}")
        
        result = send_wechat_message(content)
        
        if result.get("success"):
            print(f"✅ 周报提醒消息发送成功")
        else:
            print(f"❌ 周报提醒消息发送失败：{result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ 发送周报提醒消息时发生错误：{e}")
        return {
            "success": False,
            "error": str(e)
        }

def init_weekly_report_scheduler():
    """
    初始化周报提醒定时任务
    """
    global scheduler
    
    if scheduler is None:
        init_scheduler()
    
    try:
        # 检查是否已存在周报提醒任务
        existing_job = scheduler.get_job("weekly_report_reminder")
        if existing_job:
            print("周报提醒任务已存在，跳过初始化")
            return
        
        # 添加每周一 09:00 的定时任务
        trigger = CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Asia/Shanghai")
        scheduler.add_job(
            send_weekly_report_reminder,
            trigger=trigger,
            id="weekly_report_reminder",
            replace_existing=True
        )
        
        print("✅ 已添加周报提醒任务：每周一 09:00")
        
    except Exception as e:
        print(f"初始化周报提醒定时任务时发生错误：{e}")

@router.post("/weekly-report/schedule", summary="安排周报提醒定时任务")
def schedule_weekly_report():
    """
    安排周报提醒定时任务
    
    在每周一 09:00 发送"记得要写周报哦"到企业微信群聊
    
    Returns:
        dict: 安排结果
    """
    try:
        global scheduler
        
        if scheduler is None:
            init_scheduler()
        
        # 检查是否已存在
        existing_job = scheduler.get_job("weekly_report_reminder")
        if existing_job:
            return {
                "success": True,
                "message": "周报提醒任务已存在",
                "data": {
                    "job_id": "weekly_report_reminder",
                    "schedule": "每周一 09:00",
                    "content": "记得要写周报哦"
                }
            }
        
        # 添加定时任务
        trigger = CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Asia/Shanghai")
        scheduler.add_job(
            send_weekly_report_reminder,
            trigger=trigger,
            id="weekly_report_reminder",
            replace_existing=True
        )
        
        print("✅ 已添加周报提醒任务：每周一 09:00")
        
        return {
            "success": True,
            "message": "周报提醒任务已安排",
            "data": {
                "job_id": "weekly_report_reminder",
                "schedule": "每周一 09:00",
                "content": "记得要写周报哦"
            }
        }
        
    except Exception as e:
        print(f"安排周报提醒任务时发生错误：{e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/weekly-report/cancel", summary="取消周报提醒定时任务")
def cancel_weekly_report():
    """
    取消周报提醒定时任务
    
    Returns:
        dict: 取消结果
    """
    try:
        global scheduler
        
        if scheduler is None:
            return {
                "success": False,
                "error": "调度器未初始化"
            }
        
        # 尝试从调度器删除任务
        try:
            job = scheduler.get_job("weekly_report_reminder")
            if job:
                scheduler.remove_job("weekly_report_reminder")
                print(f"✅ 已取消周报提醒任务")
            else:
                print(f"⚠️ 周报提醒任务不存在")
        except Exception as e:
            print(f"从调度器删除任务失败：{e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        return {
            "success": True,
            "message": "周报提醒任务已取消"
        }
        
    except Exception as e:
        print(f"取消周报提醒任务时发生错误：{e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/weekly-report/status", summary="查询周报提醒任务状态")
def get_weekly_report_status():
    """
    查询周报提醒任务状态
    
    Returns:
        dict: 任务状态
    """
    try:
        global scheduler
        
        if scheduler is None:
            return {
                "success": False,
                "error": "调度器未初始化"
            }
        
        job = scheduler.get_job("weekly_report_reminder")
        
        if job:
            return {
                "success": True,
                "data": {
                    "enabled": True,
                    "job_id": "weekly_report_reminder",
                    "schedule": "每周一 09:00",
                    "content": "记得要写周报哦",
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "enabled": False,
                    "message": "周报提醒任务未安排"
                }
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/weekly-report/test", summary="测试周报提醒功能")
def test_weekly_report():
    """
    立即测试周报提醒功能
    
    Returns:
        dict: 测试结果
    """
    try:
        result = send_weekly_report_reminder()
        
        if result.get("success"):
            return {
                "success": True,
                "message": "测试消息已发送"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "发送失败")
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# 初始化周报提醒定时任务
init_weekly_report_scheduler()

# 原有的初始化代码
init_weather_database()
init_weather_scheduler()
restore_weather_schedule_from_db()
