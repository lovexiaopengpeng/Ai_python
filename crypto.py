from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import requests
import datetime
import sqlite3
import os

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

router = APIRouter(prefix="/crypto", tags=["虚拟币大额交易"])

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
        db_execute(cursor, "DELETE FROM crypto_favorites WHERE user_id = %s AND symbol = %s", (userid, symbol.upper()))
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