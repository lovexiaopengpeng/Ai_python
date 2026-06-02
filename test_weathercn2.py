#!/usr/bin/env python3
import requests

print('测试中国天气网 API...')

citycode = '101250101'

try:
    response = requests.get(
        f'http://www.weather.com.cn/data/cityinfo/{citycode}.html',
        timeout=10
    )
    
    print(f'状态码: {response.status_code}')
    print(f'内容类型: {response.headers.get("Content-Type")}')
    print(f'\n原始内容: {response.content}')
    print(f'\n文本内容: {response.text}')
            
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
