#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_robot import update_weather_config, get_weather_config

print('更新天气播报配置...')
print('-' * 50)

success = update_weather_config(
    city='长沙',
    district='岳麓区',
    send_time='13:50',
    enabled=True
)

if success:
    print('✅ 配置更新成功！')
    
    print('\n获取更新后的配置...')
    config = get_weather_config()
    if config:
        print(f'  城市: {config["city"]}')
        print(f'  区县: {config["district"]}')
        print(f'  发送时间: {config["send_time"]}')
        print(f'  启用状态: {config["enabled"]}')
    else:
        print('❌ 无法获取配置')
else:
    print('❌ 配置更新失败！')
