#!/usr/bin/env python3
import sys
import os
import requests
import json

BASE_URL = "http://localhost:8000"

def test_wechat_robot():
    print("=" * 80)
    print("测试企业微信群机器人接口")
    print("=" * 80)
    
    print(f"\n{'='*80}")
    print(f"测试1: 立即发送消息")
    print(f"{'='*80}")
    
    test_content = "测试消息：这是一条从API发送的测试消息，时间：" + str(__import__('datetime').datetime.now())
    
    try:
        response = requests.post(
            f"{BASE_URL}/wechat/send-now",
            params={"content": test_content},
            timeout=10
        )
        
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("success"):
            print(f"✅ 立即发送消息成功！")
        else:
            print(f"❌ 立即发送消息失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
        print(f"请确保FastAPI服务器正在运行：python3 main.py")
    
    print(f"\n{'='*80}")
    print(f"测试2: 创建每日定时消息")
    print(f"{'='*80}")
    
    try:
        test_data = {
            "is_daily": True,
            "send_time": "09:00",
            "content": "每日定时测试消息：早上好！现在是早上9点。"
        }
        
        response = requests.post(
            f"{BASE_URL}/wechat/send",
            json=test_data,
            timeout=10
        )
        
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("success"):
            print(f"✅ 创建每日定时消息成功！")
            daily_message_id = result.get("data", {}).get("id")
            print(f"  消息ID: {daily_message_id}")
        else:
            print(f"❌ 创建每日定时消息失败: {result.get('message', '未知错误')}")
            daily_message_id = None
            
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
        print(f"请确保FastAPI服务器正在运行：python3 main.py")
        daily_message_id = None
    
    print(f"\n{'='*80}")
    print(f"测试3: 创建单次定时消息")
    print(f"{'='*80}")
    
    try:
        import datetime
        now = datetime.datetime.now()
        next_minute = (now + datetime.timedelta(minutes=1)).strftime("%H:%M")
        
        test_data = {
            "is_daily": False,
            "send_time": next_minute,
            "content": f"单次定时测试消息：这是在 {next_minute} 发送的测试消息。"
        }
        
        response = requests.post(
            f"{BASE_URL}/wechat/send",
            json=test_data,
            timeout=10
        )
        
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("success"):
            print(f"✅ 创建单次定时消息成功！")
            print(f"  发送时间: {next_minute}")
            print(f"  请等待1分钟后查看企业微信是否收到消息")
        else:
            print(f"❌ 创建单次定时消息失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
        print(f"请确保FastAPI服务器正在运行：python3 main.py")
    
    print(f"\n{'='*80}")
    print(f"测试4: 获取消息列表")
    print(f"{'='*80}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/wechat/messages",
            timeout=10
        )
        
        result = response.json()
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        if result.get("success"):
            print(f"✅ 获取消息列表成功！")
            print(f"  总消息数: {result.get('total', 0)}")
        else:
            print(f"❌ 获取消息列表失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 发送请求失败: {e}")
        print(f"请确保FastAPI服务器正在运行：python3 main.py")
    
    print(f"\n{'='*80}")
    print(f"测试完成！")
    print(f"{'='*80}")
    
    print(f"\n使用说明：")
    print(f"1. 确保FastAPI服务器正在运行：python3 main.py")
    print(f"2. 立即发送消息：POST /wechat/send-now?content=消息内容")
    print(f"3. 每日定时发送：POST /wechat/send")
    print(f"   参数：")
    print(f"     - is_daily: true（每日定时）或 false（单次定时）")
    print(f"     - send_time: 发送时间，格式 HH:MM（例如：09:00）")
    print(f"     - content: 发送内容")
    print(f"4. 获取消息列表：GET /wechat/messages")
    print(f"5. 获取单个消息：GET /wechat/messages/{{id}}")
    print(f"6. 取消消息：DELETE /wechat/messages/{{id}}")

if __name__ == "__main__":
    test_wechat_robot()
