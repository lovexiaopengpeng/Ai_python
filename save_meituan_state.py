import asyncio
from playwright.async_api import async_playwright
import json
import os

STATE_FILE = os.path.join(os.path.dirname(__file__), "meituan_state.json")

async def save_login_state():
    """
    打开可见浏览器，让用户手动登录美团外卖，然后保存登录状态
    """
    print("=" * 70)
    print("美团外卖登录状态保存工具")
    print("=" * 70)
    
    print("""
使用说明:
1. 脚本会打开一个可见的浏览器窗口
2. 请在浏览器中手动登录美团外卖（如果还没登录）
3. 确保能看到"我的"页面显示您的用户名
4. 回到终端，按回车键保存登录状态

注意:
- 登录过程中可能需要验证码，请手动完成
- 请确保完全登录成功后再按回车
- 登录状态会保存到: meituan_state.json
""")
    
    async with async_playwright() as p:
        print("\n正在启动浏览器...")
        
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-web-security'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 414, 'height': 896},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
            geolocation={'latitude': 28.2282, 'longitude': 112.9388},
            permissions=['geolocation']
        )
        
        page = await context.new_page()
        
        print("\n正在打开美团外卖页面...")
        await page.goto("https://h5.waimai.meituan.com/", wait_until="domcontentloaded", timeout=30000)
        
        print(f"\n浏览器已打开！")
        print(f"当前页面: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        print("""
========================================
请在浏览器中完成以下操作:
1. 如果看到登录页面，请登录您的美团账号
2. 登录成功后，确保能看到"我的"页面
3. 可以尝试设置收货地址为: 长沙市岳麓区5G加速港
4. 确认一切正常后，回到终端按回车
========================================
""")
        
        try:
            await asyncio.sleep(2)
        except:
            pass
        
        print("\n请在浏览器中完成登录，完成后按回车键保存状态...")
        input()
        
        print("\n正在保存登录状态...")
        
        try:
            state = await context.storage_state()
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"✅ 登录状态已保存到: {STATE_FILE}")
            
            cookies = state.get('cookies', [])
            origins = state.get('origins', [])
            
            print(f"\n保存的信息:")
            print(f"  - Cookie数量: {len(cookies)}")
            print(f"  - localStorage/sessionStorage 数量: {len(origins)}")
            
            if cookies:
                print(f"\nCookie列表 (前10个):")
                for i, cookie in enumerate(cookies[:10]):
                    print(f"  [{i+1}] {cookie.get('name', 'unknown')} = {cookie.get('value', '')[:50]}...")
        except Exception as e:
            print(f"❌ 保存状态出错: {e}")
        
        print("\n正在关闭浏览器...")
        await browser.close()
        
        print("""
========================================
完成！
现在您可以测试爬虫了，爬虫会自动加载保存的登录状态。
========================================
""")

if __name__ == "__main__":
    asyncio.run(save_login_state())
