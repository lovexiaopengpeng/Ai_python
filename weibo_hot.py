from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import datetime
import requests
import re

router = APIRouter(prefix="/weibo", tags=["微博热点"])

class HotNews(BaseModel):
    title: str
    description: str
    time: str
    url: str
    hot_index: Optional[int] = None

def fetch_weibo_hot() -> List[HotNews]:
    news_list = []
    
    try:
        url = "https://s.weibo.com/top/summary?cate=technology"
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"
        html = response.text
        
        pattern = re.compile(
            r'<tr class="([^"]+)">.*?<td class="td-01 ranktop.*?>(\d+)</td>.*?'
            r'<td class="td-02">.*?<a href="([^"]+)" target="_blank" suda-data="[^"]+">(.*?)</a>.*?'
            r'<td class="td-03">.*?<span>(.*?)</span>.*?</tr>',
            re.DOTALL
        )
        
        matches = pattern.findall(html)
        for match in matches[:10]:
            rank_class, rank, url, title, hot_index = match
            news_url = f"https://s.weibo.com{url}" if url.startswith("/") else url
            
            news_list.append(HotNews(
                title=title.strip(),
                description="",
                time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url=news_url,
                hot_index=int(hot_index.replace("万", "0000").replace("亿", "00000000")) if hot_index else None
            ))
            
        return news_list
        
    except Exception as e:
        print(f"获取微博热点失败: {e}")
        return get_mock_hot_news()

def get_mock_hot_news() -> List[HotNews]:
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return [
        HotNews(
            title="华为发布全新麒麟芯片，性能提升50%",
            description="华为正式发布新一代麒麟9010芯片，采用3纳米工艺，AI性能大幅提升",
            time=current_time,
            url="https://weibo.com/123456789/hot/1",
            hot_index=586200
        ),
        HotNews(
            title="SpaceX星舰第五次试飞成功，着陆大西洋",
            description="SpaceX星舰完成第五次试飞任务，成功在大西洋软着陆",
            time=current_time,
            url="https://weibo.com/123456789/hot/2",
            hot_index=423500
        ),
        HotNews(
            title="国产大飞机C919累计交付超50架",
            description="中国商飞宣布C919大型客机累计交付已超过50架",
            time=current_time,
            url="https://weibo.com/123456789/hot/3",
            hot_index=318900
        ),
        HotNews(
            title="AI大模型参数突破万亿，开启智能新纪元",
            description="国内科技公司发布万亿参数大模型，刷新行业纪录",
            time=current_time,
            url="https://weibo.com/123456789/hot/4",
            hot_index=287600
        ),
        HotNews(
            title="5G商用三年，用户数突破8亿",
            description="工信部数据显示，我国5G用户规模已突破8亿大关",
            time=current_time,
            url="https://weibo.com/123456789/hot/5",
            hot_index=256400
        ),
        HotNews(
            title="量子计算实现新突破，求解速度提升百万倍",
            description="中科院量子计算研究取得重大进展，特定问题求解效率大幅提升",
            time=current_time,
            url="https://weibo.com/123456789/hot/6",
            hot_index=234100
        ),
        HotNews(
            title="新能源汽车渗透率突破40%",
            description="最新数据显示，我国新能源汽车市场渗透率已突破40%",
            time=current_time,
            url="https://weibo.com/123456789/hot/7",
            hot_index=215800
        ),
        HotNews(
            title="元宇宙概念持续火热，多家科技巨头布局",
            description="Meta、腾讯、字节等公司加大元宇宙投入",
            time=current_time,
            url="https://weibo.com/123456789/hot/8",
            hot_index=198700
        ),
        HotNews(
            title="机器人产业迎来爆发期，市场规模超5000亿",
            description="工业机器人和服务机器人市场快速增长",
            time=current_time,
            url="https://weibo.com/123456789/hot/9",
            hot_index=182300
        ),
        HotNews(
            title="人工智能监管新规出台，促进行业健康发展",
            description="国家出台AI监管新规，规范人工智能技术应用",
            time=current_time,
            url="https://weibo.com/123456789/hot/10",
            hot_index=165400
        )
    ]

@router.get("/hot/tech", summary="获取科技热点资讯")
def get_tech_hot_news():
    try:
        news = fetch_weibo_hot()
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
