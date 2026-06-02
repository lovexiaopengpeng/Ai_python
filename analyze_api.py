#!/usr/bin/env python3
import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STATE_FILE = os.path.join(os.path.dirname(__file__), "meituan_state.json")

async def analyze_api_structure():
    print("=" * 70)
    print("分析商家API数据结构")
    print("=" * 70)
    
    if not os.path.exists(STATE_FILE):
        print(f"\n❌ 未找到保存的状态文件: {STATE_FILE}")
        return
    
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        saved_state = json.load(f)
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True)
        
        context = await browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            permissions=['geolocation'],
            geolocation={'latitude': 28.157178, 'longitude': 112.952278},
            storage_state=saved_state
        )
        
        page = await context.new_page()
        
        webdriver_status = await page.evaluate("navigator.webdriver")
        print(f"\nnavigator.webdriver状态: {webdriver_status}")
        
        shop_api_data = None
        
        async def handle_response(response):
            nonlocal shop_api_data
            try:
                url = response.url
                if 'i.waimai.meituan.com' in url and 'channel/shopList' in url:
                    status = response.status
                    body = await response.text()
                    
                    if status == 200:
                        try:
                            json_data = json.loads(body)
                            shop_api_data = json_data
                            print(f"\n✅ 捕获到商家API!")
                            print(f"URL: {url[:80]}...")
                            print(f"状态码: {status}")
                        except Exception as e:
                            print(f"解析JSON失败: {e}")
            except:
                pass
        
        page.on('response', handle_response)
        
        print(f"\n访问美团外卖页面...")
        await page.goto("https://h5.waimai.meituan.com/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(10)
        
        print(f"\n尝试点击美食分类...")
        try:
            clicked = await page.evaluate("""() => {
                const elements = document.querySelectorAll('div, a, span, button');
                for (const el of elements) {
                    const text = (el.innerText || '').trim();
                    if (text === '美食' || text === '美食推荐') {
                        el.click();
                        return true;
                    }
                }
                return false;
            }""")
            
            if clicked:
                print(f"  点击成功，等待15秒...")
                for i in range(15):
                    await asyncio.sleep(2)
                    if shop_api_data:
                        break
        except Exception as e:
            print(f"  点击失败: {e}")
        
        if shop_api_data:
            print(f"\n" + "=" * 70)
            print("分析API数据结构")
            print("=" * 70)
            
            print(f"\n顶层键: {list(shop_api_data.keys())}")
            
            if 'data' in shop_api_data:
                data_str = shop_api_data['data']
                print(f"\ndata是字符串，长度: {len(data_str)}")
                
                try:
                    inner_data = json.loads(data_str)
                    print(f"\n解析后的data键: {list(inner_data.keys()) if isinstance(inner_data, dict) else '不是字典'}")
                    
                    if isinstance(inner_data, dict):
                        if 'module_list' in inner_data:
                            print(f"\nmodule_list数量: {len(inner_data['module_list'])}")
                            
                            for i, module in enumerate(inner_data['module_list']):
                                print(f"\n模块 {i+1}:")
                                if isinstance(module, dict):
                                    print(f"  键: {list(module.keys())}")
                                    
                                    if 'module_list' in module:
                                        print(f"  子模块数量: {len(module['module_list'])}")
                                        
                                        for j, sub_module in enumerate(module['module_list']):
                                            print(f"\n  子模块 {j+1}:")
                                            if isinstance(sub_module, dict):
                                                print(f"    键: {list(sub_module.keys())}")
                                                
                                                if 'string_data' in sub_module and sub_module['string_data']:
                                                    try:
                                                        string_data = json.loads(sub_module['string_data'])
                                                        print(f"    string_data键: {list(string_data.keys()) if isinstance(string_data, dict) else '不是字典'}")
                                                        
                                                        if isinstance(string_data, dict):
                                                            for key in ['poi_list', 'shop_list', 'pois', 'shops', 'items']:
                                                                if key in string_data:
                                                                    print(f"    ✅ 找到{key}! 数量: {len(string_data[key])}")
                                                                    
                                                                    if string_data[key]:
                                                                        print(f"\n    第一个{key}示例:")
                                                                        first_item = string_data[key][0]
                                                                        if isinstance(first_item, dict):
                                                                            for k, v in first_item.items():
                                                                                if len(str(v)) > 100:
                                                                                    print(f"      {k}: {str(v)[:100]}...")
                                                                                else:
                                                                                    print(f"      {k}: {v}")
                                                    except Exception as e:
                                                        print(f"    解析string_data失败: {e}")
                                                        print(f"    string_data前500字符: {sub_module['string_data'][:500]}")
                except Exception as e:
                    print(f"\n解析data失败: {e}")
                    print(f"data前1000字符: {data_str[:1000]}")
        else:
            print(f"\n❌ 未捕获到商家API数据")
        
        await browser.close()
    
    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(analyze_api_structure())
