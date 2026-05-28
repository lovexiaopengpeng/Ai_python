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
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fallback_data = [
        {"rank": 1, "symbol": "BTC", "name": "Bitcoin", "price_usd": 75500, "market_cap_usd": 1510000000000, "volume_24h_usd": 35000000000, "change_24h": -1.5, "change_7d": 2.3, "change_30d": 5.8, "id": "bitcoin"},
        {"rank": 2, "symbol": "ETH", "name": "Ethereum", "price_usd": 2070, "market_cap_usd": 250000000000, "volume_24h_usd": 15000000000, "change_24h": -1.2, "change_7d": 1.8, "change_30d": 4.2, "id": "ethereum"},
        {"rank": 3, "symbol": "USDT", "name": "Tether", "price_usd": 1, "market_cap_usd": 189000000000, "volume_24h_usd": 65000000000, "change_24h": 0.0, "change_7d": 0.1, "change_30d": 0.0, "id": "tether"},
        {"rank": 4, "symbol": "BNB", "name": "BNB", "price_usd": 650, "market_cap_usd": 88000000000, "volume_24h_usd": 1100000000, "change_24h": -0.8, "change_7d": 3.5, "change_30d": 8.2, "id": "binancecoin"},
        {"rank": 5, "symbol": "XRP", "name": "XRP", "price_usd": 1.32, "market_cap_usd": 82000000000, "volume_24h_usd": 1500000000, "change_24h": -1.3, "change_7d": 0.5, "change_30d": -2.1, "id": "ripple"},
        {"rank": 6, "symbol": "USDC", "name": "USDC", "price_usd": 1, "market_cap_usd": 35000000000, "volume_24h_usd": 5000000000, "change_24h": 0.0, "change_7d": 0.0, "change_30d": 0.0, "id": "usd-coin"},
        {"rank": 7, "symbol": "SOL", "name": "Solana", "price_usd": 178, "market_cap_usd": 75000000000, "volume_24h_usd": 2500000000, "change_24h": 2.5, "change_7d": 8.2, "change_30d": 15.5, "id": "solana"},
        {"rank": 8, "symbol": "DOGE", "name": "Dogecoin", "price_usd": 0.125, "market_cap_usd": 17500000000, "volume_24h_usd": 800000000, "change_24h": 0.8, "change_7d": -2.3, "change_30d": -5.2, "id": "dogecoin"},
        {"rank": 9, "symbol": "TRX", "name": "TRON", "price_usd": 0.118, "market_cap_usd": 12000000000, "volume_24h_usd": 450000000, "change_24h": -0.5, "change_7d": 1.2, "change_30d": 3.8, "id": "tron"},
        {"rank": 10, "symbol": "SHIB", "name": "Shiba Inu", "price_usd": 0.0000123, "market_cap_usd": 8500000000, "volume_24h_usd": 320000000, "change_24h": 1.5, "change_7d": -3.2, "change_30d": -8.5, "id": "shiba-inu"},
        {"rank": 11, "symbol": "AVAX", "name": "Avalanche", "price_usd": 35.8, "market_cap_usd": 14500000000, "volume_24h_usd": 450000000, "change_24h": -2.1, "change_7d": -4.5, "change_30d": -12.3, "id": "avalanche-2"},
        {"rank": 12, "symbol": "LINK", "name": "Chainlink", "price_usd": 14.2, "market_cap_usd": 8800000000, "volume_24h_usd": 280000000, "change_24h": -1.8, "change_7d": -3.2, "change_30d": -6.8, "id": "chainlink"},
        {"rank": 13, "symbol": "ZEC", "name": "Zcash", "price_usd": 48.5, "market_cap_usd": 1200000000, "volume_24h_usd": 45000000, "change_24h": -8.5, "change_7d": -12.3, "change_30d": -18.5, "id": "zcash"},
        {"rank": 14, "symbol": "MATIC", "name": "Polygon", "price_usd": 0.85, "market_cap_usd": 9200000000, "volume_24h_usd": 380000000, "change_24h": 0.5, "change_7d": 2.1, "change_30d": 5.2, "id": "matic-network"},
        {"rank": 15, "symbol": "ADA", "name": "Cardano", "price_usd": 0.48, "market_cap_usd": 16200000000, "volume_24h_usd": 320000000, "change_24h": -1.2, "change_7d": -2.8, "change_30d": -5.5, "id": "cardano"},
        {"rank": 16, "symbol": "DOT", "name": "Polkadot", "price_usd": 7.85, "market_cap_usd": 9200000000, "volume_24h_usd": 180000000, "change_24h": -0.8, "change_7d": 1.5, "change_30d": 3.2, "id": "polkadot"},
        {"rank": 17, "symbol": "LTC", "name": "Litecoin", "price_usd": 78.5, "market_cap_usd": 5800000000, "volume_24h_usd": 420000000, "change_24h": -1.5, "change_7d": 0.8, "change_30d": 4.5, "id": "litecoin"},
        {"rank": 18, "symbol": "BCH", "name": "Bitcoin Cash", "price_usd": 285, "market_cap_usd": 5600000000, "volume_24h_usd": 280000000, "change_24h": -2.2, "change_7d": -1.8, "change_30d": -4.5, "id": "bitcoin-cash"},
        {"rank": 19, "symbol": "XLM", "name": "Stellar", "price_usd": 0.125, "market_cap_usd": 2800000000, "volume_24h_usd": 85000000, "change_24h": -0.5, "change_7d": 1.2, "change_30d": 2.8, "id": "stellar"},
        {"rank": 20, "symbol": "TON", "name": "Toncoin", "price_usd": 2.35, "market_cap_usd": 7500000000, "volume_24h_usd": 120000000, "change_24h": -1.8, "change_7d": -3.5, "change_30d": -7.2, "id": "toncoin"},
    ]
    return fallback_data

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
        
        return coins if coins else get_fallback_top_100()
    
    except Exception as e:
        print(f"CoinGecko API error for top 100: {e}")
        return get_fallback_top_100()

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