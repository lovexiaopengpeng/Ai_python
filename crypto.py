from fastapi import APIRouter, HTTPException, Header
import requests
import datetime

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

def calculate_buy_signal(change_24h, change_7d, change_30d, volume_24h_usd, market_cap_usd):
    score = 0
    reasons = []
    
    change_24h = float(change_24h) if change_24h else 0
    change_7d = float(change_7d) if change_7d else 0
    change_30d = float(change_30d) if change_30d else 0
    
    if change_24h < -5:
        score += 30
        reasons.append("24小时跌幅超过5%，可能处于低位")
    elif change_24h < -2:
        score += 15
        reasons.append("24小时小幅下跌")
    elif change_24h > 10:
        score -= 20
        reasons.append("24小时涨幅过大，谨慎追高")
    elif change_24h > 5:
        score -= 10
        reasons.append("24小时涨幅较大")
    
    if change_7d < -10:
        score += 25
        reasons.append("7日跌幅超过10%，可能处于低位")
    elif change_7d < -3:
        score += 10
        reasons.append("7日小幅下跌")
    elif change_7d > 15:
        score -= 15
        reasons.append("7日涨幅过大")
    
    if change_30d < -15:
        score += 20
        reasons.append("30日跌幅超过15%")
    elif change_30d < -5:
        score += 8
        reasons.append("30日小幅下跌")
    elif change_30d > 20:
        score -= 10
        reasons.append("30日涨幅较大")
    
    avg_change = (change_24h + change_7d + change_30d) / 3
    if avg_change < -3:
        score += 15
        reasons.append("整体趋势向下，可能出现买入机会")
    elif avg_change > 5:
        score -= 10
        reasons.append("整体趋势向上，注意风险")
    
    if volume_24h_usd and market_cap_usd:
        volume_ratio = volume_24h_usd / max(market_cap_usd, 1)
        if volume_ratio > 0.05:
            score += 10
            reasons.append("成交量活跃")
        elif volume_ratio < 0.01:
            score -= 5
            reasons.append("成交量低迷")
    
    if score >= 60:
        return {"buy": True, "confidence": "high", "score": score, "reasons": reasons}
    elif score >= 35:
        return {"buy": True, "confidence": "medium", "score": score, "reasons": reasons}
    elif score >= 15:
        return {"buy": False, "confidence": "low", "score": score, "reasons": reasons}
    else:
        return {"buy": False, "confidence": "very_low", "score": score, "reasons": reasons}

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
        
        coins = []
        for idx, item in enumerate(data, 1):
            change_24h = item.get("price_change_percentage_24h", 0)
            change_7d = item.get("price_change_percentage_7d", 0)
            change_30d = item.get("price_change_percentage_30d", 0)
            volume_24h_usd = item.get("total_volume", 0)
            market_cap_usd = item.get("market_cap", 0)
            
            buy_signal = calculate_buy_signal(change_24h, change_7d, change_30d, volume_24h_usd, market_cap_usd)
            
            coins.append({
                "rank": idx,
                "symbol": item.get("symbol", "").upper(),
                "name": item.get("name", ""),
                "price": f"${item.get('current_price', 0):,.2f}",
                "price_usd": item.get("current_price", 0),
                "market_cap": f"${item.get('market_cap', 0):,.0f}",
                "market_cap_usd": item.get("market_cap", 0),
                "volume_24h": f"${item.get('total_volume', 0):,.0f}",
                "volume_24h_usd": item.get("total_volume", 0),
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
        return coins
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
    
    return {
        "success": True,
        "count": len(coins),
        "userid": userid,
        "data": coins,
        "message": "获取虚拟币排名前100成功",
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }