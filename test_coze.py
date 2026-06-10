import requests
import json

token = 'pat_vcDlPW4d6HgpvRL890LQEhMwkaNCeq4aOICrSozLJfoIDKTpemqgq3KpLawTOAHg'
bot_id = '7649684924001648694'
user_id = '123456789'

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# 1. 创建对话
print('1. 创建对话...')
chat_response = requests.post(
    'https://api.coze.cn/v3/chat',
    headers=headers,
    json={
        'bot_id': bot_id,
        'user_id': user_id,
        'stream': False,
        'additional_messages': [{
            'content_type': 'text',
            'role': 'user',
            'type': 'question',
            'content': '你好'
        }]
    }
)
chat_result = chat_response.json()
print(f'创建对话结果：{json.dumps(chat_result, ensure_ascii=False, indent=2)}')

if chat_result.get('code') == 0:
    conversation_id = chat_result['data']['conversation_id']
    chat_id = chat_result['data']['id']
    
    print(f'\n2. 尝试获取消息...')
    print(f'会话 ID: {conversation_id}')
    print(f'聊天 ID: {chat_id}')
    
    # 2. 等待 2 秒让机器人处理
    import time
    time.sleep(2)
    
    # 3. 尝试不同的 API 端点
    endpoints = [
        {
            'method': 'GET',
            'url': f'https://api.coze.cn/v3/chat/message?conversation_id={conversation_id}&chat_id={chat_id}'
        },
        {
            'method': 'GET',
            'url': f'https://api.coze.cn/v3/message/list?conversation_id={conversation_id}&chat_id={chat_id}'
        },
        {
            'method': 'POST',
            'url': 'https://api.coze.cn/v3/chat/message/retrieve',
            'data': {
                'conversation_id': conversation_id,
                'chat_id': chat_id
            }
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n尝试：{endpoint['method']} {endpoint['url']}")
        try:
            if endpoint['method'] == 'GET':
                response = requests.get(endpoint['url'], headers=headers)
            else:
                response = requests.post(endpoint['url'], headers=headers, json=endpoint.get('data', {}))
            
            print(f'状态码：{response.status_code}')
            try:
                result = response.json()
                print(f'响应：{json.dumps(result, ensure_ascii=False, indent=2)[:500]}')
            except:
                print(f'响应文本：{response.text[:500]}')
        except Exception as e:
            print(f'错误：{e}')
