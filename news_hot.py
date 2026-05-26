from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import datetime
import requests
from bs4 import BeautifulSoup

router = APIRouter(prefix="/news", tags=["热点资讯"])

class HotNews(BaseModel):
    title: str
    description: str
    time: str
    url: str
    hot_index: Optional[int] = None

NEWS_SOURCES = {
    "tech": {
        "name": "科技",
        "url": "https://tech.sina.com.cn/",
        "pattern": ["/doc-", "/article/"]
    },
    "finance": {
        "name": "财经",
        "url": "https://finance.sina.com.cn/",
        "pattern": ["/doc-", "/article/", "/roll/"]
    },
    "entertainment": {
        "name": "娱乐",
        "url": "https://ent.sina.com.cn/",
        "pattern": ["/doc-", "/article/"]
    },
    "sports": {
        "name": "体育",
        "url": "https://sports.sina.com.cn/",
        "pattern": ["/doc-", "/article/"]
    },
    "auto": {
        "name": "汽车",
        "url": "https://auto.sina.com.cn/",
        "pattern": ["/doc-", "/article/"]
    },
    "health": {
        "name": "健康",
        "url": "https://health.sina.com.cn/",
        "pattern": ["/doc-", "/article/"]
    }
}

def fetch_news_by_type(news_type: str) -> List[HotNews]:
    news_list = []
    
    if news_type not in NEWS_SOURCES:
        raise Exception(f"不支持的新闻类型: {news_type}")
    
    source = NEWS_SOURCES[news_type]
    url = source["url"]
    patterns = source["pattern"]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = "utf-8"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        
        is_valid = any(pattern in href for pattern in patterns)
        if is_valid and text and len(text) > 5:
            news_url = href if href.startswith('http') else url + href
            
            news_list.append(HotNews(
                title=text,
                description="",
                time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url=news_url,
                hot_index=None
            ))
        
        if len(news_list) >= 10:
            break
    
    if news_list:
        return news_list
    
    raise Exception(f"未获取到{source['name']}新闻数据")

@router.get("/hot", summary="获取热点资讯")
def get_hot_news(
    type: str = Query("tech", description="新闻类型: tech(科技), finance(财经), entertainment(娱乐), sports(体育), auto(汽车), health(健康)")
):
    try:
        news = fetch_news_by_type(type)
        source_info = NEWS_SOURCES.get(type, {"name": type})
        
        return {
            "success": True,
            "count": len(news),
            "type": type,
            "type_name": source_info["name"],
            "data": news,
            "message": f"获取{source_info['name']}热点成功"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"获取热点失败: {str(e)}"
            }
        )

@router.get("/hot/tech", summary="获取科技热点资讯")
def get_tech_hot_news():
    return get_hot_news(type="tech")

@router.get("/types", summary="获取支持的新闻类型")
def get_news_types():
    types = []
    for key, value in NEWS_SOURCES.items():
        types.append({
            "type": key,
            "name": value["name"],
            "url": value["url"]
        })
    
    return {
        "success": True,
        "types": types
    }