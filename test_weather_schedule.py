#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wechat_robot import schedule_weather_task, execute_weather_report

print('测试新的天气播报接口...')
print('-' * 50)

print('测试 1: 单次天气播报任务（14:00）')
success, result = schedule_weather_task('14:00', is_daily=False)
if success:
    print(f'  ✅ 成功安排单次天气播报任务')
    print(f'  Job ID: {result}')
else:
    print(f'  ❌ 安排失败: {result}')

print('-' * 50)

print('测试 2: 每日天气播报任务（13:50）')
success, result = schedule_weather_task('13:50', is_daily=True)
if success:
    print(f'  ✅ 成功安排每日天气播报任务')
    print(f'  Job ID: {result}')
else:
    print(f'  ❌ 安排失败: {result}')

print('-' * 50)

print('测试 3: 立即执行天气播报（验证功能）')
execute_weather_report()

print('-' * 50)
print('测试完成！')
