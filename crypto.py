from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import requests
import datetime
import sqlite3
import os
import json
import asyncio
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import Stealth
    PLAYWRIGHT_STEALTH_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_STEALTH_AVAILABLE = False

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), "user_database.db")
    return sqlite3.connect(db_path)

DB_TYPE = "sqlite"

def db_execute(cursor, query, params=()):
    query = query.replace("%s", "?")
    cursor.execute(query, params)

STATE_FILE = os.path.join(os.path.dirname(__file__), "meituan_state.json")

def has_saved_state():
    return os.path.exists(STATE_FILE)

def load_saved_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载保存的状态失败: {e}")
    return None

router = APIRouter()

class FoodDeliveryRequest(BaseModel):
    location: str = "长沙市岳麓区5G加速港"
    keyword: str = None
    min_rating: float = 0
    min_sales: int = 0
    max_delivery_fee: float = 999
    limit: int = 50

async def fetch_meituan_waimai_shops(location: str = "长沙市岳麓区5G加速港", 
                                       keyword: str = None,
                                       min_rating: float = 0,
                                       min_sales: int = 0,
                                       max_delivery_fee: float = 999,
                                       limit: int = 50):
    """
    使用Playwright获取美团外卖商家数据
    
    Args:
        location: 地址
        keyword: 搜索关键词
        min_rating: 最低评分
        min_sales: 最低月售
        max_delivery_fee: 最高配送费
        limit: 返回数量限制
    
    Returns:
        list: 商家列表
    """
    if not PLAYWRIGHT_AVAILABLE:
        raise Exception("Playwright未安装")
    
    saved_state = load_saved_state()
    
    if not saved_state:
        raise Exception("未找到保存的登录状态，请先登录")
    
    print(f"开始爬取美团外卖商家数据...")
    print(f"地址: {location}")
    print(f"使用保存的登录状态: {STATE_FILE}")
    
    shops = []
    
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
        
        async def handle_response(response):
            nonlocal shops
            try:
                url = response.url
                if 'i.waimai.meituan.com' in url and 'channel/shopList' in url:
                    status = response.status
                    body = await response.text()
                    
                    if status == 200:
                        try:
                            json_data = json.loads(body)
                            
                            if 'data' in json_data and isinstance(json_data['data'], str):
                                inner_data = json.loads(json_data['data'])
                                
                                if isinstance(inner_data, dict) and 'module_list' in inner_data:
                                    for module in inner_data['module_list']:
                                        if isinstance(module, dict) and 'module_list' in module:
                                            for sub_module in module['module_list']:
                                                if isinstance(sub_module, dict) and 'string_data' in sub_module and sub_module['string_data']:
                                                    try:
                                                        shop_data = json.loads(sub_module['string_data'])
                                                        if 'poi_name' in shop_data:
                                                            shops.append(shop_data)
                                                    except:
                                                        pass
                        except:
                            pass
            except:
                pass
        
        page.on('response', handle_response)
        
        print(f"访问美团外卖页面...")
        await page.goto("https://h5.waimai.meituan.com/", wait_until="networkidle", timeout=60000)
        await asyncio.sleep(10)
        
        print(f"点击美食分类...")
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
                print(f"等待商家数据加载...")
                for i in range(30):
                    await asyncio.sleep(1)
                    if len(shops) >= limit:
                        break
        except Exception as e:
            print(f"点击美食分类失败: {e}")
        
        if keyword:
            print(f"搜索关键词: {keyword}")
            try:
                search_input = await page.query_selector("input[placeholder*='搜索'], input[class*='search']")
                if search_input:
                    await search_input.click()
                    await asyncio.sleep(1)
                    await search_input.fill(keyword)
                    await asyncio.sleep(2)
                    await search_input.press('Enter')
                    await asyncio.sleep(10)
                    
                    for i in range(20):
                        await asyncio.sleep(1)
                        if len(shops) >= limit:
                            break
            except Exception as e:
                print(f"搜索失败: {e}")
        
        print(f"滚动页面加载更多数据...")
        for i in range(5):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(2)
            if len(shops) >= limit:
                break
        
        await asyncio.sleep(10)
        
        await browser.close()
    
    print(f"总共获取到 {len(shops)} 个商家")
    
    filtered_shops = []
    for shop in shops:
        if not isinstance(shop, dict):
            continue
        
        rating = 0
        if 'wm_poi_score' in shop:
            try:
                rating = float(shop['wm_poi_score'])
            except:
                pass
        
        sales = 0
        if 'month_sales_tip' in shop:
            try:
                sales_text = str(shop['month_sales_tip'])
                if '月售' in sales_text:
                    sales_num = sales_text.replace('月售', '').replace('+', '').replace('万', '0000')
                    sales = int(sales_num)
            except:
                pass
        
        delivery_fee = 999
        if 'shipping_fee_tip' in shop:
            try:
                fee_text = str(shop['shipping_fee_tip'])
                if '¥' in fee_text:
                    fee_num = fee_text.split('¥')[-1].strip()
                    delivery_fee = float(fee_num)
            except:
                pass
        
        if rating >= min_rating and sales >= min_sales and delivery_fee <= max_delivery_fee:
            filtered_shops.append({
                'id': shop.get('wm_poi_id', ''),
                'name': shop.get('poi_name', ''),
                'rating': rating,
                'sales': sales,
                'sales_text': shop.get('month_sales_tip', ''),
                'delivery_fee': delivery_fee,
                'delivery_fee_text': shop.get('shipping_fee_tip', ''),
                'avg_price': shop.get('avg_price_tip', ''),
                'delivery_time': shop.get('delivery_time_tip', ''),
                'distance': shop.get('distance', ''),
                'min_price': shop.get('min_price_tip', ''),
                'image': shop.get('poi_pic', ''),
                'address': location
            })
    
    filtered_shops = filtered_shops[:limit]
    print(f"筛选后返回 {len(filtered_shops)} 个商家")
    
    return filtered_shops

@router.get("/food-delivery/meituan/homepage")
async def get_meituan_homepage(location: str = "长沙市岳麓区5G加速港"):
    """
    获取美团外卖首页数据（商家列表）
    
    Args:
        location: 地址，默认为"长沙市岳麓区5G加速港"
    
    Returns:
        dict: 首页数据
    """
    try:
        shops = await fetch_meituan_waimai_shops(location=location, limit=50)
        
        categories = []
        category_names = ["美食", "甜点饮品", "超市便利", "蔬菜水果", "鲜花蛋糕", "夜宵", "正餐优选", "汉堡披萨"]
        for name in category_names:
            categories.append({
                'id': name,
                'name': name,
                'icon': '',
                'url': ''
            })
        
        banners = []
        
        return {
            'success': True,
            'data': {
                'shops': shops,
                'categories': categories,
                'banners': banners,
                'location': location,
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }
    except Exception as e:
        print(f"获取美团外卖首页数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'data': {
                'shops': [],
                'categories': [],
                'banners': [],
                'location': location,
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }

@router.get("/food-delivery/meituan/search")
async def search_meituan(
    location: str = "长沙市岳麓区5G加速港",
    keyword: str = None,
    min_rating: float = 0,
    min_sales: int = 0,
    max_delivery_fee: float = 999,
    limit: int = 50
):
    """
    搜索美团外卖商家
    
    Args:
        location: 地址
        keyword: 搜索关键词
        min_rating: 最低评分
        min_sales: 最低月售
        max_delivery_fee: 最高配送费
        limit: 返回数量限制
    
    Returns:
        dict: 搜索结果
    """
    try:
        shops = await fetch_meituan_waimai_shops(
            location=location,
            keyword=keyword,
            min_rating=min_rating,
            min_sales=min_sales,
            max_delivery_fee=max_delivery_fee,
            limit=limit
        )
        
        return {
            'success': True,
            'data': {
                'shops': shops,
                'total': len(shops),
                'keyword': keyword,
                'location': location,
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }
    except Exception as e:
        print(f"搜索美团外卖商家失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'data': {
                'shops': [],
                'total': 0,
                'keyword': keyword,
                'location': location,
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }

@router.post("/food-delivery/meituan/test")
async def test_meituan_crawler(request: FoodDeliveryRequest):
    """
    测试美团外卖爬虫
    
    Args:
        request: 爬取请求参数
    
    Returns:
        dict: 测试结果
    """
    try:
        shops = await fetch_meituan_waimai_shops(
            location=request.location,
            keyword=request.keyword,
            min_rating=request.min_rating,
            min_sales=request.min_sales,
            max_delivery_fee=request.max_delivery_fee,
            limit=request.limit
        )
        
        return {
            'success': True,
            'data': {
                'shops': shops,
                'total': len(shops),
                'request': request.dict(),
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }
    except Exception as e:
        print(f"测试美团外卖爬虫失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'data': {
                'shops': [],
                'total': 0,
                'request': request.dict(),
                'platform': 'meituan',
                'timestamp': datetime.datetime.now().isoformat()
            }
        }
