#!/usr/bin/env python3
import asyncio
import json
import os
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

STATE_FILE = os.path.join(os.path.dirname(__file__), "meituan_state.json")

async def test_with_address_selection():
    print("=" * 70)
    print("测试当前登录状态 - 自动选择地址")
    print("=" * 70)
    
    if not os.path.exists(STATE_FILE):
        print(f"\n❌ 未找到保存的状态文件: {STATE_FILE}")
        return
    
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        saved_state = json.load(f)
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=False)
        
        context = await browser.new_context(
            viewport={'width': 375, 'height': 667},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            permissions=['geolocation'],
            geolocation={'latitude': 28.116918, 'longitude': 112.936868},
            storage_state=saved_state
        )
        
        page = await context.new_page()
        
        webdriver_status = await page.evaluate("navigator.webdriver")
        print(f"\nnavigator.webdriver状态: {webdriver_status}")
        
        api_data = {}
        async def handle_response(response):
            try:
                url = response.url
                if 'i.waimai.meituan.com' in url:
                    status = response.status
                    body = await response.text()
                    
                    api_data[url] = {
                        'status': status,
                        'body': body[:2000]
                    }
                    
                    if 'shopList' in url or 'poi' in url or 'shop' in url:
                        print(f"\n{'='*70}")
                        print(f"捕获商家API: {url[:80]}...")
                        print(f"状态码: {status}")
                        
                        if status == 200:
                            try:
                                json_data = json.loads(body)
                                print(f"✅ JSON解析成功!")
                                print(f"顶层键: {list(json_data.keys())}")
                                
                                if 'data' in json_data:
                                    if isinstance(json_data['data'], str):
                                        print(f"data是字符串，长度: {len(json_data['data'])}")
                                        if 'poi' in json_data['data'].lower() or 'shop' in json_data['data'].lower():
                                            print(f"✅ data包含商家数据!")
                                            inner_data = json.loads(json_data['data'])
                                            print(f"解析后的data键: {list(inner_data.keys()) if isinstance(inner_data, dict) else '不是字典'}")
                                    else:
                                        print(f"data键: {list(json_data['data'].keys()) if isinstance(json_data['data'], dict) else '不是字典'}")
                            except Exception as e:
                                print(f"JSON解析失败: {e}")
                                print(f"响应前1000字符: {body[:1000]}")
                        else:
                            print(f"响应前500字符: {body[:500]}")
            except:
                pass
        
        page.on('response', handle_response)
        
        print(f"\n访问美团外卖页面...")
        await page.goto("https://h5.waimai.meituan.com/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(10)
        
        page_text = await page.evaluate("""() => {
            return document.body.innerText || '';
        }""")
        
        print(f"\n初始页面状态:")
        print(f"  URL: {page.url}")
        print(f"  标题: {await page.title()}")
        print(f"  页面文本长度: {len(page_text)}")
        print(f"  包含'登录': {'登录' in page_text}")
        print(f"  包含'商家': {'商家' in page_text}")
        print(f"  包含'评分': {'评分' in page_text}")
        print(f"  包含'网络好像不太给力': {'网络好像不太给力' in page_text}")
        
        # 检查localStorage
        storage_info = await page.evaluate("""() => {
            const result = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                result[key] = localStorage.getItem(key);
            }
            return result;
        }""")
        
        print(f"\nlocalStorage关键信息:")
        key_items = ['pickedpoi', 'geopoi', 'deliverypoi', 'addstore']
        for key in key_items:
            if key in storage_info:
                print(f"  {key}: {storage_info[key][:200]}")
        
        # 尝试点击地址选择器
        print(f"\n点击地址选择器...")
        try:
            await page.evaluate("""() => {
                const selectors = ['.addr_W3eGpu', '.ellipsis_dSZz_q', '.upHeader_SFVuMM', '.homeHeader_cMSobe'];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }""")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"  出错: {e}")
        
        # 尝试选择地址
        print(f"\n选择地址...")
        try:
            selected = await page.evaluate("""() => {
                const keywords = ['湖南湘江新区大学生创新创业园', '大学生创新创业园', '5G加速港', '陈先生'];
                
                for (const keyword of keywords) {
                    const elements = document.querySelectorAll('[class*="deliveryPoiItem"], [class*="poiItem"], [class*="addressItem"], [class*="item"]');
                    
                    for (const el of elements) {
                        const text = (el.innerText || '').trim();
                        if (text.includes(keyword)) {
                            el.click();
                            return {
                                success: true,
                                keyword: keyword,
                                address: text
                            };
                        }
                    }
                }
                
                return { success: false };
            }""")
            
            print(f"选择结果: {selected}")
        except Exception as e:
            print(f"  出错: {e}")
        
        print(f"\n等待页面加载...")
        for i in range(15):
            await asyncio.sleep(2)
            
            page_text = await page.evaluate("""() => {
                return document.body.innerText || '';
            }""")
            
            print(f"\n第 {i+1} 次检查:")
            print(f"  页面文本长度: {len(page_text)}")
            print(f"  包含'评分': {'评分' in page_text}")
            print(f"  包含'月售': {'月售' in page_text}")
            print(f"  包含'配送': {'配送' in page_text}")
            print(f"  包含'网络好像不太给力': {'网络好像不太给力' in page_text}")
            
            if '评分' in page_text or '月售' in page_text:
                print(f"  ✅ 找到商家数据！")
                
                shops = await page.evaluate("""() => {
                    const results = [];
                    const allElements = document.querySelectorAll('div, a, section, li');
                    
                    allElements.forEach(el => {
                        const text = el.innerText;
                        if (!text) return;
                        
                        if (text.includes('评分') || text.includes('月售') || text.includes('配送')) {
                            const lines = text.trim().split('\\n');
                            if (lines.length >= 3) {
                                results.push(lines);
                            }
                        }
                    });
                    
                    return results;
                }""")
                
                if shops:
                    print(f"\n  找到 {len(shops)} 个商家片段:")
                    for j, shop in enumerate(shops[:5]):
                        print(f"\n  商家 {j+1}:")
                        for line in shop[:5]:
                            print(f"    {line}")
                
                break
            
            if '网络好像不太给力' in page_text or '重新加载' in page_text:
                print(f"  检测到网络错误，尝试点击重新加载...")
                try:
                    clicked = await page.evaluate("""() => {
                        const elements = document.querySelectorAll('div, a, button, span');
                        for (const el of elements) {
                            const text = (el.innerText || '').trim();
                            if (text === '重新加载' || text.includes('重新加载')) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }""")
                    if clicked:
                        print(f"  点击成功，等待3秒...")
                        await asyncio.sleep(3)
                except Exception as e:
                    print(f"  点击失败: {e}")
        
        print(f"\n等待90秒以便观察页面...")
        await asyncio.sleep(90)
        
        await browser.close()
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_with_address_selection())
