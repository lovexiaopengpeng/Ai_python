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

# 简化的数据库连接函数，避免复杂的导入
def get_db_connection():
    # 使用与 main.py 相同的数据库路径
    db_path = os.path.join(os.path.dirname(__file__), "user_database.db")
    return sqlite3.connect(db_path)

DB_TYPE = "sqlite"

def db_execute(cursor, query, params=()):
    # 对于 SQLite，将 %s 替换为 ?
    query = query.replace("%s", "?")
    cursor.execute(query, params)

STATE_FILE = os.path.join(os.path.dirname(__file__), "meituan_state.json")

def has_saved_state():
    """
    检查是否有保存的登录状态
    
    Returns:
        bool: 是否有保存的状态
    """
    return os.path.exists(STATE_FILE)

def load_saved_state():
    """
    加载保存的登录状态
    
    Returns:
        dict: storage_state 字典，如果没有保存则返回 None
    """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

router = APIRouter(prefix="/crypto_old", tags=["虚拟币大额交易"])

def fetch_from_binance_api():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        main_coins = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
                      "DOGEUSDT", "SHIBUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
                      "ADAUSDT", "MATICUSDT", "LTCUSDT", "TRXUSDT", "BCHUSDT"]
        
        trades = []
        for item in data:
            symbol = item.get("symbol", "")
            if symbol in main_coins:
                price = float(item.get("lastPrice", "0"))
                change = float(item.get("priceChangePercent", "0"))
                volume = float(item.get("volume", "0"))
                
                trades.append({
                    "symbol": f"{symbol[:-4]}/USDT",
                    "price": f"${price:,.2f}",
                    "change": f"{change:+.2f}%",
                    "volume": f"${volume:,.0f}",
                    "platform": "Binance",
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "type": "spot",
                    "url": f"https://www.binance.com/en/trade/{symbol[:-4]}_USDT"
                })
        return trades
    except Exception as e:
        print(f"Binance API error: {e}")
        return []

def fetch_from_coingecko_api():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 20,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        trades = []
        for item in data:
            symbol = item.get("symbol", "").upper()
            name = item.get("name", "")
            price = item.get("current_price", 0)
            change = item.get("price_change_percentage_24h", 0)
            volume = item.get("total_volume", 0)
            
            trades.append({
                "symbol": f"{symbol}/USD",
                "name": name,
                "price": f"${price:,.2f}",
                "change": f"{change:+.2f}%",
                "volume": f"${volume:,.0f}",
                "platform": "CoinGecko",
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "market",
                "url": item.get("url", "https://www.coingecko.com")
            })
        return trades
    except Exception as e:
        print(f"CoinGecko API error: {e}")
        return []

def fetch_from_cryptocompare_api():
    url = "https://min-api.cryptocompare.com/data/pricemultifull"
    fsyms = "BTC,ETH,BNB,SOL,XRP,DOGE,SHIB,AVAX,LINK,DOT,ADA,MATIC,LTC,TRX,BCH"
    params = {
        "fsyms": fsyms,
        "tsyms": "USD"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        trades = []
        for symbol, info in data.get("RAW", {}).items():
            usd_info = info.get("USD", {})
            price = usd_info.get("PRICE", 0)
            change = usd_info.get("CHANGEPCT24HOUR", 0)
            volume = usd_info.get("VOLUME24HOUR", 0)
            
            trades.append({
                "symbol": f"{symbol}/USD",
                "price": f"${price:,.2f}",
                "change": f"{change:+.2f}%",
                "volume": f"${volume:,.0f}",
                "platform": "CryptoCompare",
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "market",
                "url": f"https://www.cryptocompare.com/coins/{symbol.lower()}/overview"
            })
        return trades
    except Exception as e:
        print(f"CryptoCompare API error: {e}")
        return []

def fetch_from_coinmarketcap_api():
    url = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listings/latest"
    params = {
        "start": "1",
        "limit": "20",
        "convert": "USD"
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        trades = []
        for item in data.get("data", {}).get("cryptoCurrencyList", []):
            symbol = item.get("symbol", "")
            name = item.get("name", "")
            price = item.get("quotes", [{}])[0].get("price", 0)
            change = item.get("quotes", [{}])[0].get("percentChange24h", 0)
            volume = item.get("quotes", [{}])[0].get("volume24h", 0)
            
            trades.append({
                "symbol": f"{symbol}/USD",
                "name": name,
                "price": f"${price:,.2f}",
                "change": f"{change:+.2f}%",
                "volume": f"${volume:,.0f}",
                "platform": "CoinMarketCap",
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "market",
                "url": f"https://coinmarketcap.com/currencies/{name.lower().replace(' ', '-')}/"
            })
        return trades
    except Exception as e:
        print(f"CoinMarketCap API error: {e}")
        return []

def fetch_large_trades():
    all_trades = []
    seen_symbols = set()
    
    sources = [
        fetch_from_binance_api,
        fetch_from_coingecko_api,
        fetch_from_cryptocompare_api,
        fetch_from_coinmarketcap_api
    ]
    
    for fetch_func in sources:
        try:
            data = fetch_func()
            for item in data:
                key = f"{item['symbol']}-{item['platform']}"
                if key not in seen_symbols:
                    seen_symbols.add(key)
                    all_trades.append(item)
        except Exception as e:
            print(f"Error fetching from source: {e}")
            continue
    
    if not all_trades:
        raise Exception("所有数据源都无法获取数据")
    
    all_trades.sort(key=lambda x: x["time"], reverse=True)
    
    return all_trades[:50]

@router.get("/large-trades", summary="获取主流虚拟币大额买卖情况")
def get_crypto_large_trades(userid: str = Header(None)):
    if not userid:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "请求头中缺少 userid 参数"}
        )
    
    try:
        trades = fetch_large_trades()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"获取虚拟币数据失败: {str(e)}"}
        )
    
    return {
        "success": True,
        "count": len(trades),
        "userid": userid,
        "data": trades,
        "message": "获取虚拟币大额交易信息成功",
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def calculate_buy_signal(change_24h, change_7d, change_30d, volume_24h_usd, market_cap_usd, price_usd, rank):
    score = 0
    reasons = []
    
    change_24h = float(change_24h) if change_24h else 0
    change_7d = float(change_7d) if change_7d else 0
    change_30d = float(change_30d) if change_30d else 0
    price_usd = float(price_usd) if price_usd else 0
    rank = int(rank) if rank else 100
    
    if change_24h < -10:
        score += 45
        reasons.append("24小时大幅下跌超过10%，强烈买入信号")
    elif change_24h < -6:
        score += 28
        reasons.append("24小时跌幅超过6%")
    elif change_24h < -3:
        score += 14
        reasons.append("24小时小幅下跌")
    elif change_24h < 2:
        score += 6
        reasons.append("24小时价格稳定")
    elif change_24h > 12:
        score -= 30
        reasons.append("24小时涨幅过大，谨慎追高")
    elif change_24h > 6:
        score -= 15
        reasons.append("24小时涨幅较大")
    
    if change_7d < -18:
        score += 35
        reasons.append("7日大幅下跌超过18%")
    elif change_7d < -10:
        score += 22
        reasons.append("7日跌幅超过10%")
    elif change_7d < -4:
        score += 10
        reasons.append("7日小幅下跌")
    elif change_7d < 3:
        score += 4
        reasons.append("7日价格稳定")
    elif change_7d > 22:
        score -= 20
        reasons.append("7日涨幅过大")
    
    if change_30d < -25:
        score += 30
        reasons.append("30日大幅下跌超过25%")
    elif change_30d < -12:
        score += 18
        reasons.append("30日跌幅超过12%")
    elif change_30d < -4:
        score += 8
        reasons.append("30日小幅下跌")
    elif change_30d < 3:
        score += 3
        reasons.append("30日价格稳定")
    elif change_30d > 28:
        score -= 15
        reasons.append("30日涨幅较大")
    
    avg_change = (change_24h + change_7d + change_30d) / 3
    momentum_score = change_24h - change_7d / 7
    if momentum_score < -2:
        score += 12
        reasons.append("短期下跌加速，可能接近底部")
    elif momentum_score > 2:
        score -= 8
        reasons.append("短期上涨加速，可能过热")
    
    rsi_value = min(100, max(0, 50 - avg_change * 2))
    if rsi_value < 30:
        score += 18
        reasons.append("RSI低于30，超卖状态")
    elif rsi_value < 40:
        score += 8
        reasons.append("RSI偏低，可能处于低位")
    elif rsi_value > 70:
        score -= 15
        reasons.append("RSI高于70，超买状态")
    
    macd_signal = change_7d - change_30d / 4.28
    if macd_signal < -3:
        score += 15
        reasons.append("MACD指标显示买入信号")
    elif macd_signal > 5:
        score -= 10
        reasons.append("MACD指标显示卖出信号")
    
    if volume_24h_usd and market_cap_usd:
        volume_ratio = volume_24h_usd / max(market_cap_usd, 1)
        if volume_ratio > 0.1:
            score += 15
            reasons.append("成交量非常活跃")
        elif volume_ratio > 0.04:
            score += 8
            reasons.append("成交量活跃")
        elif volume_ratio < 0.006:
            score -= 8
            reasons.append("成交量低迷")
    
    if price_usd > 0:
        if price_usd < 0.5:
            score += 10
            reasons.append("价格较低，风险较小")
        elif price_usd < 5:
            score += 6
            reasons.append("价格适中")
        elif price_usd < 50:
            score += 3
            reasons.append("价格合理")
        elif price_usd > 10000:
            score -= 6
            reasons.append("价格较高，风险较大")
    
    volatility = abs(change_24h) + abs(change_7d) + abs(change_30d)
    if volatility < 8:
        score += 12
        reasons.append("波动性低，适合稳健投资")
    elif volatility < 15:
        score += 5
        reasons.append("波动性适中")
    elif volatility > 60:
        score -= 10
        reasons.append("波动性过高，风险较大")
    
    if rank <= 10:
        score += 8
        reasons.append("市值排名前10，稳定性高")
    elif rank <= 50:
        score += 4
        reasons.append("市值排名前50，相对稳定")
    elif rank > 80:
        score -= 4
        reasons.append("市值排名靠后，风险较高")
    
    trend_consistency = abs(change_24h / max(abs(change_7d), 0.1))
    if 0.5 < trend_consistency < 2:
        score += 6
        reasons.append("趋势一致性较好")
    
    reasons = sorted(reasons, key=lambda x: len(x), reverse=True)[:5]
    
    if score >= 55:
        return {"buy": True, "confidence": "high", "score": score, "reasons": reasons, "risk_level": "low"}
    elif score >= 35:
        return {"buy": True, "confidence": "medium", "score": score, "reasons": reasons, "risk_level": "medium"}
    elif score >= 20:
        return {"buy": False, "confidence": "low", "score": score, "reasons": reasons, "risk_level": "medium-high"}
    else:
        return {"buy": False, "confidence": "very_low", "score": score, "reasons": reasons, "risk_level": "high"}

def get_fallback_top_100():
    return None

def fetch_top_100_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h,7d,30d"
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if not data or not isinstance(data, list):
            raise Exception("Empty or invalid response")
        
        coins = []
        for idx, item in enumerate(data, 1):
            try:
                change_24h = float(item.get("price_change_percentage_24h", 0))
                change_7d = float(item.get("price_change_percentage_7d", 0))
                change_30d = float(item.get("price_change_percentage_30d", 0))
                volume_24h_usd = float(item.get("total_volume", 0))
                market_cap_usd = float(item.get("market_cap", 0))
                price_usd = float(item.get("current_price", 0))
                
                buy_signal = calculate_buy_signal(change_24h, change_7d, change_30d, volume_24h_usd, market_cap_usd, price_usd, idx)
                
                price_fmt = f"${price_usd:,.2f}" if price_usd else "$0.00"
                market_cap_fmt = f"${market_cap_usd:,.0f}" if market_cap_usd else "$0"
                volume_fmt = f"${volume_24h_usd:,.0f}" if volume_24h_usd else "$0"
                
                coins.append({
                    "rank": idx,
                    "symbol": str(item.get("symbol", "")).upper(),
                    "name": str(item.get("name", "")),
                    "price": price_fmt,
                    "price_usd": price_usd,
                    "market_cap": market_cap_fmt,
                    "market_cap_usd": market_cap_usd,
                    "volume_24h": volume_fmt,
                    "volume_24h_usd": volume_24h_usd,
                    "change_24h": f"{change_24h:+.2f}%",
                    "change_7d": f"{change_7d:+.2f}%",
                    "change_30d": f"{change_30d:+.2f}%",
                    "circulating_supply": item.get("circulating_supply", 0),
                    "max_supply": item.get("max_supply", 0),
                    "buy_signal": buy_signal,
                    "platform": "CoinGecko",
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "url": f"https://www.coingecko.com/en/coins/{item.get('id', '')}"
                })
            except Exception as item_e:
                print(f"Error processing item {idx}: {item_e}")
                continue
        
        return coins if coins else []
    
    except Exception as e:
        print(f"CoinGecko API error for top 100: {e}")
        return []

@router.get("/top-100", summary="获取排名前100的虚拟币")
def get_top_100_coins(userid: str = Header(None)):
    if not userid:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "message": "请求头中缺少 userid 参数"}
        )
    
    try:
        coins = fetch_top_100_coins()
        if not coins:
            raise Exception("无法获取虚拟币排名数据")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": f"获取虚拟币排名数据失败: {str(e)}"}
        )
    
    buy_recommend = [coin for coin in coins if coin["buy_signal"]["buy"]]
    not_recommend = [coin for coin in coins if not coin["buy_signal"]["buy"]]
    
    buy_recommend.sort(key=lambda x: x["buy_signal"]["score"], reverse=True)
    not_recommend.sort(key=lambda x: x["buy_signal"]["score"], reverse=True)
    
    return {
        "success": True,
        "count": len(coins),
        "userid": userid,
        "data": coins,
        "buy_recommend": {
            "count": len(buy_recommend),
            "data": buy_recommend
        },
        "not_recommend": {
            "count": len(not_recommend),
            "data": not_recommend
        },
        "message": "获取虚拟币排名前100成功",
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/coin/{symbol}", summary="查询特定虚拟币详情")
def get_coin_detail(
    symbol: str,
    userid: str = Header(None)
):
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    symbol = symbol.upper()
    
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={symbol.lower()}&order=market_cap_desc&per_page=1&page=1&sparkline=false&price_change_percentage=24h%2C7d%2C30d"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                item = data[0]
                rank = item.get("market_cap_rank", 0)
                change_24h = item.get("price_change_percentage_24h", 0)
                change_7d = item.get("price_change_percentage_7d", 0)
                change_30d = item.get("price_change_percentage_30d", 0)
                volume_24h_usd = item.get("total_volume", 0)
                market_cap_usd = item.get("market_cap", 0)
                price_usd = item.get("current_price", 0)
                
                buy_signal = calculate_buy_signal(change_24h, change_7d, change_30d, volume_24h_usd, market_cap_usd, price_usd, rank)
                
                price_fmt = f"${price_usd:,.2f}" if price_usd else "$0.00"
                market_cap_fmt = f"${market_cap_usd:,.0f}" if market_cap_usd else "$0"
                volume_fmt = f"${volume_24h_usd:,.0f}" if volume_24h_usd else "$0"
                
                return {
                    "success": True,
                    "symbol": symbol,
                    "name": item.get("name", ""),
                    "price": price_fmt,
                    "price_usd": price_usd,
                    "market_cap": market_cap_fmt,
                    "market_cap_usd": market_cap_usd,
                    "volume_24h": volume_fmt,
                    "volume_24h_usd": volume_24h_usd,
                    "change_24h": f"{change_24h:+.2f}%",
                    "change_7d": f"{change_7d:+.2f}%",
                    "change_30d": f"{change_30d:+.2f}%",
                    "rank": rank,
                    "circulating_supply": item.get("circulating_supply", 0),
                    "max_supply": item.get("max_supply", 0),
                    "high_24h": f"${item.get('high_24h', 0):,.2f}",
                    "low_24h": f"${item.get('low_24h', 0):,.2f}",
                    "buy_signal": buy_signal,
                    "platform": "CoinGecko",
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "url": f"https://www.coingecko.com/en/coins/{item.get('id', '')}",
                    "userid": userid
                }
        
        raise HTTPException(status_code=404, detail={"success": False, "message": f"未找到虚拟币: {symbol}"})
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching coin detail: {e}")
        raise HTTPException(status_code=500, detail={"success": False, "message": "获取虚拟币详情失败"})


class FavoriteRequest(BaseModel):
    symbol: str
    name: str = ""


@router.post("/favorites", summary="收藏虚拟币")
def add_favorite(req: FavoriteRequest, userid: str = Header(None)):
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        # 先检查是否已经收藏
        db_execute(cursor, "SELECT id FROM crypto_favorites WHERE user_id = %s AND symbol = %s", (userid, req.symbol.upper()))
        existing = cursor.fetchone()
        
        if existing:
            return {"success": True, "message": "该虚拟币已经收藏"}
        
        # 添加收藏
        db_execute(cursor, "INSERT INTO crypto_favorites (user_id, symbol, name) VALUES (%s, %s, %s)",
                       (userid, req.symbol.upper(), req.name))
        conn.commit()
        
        print(f"✅ 用户 {userid} 收藏虚拟币: {req.symbol.upper()}")
        
        return {"success": True, "message": "收藏成功"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"success": False, "message": f"收藏失败: {str(e)}"})
    finally:
        conn.close()


@router.delete("/favorites/{symbol}", summary="取消收藏虚拟币")
def remove_favorite(symbol: str, userid: str = Header(None)):
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT name FROM crypto_favorites WHERE user_id = %s AND symbol = %s", (userid, symbol.upper()))
        result = cursor.fetchone()
        coin_name = result[0] if result else ""
        
        db_execute(cursor, "DELETE FROM crypto_favorites WHERE user_id = %s AND symbol = %s", (userid, symbol.upper()))
        
        if cursor.rowcount > 0:
            db_execute(cursor, "INSERT INTO crypto_favorites_removed (user_id, symbol, name, removed_at) VALUES (%s, %s, %s, %s)", (userid, symbol.upper(), coin_name, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ 用户 {userid} 取消收藏虚拟币: {symbol.upper()}")
            return {"success": True, "message": "取消收藏成功"}
        else:
            return {"success": True, "message": "该虚拟币未在收藏列表中"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail={"success": False, "message": f"取消收藏失败: {str(e)}"})
    finally:
        conn.close()


@router.get("/favorites", summary="获取收藏的虚拟币列表")
def get_favorites(userid: str = Header(None)):
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    try:
        db_execute(cursor, "SELECT symbol, name, created_at FROM crypto_favorites WHERE user_id = %s ORDER BY created_at DESC", (userid,))
        favorites = cursor.fetchall()
        
        favorite_list = []
        for fav in favorites:
            favorite_list.append({
                "symbol": fav[0],
                "name": fav[1],
                "created_at": str(fav[2])
            })
        
        return {"success": True, "count": len(favorite_list), "favorites": favorite_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "message": f"获取收藏列表失败: {str(e)}"})
    finally:
        conn.close()

@router.get("/favorites/removed", summary="查询取消收藏列表")
def get_removed_favorites(userid: str = Header(None)):
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    try:
        conn = database.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT symbol, name, removed_at FROM crypto_favorites_removed WHERE user_id = %s ORDER BY removed_at DESC",
            (userid,)
        )
        records = cursor.fetchall()
        
        removed_list = []
        for record in records:
            removed_list.append({
                "symbol": record[0],
                "name": record[1] if record[1] else "",
                "removed_at": record[2]
            })
        
        return {"success": True, "count": len(removed_list), "data": removed_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail={"success": False, "message": f"获取取消收藏列表失败: {str(e)}"})
    finally:
        conn.close()

async def fetch_meituan_homepage_async():
    """
    异步获取美团首页数据（使用Playwright）

    通过Playwright无头浏览器访问美团H5页面，捕获API数据

    Returns:
        tuple: (data, error)
            - data: 包含导航、城市、推荐等数据的字典
            - error: 错误信息，如果成功则为None
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, "Playwright 未安装，请先安装: pip install playwright && playwright install chromium"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            context = await browser.new_context(
                viewport={'width': 375, 'height': 667},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
            )
            
            page = await context.new_page()
            
            categories = []
            restaurants = []
            banners = []
            
            async def handle_response(response):
                pass
            
            page.on('response', handle_response)
            
            await page.goto("https://h5.meituan.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            for i in range(3):
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(1)
            
            page_data = await page.evaluate("""() => {
                const results = {
                    categories: [],
                    restaurants: [],
                    banners: []
                };
                
                document.querySelectorAll('[class*="nav"] a, [class*="Nav"] a, [class*="menu"] a, [class*="Menu"] a').forEach(el => {
                    const text = el.innerText;
                    if (text && text.trim().length > 0 && text.trim().length < 10) {
                        if (!results.categories.includes(text.trim())) {
                            results.categories.push(text.trim());
                        }
                    }
                });
                
                const allElements = document.querySelectorAll('div, a, section');
                allElements.forEach(el => {
                    const text = el.innerText;
                    if (!text) return;
                    
                    const hasShopName = /[店馆楼城]/.test(text) || text.includes('·') || text.includes('（多城市）');
                    const hasProduct = text.includes('【') || text.includes('】');
                    const hasPrice = text.includes('¥') || text.includes('起');
                    
                    if ((hasShopName || hasProduct) && text.length > 10 && text.length < 500) {
                        const lines = text.trim().split('\\n');
                        if (lines.length >= 3) {
                            const shopName = lines[0];
                            if (shopName.length > 2 && shopName.length < 50) {
                                let price = '';
                                let product = '';
                                
                                for (let j = 1; j < lines.length; j++) {
                                    if (lines[j].includes('¥') || lines[j].includes('元')) {
                                        price = lines[j].trim();
                                    } else if (lines[j].includes('【') && lines[j].includes('】')) {
                                        product = lines[j].trim();
                                    }
                                }
                                
                                if (!results.restaurants.find(r => r.name === shopName)) {
                                    results.restaurants.push({
                                        name: shopName,
                                        product: product,
                                        price: price,
                                        rating: '',
                                        month_sales: '',
                                        delivery_time: '',
                                        delivery_fee: ''
                                    });
                                }
                            }
                        }
                    }
                });
                
                document.querySelectorAll('[class*="banner"] img, [class*="Banner"] img, [class*="swiper"] img').forEach(el => {
                    const src = el.src || el.getAttribute('data-src');
                    if (src) {
                        results.banners.push({ image: src, url: '' });
                    }
                });
                
                return results;
            }""")
            
            await browser.close()
            
            categories = page_data.get('categories', [])
            restaurants = page_data.get('restaurants', [])
            banners = page_data.get('banners', [])
            
            if not categories:
                categories = [
                    {'name': '外卖'},
                    {'name': '美食团购'},
                    {'name': '酒店'},
                    {'name': '娱乐'},
                    {'name': '猫眼电影'}
                ]
            
            if not banners:
                banners = [
                    {'image': '', 'url': '', 'title': '美团优惠活动'},
                    {'image': '', 'url': '', 'title': '新用户专享'}
                ]
            
            return {
                'categories': categories,
                'restaurants': restaurants,
                'banners': banners,
                'services': [],
                'cities': [],
                'source': '美团官网'
            }, None
            
    except Exception as e:
        return None, f"爬取美团数据失败: {str(e)}"


def fetch_meituan_homepage():
    """
    获取美团首页数据（爬虫函数）

    通过爬虫方式获取美团首页的导航菜单、城市信息、热门推荐等数据

    Returns:
        tuple: (data, error)
            - data: 包含导航、城市、推荐等数据的字典
            - error: 错误信息，如果成功则为None
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(fetch_meituan_homepage_async())

@router.get("/meituan/home", summary="获取美团首页数据")
def get_meituan_home(userid: str = Header(None)):
    """
    获取美团首页数据接口

    提供HTTP接口供外部调用，获取美团首页数据

    Args:
        userid: 用户ID（请求头参数），用于身份验证

    Returns:
        dict: 包含success、userid、data、message、update_time的响应字典
              data中包含导航、城市、推荐等数据
    """
    if not userid:
        raise HTTPException(status_code=400, detail={"success": False, "message": "请求头中缺少 userid 参数"})
    
    data, error = fetch_meituan_homepage()
    
    if error:
        raise HTTPException(status_code=500, detail={"success": False, "message": error})
    
    if not data:
        raise HTTPException(status_code=500, detail={"success": False, "message": "获取美团数据失败"})
    
    return {
        "success": True,
        "userid": userid,
        "data": data,
        "message": "获取美团首页数据成功",
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


async def fetch_meituan_waimai_homepage_async(address: str = "长沙市岳麓区5G加速港"):
    """
    异步获取美团外卖首页数据（使用Playwright）

    通过Playwright无头浏览器访问美团外卖H5页面，捕获API数据

    Args:
        address: 配送地址，默认为"长沙市岳麓区5G加速港"

    Returns:
        tuple: (data, error)
            - data: 包含分类、商家、优惠活动、轮播图等数据的字典
            - error: 错误信息，如果成功则为None
    """
    if not PLAYWRIGHT_AVAILABLE:
        return None, "Playwright 未安装，请先安装: pip install playwright && playwright install chromium"
    
    api_data = {}
    h5_shops = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            saved_state = load_saved_state()
            if saved_state:
                print(f"使用保存的登录状态 (Cookie: {len(saved_state.get('cookies', []))} 个)")
                context = await browser.new_context(
                    viewport={'width': 375, 'height': 667},
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    geolocation={'latitude': 28.2282, 'longitude': 112.9388},
                    permissions=['geolocation'],
                    storage_state=saved_state
                )
            else:
                print("未找到保存的登录状态，使用匿名模式")
                context = await browser.new_context(
                    viewport={'width': 375, 'height': 667},
                    user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                    geolocation={'latitude': 28.2282, 'longitude': 112.9388},
                    permissions=['geolocation']
                )
            
            page = await context.new_page()
            
            async def handle_response(response):
                url = response.url
                if 'i.waimai.meituan.com' in url and response.status == 200:
                    try:
                        data = await response.json()
                        api_data[url] = data
                    except:
                        pass
            
            page.on('response', handle_response)
            
            await page.goto("https://h5.waimai.meituan.com/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(10)
            
            try:
                close_buttons = await page.query_selector_all("[class*='close'], [class*='Close'], [class*='modalClose']")
                for btn in close_buttons:
                    try:
                        await btn.click()
                        await asyncio.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            try:
                await page.evaluate("""() => {
                    const selectors = ['.modalShadow', '.modalContainer', '[class*="modal"]', '[class*="Modal"]', '[class*="popup"]', '[class*="Popup"]'];
                    selectors.forEach(sel => {
                        const elements = document.querySelectorAll(sel);
                        elements.forEach(el => {
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                            el.style.pointerEvents = 'none';
                        });
                    });
                }""")
                await asyncio.sleep(2)
            except:
                pass
            
            try:
                print(f"当前页面URL: {page.url}")
                
                await page.evaluate("""() => {
                    const selectors = ['.addr_W3eGpu', '.ellipsis_dSZz_q', '.upHeader_SFVuMM', '.homeHeader_cMSobe', '[class*="address"]', '[class*="addr"]'];
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
                
                print(f"点击地址选择器后的URL: {page.url}")
                
                current_address = await page.evaluate("""() => {
                    const selectors = ['.addr_W3eGpu', '.ellipsis_dSZz_q', '.upHeader_SFVuMM', '.homeHeader_cMSobe', '[class*="address"]', '[class*="addr"]'];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText) {
                            return el.innerText.trim();
                        }
                    }
                    return '';
                }""")
                print(f"当前地址: {current_address}")
            except Exception as e:
                print(f"点击地址选择器出错: {e}")
            
            try:
                print(f"尝试从地址列表中选择...")
                
                selected = await page.evaluate("""() => {
                    const keywords = ['5G加速港', '湖南湘江新区大学生创新创业园', '大学生创新创业园', '岳麓区'];
                    
                    for (const keyword of keywords) {
                        const elements = document.querySelectorAll('[class*="deliveryPoiItem"], [class*="poiList"], [class*="poiItem"], [class*="addressItem"], [class*="item"]');
                        
                        for (const el of elements) {
                            const text = (el.innerText || '').trim();
                            if (text.includes(keyword)) {
                                console.log(`找到匹配地址: ${text}`);
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
                
                print(f"选择地址结果: {selected}")
                
                if not selected.get('success'):
                    print(f"未找到匹配地址，尝试搜索...")
                    address_input = await page.query_selector("input.poiInput_RoNbDP, input[placeholder*='小区/街道/大厦/学校名称']")
                    if address_input:
                        print(f"找到地址输入框")
                        await address_input.click()
                        await asyncio.sleep(2)
                        await address_input.fill(address)
                        await asyncio.sleep(3)
                        await address_input.press('Enter')
                        await asyncio.sleep(10)
                        
                        try:
                            await page.evaluate("""() => {
                                const keywords = ['5G加速港', '湖南湘江新区', '大学生创新创业园', '岳麓区'];
                                for (const keyword of keywords) {
                                    const elements = document.querySelectorAll('[class*="deliveryPoiItem"], [class*="poiList"], [class*="poiItem"], [class*="addressItem"], [class*="item"]');
                                    for (const el of elements) {
                                        const text = (el.innerText || '').trim();
                                        if (text.includes(keyword)) {
                                            el.click();
                                            return true;
                                        }
                                    }
                                }
                                return false;
                            }""")
                            await asyncio.sleep(5)
                        except Exception as e:
                            print(f"点击搜索结果出错: {e}")
                    else:
                        print(f"未找到地址输入框")
            except Exception as e:
                print(f"选择地址出错: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"等待页面加载商家数据...")
            for i in range(10):
                await asyncio.sleep(2)
                
                # 检查是否有网络错误
                network_error = await page.evaluate("""() => {
                    const text = document.body.innerText || '';
                    return text.includes('网络好像不太给力') || text.includes('重新加载');
                }""")
                
                if network_error:
                    print(f"  检测到网络错误，尝试重新加载...")
                    try:
                        await page.reload(wait_until="networkidle", timeout=30000)
                        await asyncio.sleep(3)
                    except:
                        pass
                
                # 检查是否需要开启定位
                need_location = await page.evaluate("""() => {
                    const text = document.body.innerText || '';
                    return text.includes('开启定位') || text.includes('去开启') || text.includes('授权获取精确定位');
                }""")
                
                if need_location:
                    print(f"  检测到需要定位，尝试点击'去开启'...")
                    try:
                        await page.evaluate("""() => {
                            const elements = document.querySelectorAll('div, a, button, span');
                            for (const el of elements) {
                                const text = (el.innerText || '').trim();
                                if (text.includes('去开启') || text.includes('开启定位')) {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        await asyncio.sleep(3)
                    except:
                        pass
                
                print(f"  等待中... ({i+1}/10)")
            
            await asyncio.sleep(15)
            
            for i in range(5):
                await page.mouse.wheel(0, 1000)
                await asyncio.sleep(2)
            
            await asyncio.sleep(10)
            
            await browser.close()
            
            async with async_playwright() as p2:
                browser2 = await p2.chromium.launch(headless=True)
                if saved_state:
                    context2 = await browser2.new_context(
                        viewport={'width': 375, 'height': 667},
                        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                        storage_state=saved_state
                    )
                else:
                    context2 = await browser2.new_context(
                        viewport={'width': 375, 'height': 667},
                        user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                    )
                
                page2 = await context2.new_page()
                
                await page2.goto("https://h5.meituan.com/", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(5)
                
                for i in range(3):
                    await page2.mouse.wheel(0, 800)
                    await asyncio.sleep(1)
                
                h5_data = await page2.evaluate("""() => {
                    const results = [];
                    const allElements = document.querySelectorAll('div, a, section');
                    allElements.forEach(el => {
                        const text = el.innerText;
                        if (!text) return;
                        
                        const hasShopName = /[店馆楼城]/.test(text) || text.includes('·') || text.includes('（多城市）');
                        const hasProduct = text.includes('【') || text.includes('】');
                        const hasPrice = text.includes('¥') || text.includes('起');
                        
                        if ((hasShopName || hasProduct) && text.length > 10 && text.length < 500) {
                            const lines = text.trim().split('\\n');
                            if (lines.length >= 3) {
                                const shopName = lines[0];
                                if (shopName.length > 2 && shopName.length < 50) {
                                    let price = '';
                                    let product = '';
                                    
                                    for (let j = 1; j < lines.length; j++) {
                                        if (lines[j].includes('¥') || lines[j].includes('元')) {
                                            price = lines[j].trim();
                                        } else if (lines[j].includes('【') && lines[j].includes('】')) {
                                            product = lines[j].trim();
                                        }
                                    }
                                    
                                    if (!results.find(r => r.name === shopName)) {
                                        results.push({
                                            name: shopName,
                                            product: product,
                                            price: price
                                        });
                                    }
                                }
                            }
                        }
                    });
                    return results;
                }""")
                
                h5_shops = h5_data
                
                await browser2.close()
        
        categories = []
        restaurants = []
        banners = []
        promotions = []
        filters = []
        
        for url, data in api_data.items():
            if 'rcmd' in url:
                if 'data' in data and isinstance(data['data'], str):
                    try:
                        inner_data = json.loads(data['data'])
                        if 'module_list' in inner_data:
                            for module in inner_data['module_list']:
                                if 'module_list' in module:
                                    for sub_module in module['module_list']:
                                        if 'string_data' in sub_module and sub_module['string_data']:
                                            try:
                                                string_data = json.loads(sub_module['string_data'])
                                                
                                                if 'cate_list' in string_data:
                                                    for cate in string_data['cate_list']:
                                                        categories.append({
                                                            'name': cate.get('name', ''),
                                                            'icon': cate.get('url', ''),
                                                            'code': cate.get('code', '')
                                                        })
                                                
                                                if 'poi_list' in string_data:
                                                    for poi in string_data['poi_list'][:30]:
                                                        mt_poi_info = poi.get('mt_poi_info', {})
                                                        restaurants.append({
                                                            'name': mt_poi_info.get('poi_name', ''),
                                                            'rating': str(mt_poi_info.get('poi_score', '')),
                                                            'month_sales': mt_poi_info.get('month_sales', ''),
                                                            'delivery_time': mt_poi_info.get('delivery_time', ''),
                                                            'delivery_fee': mt_poi_info.get('shipping_fee', ''),
                                                            'min_price': mt_poi_info.get('min_price', ''),
                                                            'address': mt_poi_info.get('address', '')
                                                        })
                                                
                                                if 'banner_list' in string_data:
                                                    for banner in string_data['banner_list']:
                                                        banners.append({
                                                            'image': banner.get('pic_url', ''),
                                                            'url': banner.get('link', '')
                                                        })
                                                
                                                if 'activity_list' in string_data:
                                                    for activity in string_data['activity_list']:
                                                        promotions.append({
                                                            'title': activity.get('name', ''),
                                                            'description': activity.get('info', '')
                                                        })
                                            except:
                                                pass
                    except:
                        pass
            
            if 'dsp/resource' in url:
                if 'data' in data and 'entrance_openH5shouyebanner_et_code' in data['data']:
                    banner_data = data['data']['entrance_openH5shouyebanner_et_code']
                    if 'module_list' in banner_data:
                        for banner in banner_data['module_list']:
                            banners.append({
                                'image': banner.get('picUrl', ''),
                                'url': banner.get('activityUrl', '')
                            })
        
        if not restaurants and h5_shops:
            for shop in h5_shops:
                restaurants.append({
                    'name': shop.get('name', ''),
                    'rating': '',
                    'month_sales': '',
                    'delivery_time': '',
                    'delivery_fee': '',
                    'min_price': '',
                    'address': '',
                    'product': shop.get('product', ''),
                    'price': shop.get('price', '')
                })
        
        filters = [
            {'name': '点评高分'},
            {'name': '优惠商家'},
            {'name': '满减优惠'},
            {'name': '品牌商家'}
        ]
        
        categories = [dict(t) for t in {tuple(d.items()) for d in categories}]
        banners = [dict(t) for t in {tuple(d.items()) for d in banners}]
        
        if not categories:
            categories = [
                {'name': '美食', 'icon': '', 'code': '910'},
                {'name': '鲜花蛋糕', 'icon': '', 'code': '23'},
                {'name': '甜点饮品', 'icon': '', 'code': '19'},
                {'name': '快食简餐', 'icon': '', 'code': '100325'},
                {'name': '超市便利', 'icon': '', 'code': '101574'}
            ]
        
        return {
            'address': address,
            'categories': categories,
            'restaurants': restaurants,
            'promotions': promotions,
            'banners': banners,
            'filters': filters,
            'source': '美团外卖'
        }, None
        
    except Exception as e:
        return None, f"爬取美团外卖数据失败: {str(e)}"


def fetch_meituan_waimai_homepage(address: str = "长沙市岳麓区5G加速港"):
    """
    获取美团外卖首页数据（爬虫函数）

    通过爬虫方式获取美团外卖首页的分类、商家、优惠活动、轮播图等数据

    Args:
        address: 配送地址，默认为"长沙市岳麓区5G加速港"

    Returns:
        tuple: (data, error)
            - data: 包含分类、商家、优惠活动、轮播图等数据的字典
            - error: 错误信息，如果成功则为None
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(fetch_meituan_waimai_homepage_async(address))


@router.get("/meituan/waimai/home", summary="获取美团外卖首页数据")
def get_meituan_waimai_home(
    userid: str = Header(None),
    address: str = "长沙市岳麓区5G加速港"
):
    """
    获取美团外卖首页数据接口

    提供HTTP接口供外部调用，获取指定地址的美团外卖首页数据

    Args:
        userid: 用户ID（请求头参数），用于身份验证
        address: 配送地址，默认为"长沙市岳麓区5G加速港"

    Returns:
        dict: 包含success、userid、address、data、message、update_time的响应字典
              data中包含分类、商家、优惠活动、轮播图等数据
    """
    if not userid:
        raise HTTPException(
            status_code=400, 
            detail={"success": False, "message": "请求头中缺少 userid 参数"}
        )
    
    data, error = fetch_meituan_waimai_homepage(address)
    
    if error:
        raise HTTPException(
            status_code=500, 
            detail={"success": False, "message": error}
        )
    
    if not data:
        raise HTTPException(
            status_code=500, 
            detail={"success": False, "message": "获取美团外卖数据失败"}
        )
    
    return {
        "success": True,
        "userid": userid,
        "address": address,
        "data": data,
        "message": "获取美团外卖首页数据成功",
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
