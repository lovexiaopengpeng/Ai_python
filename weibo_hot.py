from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import datetime
import requests

router = APIRouter(prefix="/weibo", tags=["微博热点"])

class HotNews(BaseModel):
    title: str
    description: str
    time: str
    url: str
    hot_index: Optional[int] = None

def fetch_weibo_hot_spider() -> List[HotNews]:
    news_list = []
    
    url = "https://m.weibo.cn/api/container/getIndex?containerid=1060030002_001"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.weibo.cn/"
    }
    
    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()
    
    if data.get("ok") != 1:
        raise Exception(f"微博API返回失败: {data.get('msg', '未知错误')}")
    
    cards = data.get("data", {}).get("cards", [])
    
    if not cards:
        raise Exception("未获取到卡片数据")
    
    for card in cards:
        card_group = card.get("card_group", [])
        if card_group:
            for item in card_group[:10]:
                if item.get("card_type") == 11:
                    title = item.get("desc", "")
                    scheme = item.get("scheme", "")
                    hot_value = item.get("hot_value", 0)
                    
                    news_list.append(HotNews(
                        title=title,
                        description="",
                        time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        url=scheme,
                        hot_index=hot_value
                    ))
    
    if not news_list:
        raise Exception("未获取到热点数据")
    
    return news_list[:10]

@router.get("/hot/tech", summary="获取科技热点资讯")
def get_tech_hot_news():
    try:
        news = fetch_weibo_hot_spider()
        return {
            "success": True,
            "count": len(news),
            "data": news,
            "message": "获取科技热点成功"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"获取科技热点失败: {str(e)}"
            }
        )

@router.get("/hot", summary="获取综合热点资讯")
def get_all_hot_news():
    return get_tech_hot_news()