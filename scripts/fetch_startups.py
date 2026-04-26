#!/usr/bin/env python3
"""
StartupRadar 数据抓取脚本
从多渠道抓取初创公司信息和全网讨论。

数据源（参考豆包建议，全面覆盖）：
  ── 创投媒体 RSS ──
  1. 36氪          - 国内最大创投媒体
  2. 虎嗅          - 科技商业媒体
  3. 少数派        - 科技生活方式
  4. 铅笔道        - 早期创业访谈
  5. 创业邦        - 创投生态
  6. 投资界        - PE/VC 资讯
  7. TechCrunch    - 全球科技创投
  8. TechNode      - 中国科技英文媒体

  ── 创投数据平台 ──
  9. IT 桔子       - 创投数据库（每日新收录）
  10. 鲸准(36氪)   - 创投数据库

  ── 产品发现平台 ──
  11. Product Hunt  - 全球新产品首发
  12. Indie Hackers - 独立开发者社区

  ── 开源社区 ──
  13. GitHub Trending - 开源项目趋势
  14. HuggingFace    - AI 模型社区

  ── 社交媒体热搜 ──
  15. 微博热搜
  16. 知乎热榜
  17. 抖音热搜
  18. B站热搜
  19. 小红书
  20. Twitter/X Trending

  ── 垂直社区 ──
  21. 雪球         - 投资社区
  22. V2EX         - 开发者社区
"""

import json
import os
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from html import unescape

import feedparser
import httpx

# ========== 配置 ==========
RAW_DIR = Path(__file__).parent.parent / "raw"
RAW_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

HEADERS_BOT = {
    "User-Agent": "StartupRadar/1.0 (news aggregator; +https://github.com/startup-radar)"
}

# 关键词过滤
STARTUP_KEYWORDS_ZH = [
    "初创", "创业", "融资", "种子轮", "天使轮", "A轮", "B轮", "Pre-A", "Pre-Seed",
    "孵化", "加速器", "独角兽", "估值", "创始人", "联合创始人", "获投",
    "新锐", "新兴", "早期项目", "AI创业", "大模型", "AGI", "AIGC",
    "开源项目", "SaaS", "Web3", "硬科技", "生物医药", "芯片",
    "新一轮", "领投", "跟投", "战略投资", "数千万", "数亿",
    # ── 中国创投生态补充 ──
    "国产替代", "信创", "出海", "下沉市场", "新消费", "新能源",
    "智能制造", "自动驾驶", "具身智能", "人形机器人", "低空经济",
    "合成生物", "脑机接口", "量子计算", "商业航天",
    "红杉", "高瓴", "经纬", "IDG", "真格", "源码", "五源",
    "深创投", "达晨", "君联", "北极光", "GGV", "光速",
    "中关村", "张江", "南山", "前海", "天府", "光谷",
    "科创板", "北交所", "专精特新", "小巨人", "瞪羚企业",
]

STARTUP_KEYWORDS_EN = [
    "startup", "seed round", "series a", "series b", "pre-seed",
    "funding", "raised", "valuation", "founder", "co-founder",
    "incubator", "accelerator", "unicorn", "early-stage",
    "AI startup", "LLM", "open source", "SaaS", "Web3",
    "launch", "beta", "YC", "Y Combinator",
]


def clean_html(text):
    """去除 HTML 标签"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def matches_keywords(text, lang="zh"):
    """检查文本是否包含初创公司相关关键词"""
    text_lower = text.lower()
    keywords = STARTUP_KEYWORDS_ZH if lang == "zh" else STARTUP_KEYWORDS_EN
    return any(kw.lower() in text_lower for kw in keywords)


def make_entry(source, title, summary, url, published, lang="zh", entry_type="news", meta=None):
    """构造标准数据条目"""
    return {
        "source": source,
        "title": clean_html(title)[:200],
        "summary": clean_html(summary)[:500],
        "url": url,
        "published": published or TODAY,
        "lang": lang,
        "type": entry_type,
        "fetchedAt": TODAY,
        **({"meta": meta} if meta else {}),
    }


# ============================================================
#  第一部分：创投媒体 RSS
# ============================================================

RSS_FEEDS = [
    # ── 国内创投媒体（主力源）──
    {"name": "36氪",       "url": "https://36kr.com/feed",                "lang": "zh"},
    {"name": "虎嗅",       "url": "https://www.huxiu.com/rss/0.xml",     "lang": "zh"},
    {"name": "少数派",     "url": "https://sspai.com/feed",               "lang": "zh"},
    {"name": "铅笔道",     "url": "https://www.pencilnews.cn/feed",      "lang": "zh"},
    {"name": "创业邦",     "url": "https://www.cyzone.cn/rss/",          "lang": "zh"},
    {"name": "投资界",     "url": "https://www.pedaily.cn/rss/rss.xml",  "lang": "zh"},
    {"name": "钛媒体",     "url": "https://www.tmtpost.com/rss.xml",     "lang": "zh"},
    {"name": "极客公园",   "url": "https://www.geekpark.net/rss",        "lang": "zh"},
    {"name": "爱范儿",     "url": "https://www.ifanr.com/feed",          "lang": "zh"},
    {"name": "动点科技",   "url": "https://cn.technode.com/feed/",       "lang": "zh"},
    # ── 海外科技媒体 ──
    {"name": "TechCrunch",  "url": "https://techcrunch.com/feed/",     "lang": "en"},
    {"name": "TechNode",    "url": "https://technode.com/feed/",       "lang": "en"},
    {"name": "The Verge",   "url": "https://www.theverge.com/rss/index.xml", "lang": "en"},
    {"name": "Hacker News", "url": "https://hnrss.org/newest?q=startup+OR+funding+OR+launch", "lang": "en"},
]


def fetch_rss_feeds():
    """从 RSS 源抓取创投新闻"""
    print("📡 [1/8] 抓取创投媒体 RSS...")
    all_entries = []

    for feed_info in RSS_FEEDS:
        try:
            print(f"  → {feed_info['name']}...", end=" ")
            resp = httpx.get(
                feed_info["url"], headers=HEADERS_BOT,
                timeout=15, follow_redirects=True,
            )
            feed = feedparser.parse(resp.text)
            count = 0

            for entry in feed.entries[:50]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                link = entry.get("link", "")
                published = entry.get("published", entry.get("updated", ""))

                text = title + " " + summary
                if not matches_keywords(text, feed_info["lang"]):
                    continue

                all_entries.append(make_entry(
                    source=feed_info["name"],
                    title=title, summary=summary,
                    url=link, published=published,
                    lang=feed_info["lang"],
                ))
                count += 1

            print(f"{count} 条")
        except Exception as e:
            print(f"失败: {e}")

    print(f"  📊 RSS 合计: {len(all_entries)} 条")
    return all_entries


# ============================================================
#  第二部分：创投数据平台（IT 桔子、鲸准）
# ============================================================

def fetch_itjuzi():
    """
    IT 桔子 - 每日新收录初创公司
    https://www.itjuzi.com
    需要登录态 Cookie 或 API Token
    """
    print("📡 [2/8] 抓取创投数据平台...")
    entries = []

    # --- IT 桔子 ---
    cookie = os.getenv("ITJUZI_COOKIE", "")
    print(f"  → IT 桔子...", end=" ")
    if not cookie:
        print("跳过（需设置 ITJUZI_COOKIE）")
    else:
        try:
            resp = httpx.get(
                "https://www.itjuzi.com/api/investevents",
                params={"page": 1, "per_page": 30},
                headers={**HEADERS, "Cookie": cookie},
                timeout=15,
            )
            data = resp.json()
            for item in data.get("data", {}).get("data", []):
                entries.append(make_entry(
                    source="IT桔子",
                    title=f"{item.get('com_name', '')} 获得{item.get('round', '')}融资",
                    summary=f"投资方: {item.get('investor_name', '未披露')}，"
                            f"金额: {item.get('money', '未披露')}，"
                            f"行业: {item.get('cat_name', '')}",
                    url=f"https://www.itjuzi.com/company/{item.get('com_id', '')}",
                    published=item.get("date", TODAY),
                    meta={"round": item.get("round"), "money": item.get("money")},
                ))
            print(f"{len(entries)} 条融资事件")
        except Exception as e:
            print(f"失败: {e}")

    # --- 鲸准 ---
    jz_token = os.getenv("JINGDATA_TOKEN", "")
    print(f"  → 鲸准...", end=" ")
    if not jz_token:
        print("跳过（需设置 JINGDATA_TOKEN）")
    else:
        try:
            resp = httpx.get(
                "https://api.jingdata.com/v2/investevents",
                params={"page": 1, "pagesize": 30},
                headers={"Authorization": f"Bearer {jz_token}"},
                timeout=15,
            )
            data = resp.json()
            for item in data.get("data", []):
                entries.append(make_entry(
                    source="鲸准",
                    title=f"{item.get('company_name', '')} {item.get('round', '')}",
                    summary=item.get("brief", ""),
                    url=item.get("url", ""),
                    published=item.get("date", TODAY),
                    meta={"round": item.get("round"), "amount": item.get("amount")},
                ))
            print(f"{len([e for e in entries if e['source']=='鲸准'])} 条")
        except Exception as e:
            print(f"失败: {e}")

    return entries


# ============================================================
#  第三部分：产品发现平台（Product Hunt、Indie Hackers）
# ============================================================

def fetch_product_hunt():
    """Product Hunt - 全球新产品首发"""
    print("📡 [3/8] 抓取产品发现平台...")
    entries = []

    # --- Product Hunt ---
    token = os.getenv("PH_TOKEN", "")
    print(f"  → Product Hunt...", end=" ")
    if not token:
        print("跳过（需设置 PH_TOKEN）")
    else:
        try:
            resp = httpx.post(
                "https://api.producthunt.com/v2/api/graphql",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"query": """{
                    posts(order: RANKING, first: 30) {
                        edges { node {
                            name tagline url website
                            votesCount commentsCount createdAt
                            topics { edges { node { name } } }
                            makers { name headline }
                        }}
                    }
                }"""},
                timeout=15,
            )
            data = resp.json()
            for edge in data.get("data", {}).get("posts", {}).get("edges", []):
                node = edge["node"]
                topics = [e["node"]["name"] for e in node.get("topics", {}).get("edges", [])]
                makers = [m.get("name", "") for m in node.get("makers", [])]
                entries.append(make_entry(
                    source="Product Hunt",
                    title=node["name"],
                    summary=node.get("tagline", ""),
                    url=node.get("url", ""),
                    published=node.get("createdAt", ""),
                    lang="en", entry_type="product",
                    meta={
                        "votes": node.get("votesCount", 0),
                        "comments": node.get("commentsCount", 0),
                        "topics": topics,
                        "makers": makers,
                        "website": node.get("website", ""),
                    },
                ))
            print(f"{len(entries)} 个产品")
        except Exception as e:
            print(f"失败: {e}")

    # --- Indie Hackers（RSS） ---
    print(f"  → Indie Hackers...", end=" ")
    try:
        resp = httpx.get(
            "https://www.indiehackers.com/feed.xml",
            headers=HEADERS_BOT, timeout=15, follow_redirects=True,
        )
        feed = feedparser.parse(resp.text)
        ih_count = 0
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            entries.append(make_entry(
                source="Indie Hackers",
                title=title, summary=summary,
                url=entry.get("link", ""),
                published=entry.get("published", ""),
                lang="en", entry_type="community",
            ))
            ih_count += 1
        print(f"{ih_count} 条")
    except Exception as e:
        print(f"失败: {e}")

    return entries


# ============================================================
#  第四部分：开源社区（GitHub Trending、HuggingFace）
# ============================================================

def fetch_opensource():
    """GitHub Trending + HuggingFace 热门模型"""
    print("📡 [4/8] 抓取开源社区...")
    entries = []

    # --- GitHub Trending ---
    print(f"  → GitHub Trending...", end=" ")
    try:
        # 方案 A：非官方 API
        resp = httpx.get(
            "https://api.gitterapp.com/repositories?language=&since=daily",
            headers=HEADERS_BOT, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            gh_count = 0
            for repo in data[:40]:
                name = repo.get("name", "")
                desc = repo.get("description", "") or ""
                text = (name + " " + desc).lower()
                # 更宽泛的关键词匹配
                gh_keywords = STARTUP_KEYWORDS_EN + [
                    "llm", "agent", "model", "inference", "deploy",
                    "platform", "framework", "tool", "api",
                ]
                if any(kw.lower() in text for kw in gh_keywords):
                    entries.append(make_entry(
                        source="GitHub",
                        title=repo.get("fullName", name),
                        summary=desc[:300],
                        url=f"https://github.com/{repo.get('fullName', '')}",
                        published=TODAY,
                        lang="en", entry_type="repo",
                        meta={
                            "stars": repo.get("stars", 0),
                            "forks": repo.get("forks", 0),
                            "todayStars": repo.get("currentPeriodStars", 0),
                            "language": repo.get("language", ""),
                        },
                    ))
                    gh_count += 1
            print(f"{gh_count} 个仓库")
        else:
            # 方案 B：GitHub 官方搜索 API
            resp = httpx.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": "stars:>100 pushed:>" + TODAY,
                    "sort": "stars", "order": "desc", "per_page": 30,
                },
                headers={**HEADERS_BOT, "Accept": "application/vnd.github.v3+json"},
                timeout=15,
            )
            data = resp.json()
            gh_count = 0
            for repo in data.get("items", []):
                entries.append(make_entry(
                    source="GitHub",
                    title=repo.get("full_name", ""),
                    summary=repo.get("description", "")[:300],
                    url=repo.get("html_url", ""),
                    published=repo.get("pushed_at", TODAY),
                    lang="en", entry_type="repo",
                    meta={
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language", ""),
                    },
                ))
                gh_count += 1
            print(f"{gh_count} 个仓库（GitHub API）")
    except Exception as e:
        print(f"失败: {e}")

    # --- HuggingFace Trending ---
    print(f"  → HuggingFace...", end=" ")
    try:
        resp = httpx.get(
            "https://huggingface.co/api/trending",
            headers=HEADERS_BOT, timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            hf_count = 0
            for item in (data.get("recentlyTrending", []) or data if isinstance(data, list) else [])[:20]:
                repo_id = item.get("repoData", {}).get("id", "") if isinstance(item, dict) else ""
                if not repo_id and isinstance(item, dict):
                    repo_id = item.get("id", "")
                if repo_id:
                    entries.append(make_entry(
                        source="HuggingFace",
                        title=repo_id,
                        summary=f"HuggingFace trending model/dataset",
                        url=f"https://huggingface.co/{repo_id}",
                        published=TODAY,
                        lang="en", entry_type="model",
                        meta={"likes": item.get("likes", 0)},
                    ))
                    hf_count += 1
            print(f"{hf_count} 个模型")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    return entries


# ============================================================
#  第五部分：社交媒体热搜
#  微博、知乎、抖音、B站、小红书、Twitter/X
# ============================================================

def fetch_social_media():
    """抓取社交媒体热搜中的初创公司相关话题"""
    print("📡 [5/8] 抓取社交媒体热搜...")
    entries = []

    # --- 微博热搜 ---
    print(f"  → 微博热搜...", end=" ")
    try:
        resp = httpx.get(
            "https://weibo.com/ajax/side/hotSearch",
            headers={**HEADERS, "Referer": "https://weibo.com/"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            wb_count = 0
            for item in data.get("data", {}).get("realtime", []):
                word = item.get("word", "")
                if matches_keywords(word, "zh"):
                    entries.append(make_entry(
                        source="微博",
                        title=f"#{word}#",
                        summary=item.get("label_name", ""),
                        url=f"https://s.weibo.com/weibo?q=%23{word}%23",
                        published=TODAY,
                        meta={"hotValue": item.get("num", 0), "rank": item.get("rank", 0)},
                    ))
                    wb_count += 1
            print(f"{wb_count} 条")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    # --- 知乎热榜 ---
    print(f"  → 知乎热榜...", end=" ")
    try:
        resp = httpx.get(
            "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
            params={"limit": 50},
            headers={
                **HEADERS,
                "Referer": "https://www.zhihu.com/hot",
                "Cookie": os.getenv("ZHIHU_COOKIE", ""),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            zh_count = 0
            for item in data.get("data", []):
                target = item.get("target", {})
                title = target.get("title", "")
                excerpt = target.get("excerpt", "")
                if matches_keywords(title + " " + excerpt, "zh"):
                    entries.append(make_entry(
                        source="知乎",
                        title=title,
                        summary=excerpt,
                        url=f"https://www.zhihu.com/question/{target.get('id', '')}",
                        published=TODAY,
                        meta={
                            "hotValue": item.get("detail_text", ""),
                            "answerCount": target.get("answer_count", 0),
                            "followerCount": target.get("follower_count", 0),
                        },
                    ))
                    zh_count += 1
            print(f"{zh_count} 条")
        else:
            print(f"HTTP {resp.status_code}（可能需要 ZHIHU_COOKIE）")
    except Exception as e:
        print(f"失败: {e}")

    # --- 抖音热搜 ---
    print(f"  → 抖音热搜...", end=" ")
    try:
        resp = httpx.get(
            "https://www.douyin.com/aweme/v1/web/hot/search/list/",
            headers={**HEADERS, "Referer": "https://www.douyin.com/"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            dy_count = 0
            for item in data.get("data", {}).get("word_list", []):
                word = item.get("word", "")
                if matches_keywords(word, "zh"):
                    entries.append(make_entry(
                        source="抖音",
                        title=word,
                        summary=item.get("event_time", ""),
                        url=f"https://www.douyin.com/search/{word}",
                        published=TODAY,
                        meta={"hotValue": item.get("hot_value", 0)},
                    ))
                    dy_count += 1
            print(f"{dy_count} 条")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    # --- B站热搜 ---
    print(f"  → B站热搜...", end=" ")
    try:
        resp = httpx.get(
            "https://app.bilibili.com/x/v2/search/trending/ranking",
            headers=HEADERS, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            bili_count = 0
            for item in data.get("data", {}).get("list", []):
                keyword = item.get("keyword", "") or item.get("show_name", "")
                if matches_keywords(keyword, "zh"):
                    entries.append(make_entry(
                        source="B站",
                        title=keyword,
                        summary="",
                        url=f"https://search.bilibili.com/all?keyword={keyword}",
                        published=TODAY,
                        meta={"hotValue": item.get("hot_id", 0)},
                    ))
                    bili_count += 1
            print(f"{bili_count} 条")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    # --- 小红书（通过搜索建议间接获取热点） ---
    print(f"  → 小红书...", end=" ")
    try:
        # 小红书没有公开热搜 API，通过搜索建议接口探测
        xhs_keywords = ["AI创业", "初创公司", "融资", "创业项目"]
        xhs_count = 0
        for kw in xhs_keywords:
            resp = httpx.get(
                "https://edith.xiaohongshu.com/api/sns/web/v1/search/hot_list",
                headers={**HEADERS, "Referer": "https://www.xiaohongshu.com/"},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    title = item.get("title", "") or item.get("name", "")
                    if title and matches_keywords(title, "zh"):
                        entries.append(make_entry(
                            source="小红书",
                            title=title,
                            summary="",
                            url=f"https://www.xiaohongshu.com/search_result?keyword={title}",
                            published=TODAY,
                        ))
                        xhs_count += 1
            break  # 只请求一次热榜
        print(f"{xhs_count} 条")
    except Exception as e:
        print(f"失败: {e}")

    # --- Twitter/X Trending ---
    bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
    print(f"  → Twitter/X...", end=" ")
    if not bearer:
        print("跳过（需设置 TWITTER_BEARER_TOKEN）")
    else:
        try:
            # 搜索最近的初创公司相关推文
            resp = httpx.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params={
                    "query": "(startup OR funding OR \"series a\" OR launch) lang:en -is:retweet",
                    "max_results": 30,
                    "tweet.fields": "created_at,public_metrics,author_id",
                },
                headers={"Authorization": f"Bearer {bearer}"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                tw_count = 0
                for tweet in data.get("data", []):
                    metrics = tweet.get("public_metrics", {})
                    entries.append(make_entry(
                        source="Twitter",
                        title=tweet.get("text", "")[:140],
                        summary=tweet.get("text", ""),
                        url=f"https://twitter.com/i/web/status/{tweet['id']}",
                        published=tweet.get("created_at", TODAY),
                        lang="en", entry_type="social",
                        meta={
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                        },
                    ))
                    tw_count += 1
                print(f"{tw_count} 条")
            else:
                print(f"HTTP {resp.status_code}")
        except Exception as e:
            print(f"失败: {e}")

    print(f"  📊 社交媒体合计: {len(entries)} 条")
    return entries


# ============================================================
#  第六部分：垂直社区（雪球、V2EX）
# ============================================================

def fetch_vertical_communities():
    """抓取垂直社区的初创公司讨论"""
    print("📡 [6/8] 抓取垂直社区...")
    entries = []

    # --- 雪球（投资社区） ---
    print(f"  → 雪球...", end=" ")
    try:
        resp = httpx.get(
            "https://xueqiu.com/statuses/hot/listV2.json",
            params={"since_id": -1, "max_id": -1, "size": 30},
            headers={
                **HEADERS,
                "Referer": "https://xueqiu.com/",
                "Cookie": os.getenv("XUEQIU_COOKIE", "xq_a_token=placeholder;"),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            xq_count = 0
            for item in data.get("data", {}).get("items", []):
                original = item.get("original_status", {})
                title = original.get("title", "") or original.get("description", "")[:100]
                if matches_keywords(title, "zh"):
                    entries.append(make_entry(
                        source="雪球",
                        title=title,
                        summary=original.get("description", "")[:300],
                        url=f"https://xueqiu.com{original.get('target', '')}",
                        published=TODAY,
                        entry_type="community",
                        meta={
                            "replyCount": original.get("reply_count", 0),
                            "likeCount": original.get("like_count", 0),
                        },
                    ))
                    xq_count += 1
            print(f"{xq_count} 条")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    # --- V2EX（开发者社区） ---
    print(f"  → V2EX...", end=" ")
    try:
        resp = httpx.get(
            "https://www.v2ex.com/api/topics/hot.json",
            headers=HEADERS_BOT, timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            v2_count = 0
            for topic in data:
                title = topic.get("title", "")
                content = topic.get("content", "")
                if matches_keywords(title + " " + content, "zh"):
                    entries.append(make_entry(
                        source="V2EX",
                        title=title,
                        summary=content[:300],
                        url=f"https://www.v2ex.com/t/{topic.get('id', '')}",
                        published=topic.get("created", TODAY),
                        entry_type="community",
                        meta={
                            "replies": topic.get("replies", 0),
                            "node": topic.get("node", {}).get("title", ""),
                        },
                    ))
                    v2_count += 1
            print(f"{v2_count} 条")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    return entries


# ============================================================
#  第七部分：Crunchbase（海外创投数据库）
# ============================================================

def fetch_crunchbase():
    """Crunchbase - 全球创投数据库"""
    print("📡 [7/8] 抓取 Crunchbase...")
    entries = []

    api_key = os.getenv("CRUNCHBASE_API_KEY", "")
    print(f"  → Crunchbase...", end=" ")
    if not api_key:
        print("跳过（需设置 CRUNCHBASE_API_KEY）")
        return entries

    try:
        resp = httpx.get(
            "https://api.crunchbase.com/api/v4/searches/funding_rounds",
            params={
                "user_key": api_key,
                "field_ids": "identifier,announced_on,money_raised,funded_organization_identifier,investment_type",
                "order": "announced_on DESC",
                "limit": 30,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("entities", []):
                props = item.get("properties", {})
                org = props.get("funded_organization_identifier", {})
                entries.append(make_entry(
                    source="Crunchbase",
                    title=f"{org.get('value', 'Unknown')} - {props.get('investment_type', '')}",
                    summary=f"Raised {props.get('money_raised', {}).get('value_usd', 'N/A')} USD",
                    url=f"https://www.crunchbase.com/funding_round/{item.get('identifier', {}).get('permalink', '')}",
                    published=props.get("announced_on", TODAY),
                    lang="en", entry_type="funding",
                    meta={
                        "amount_usd": props.get("money_raised", {}).get("value_usd"),
                        "round": props.get("investment_type"),
                    },
                ))
            print(f"{len(entries)} 条融资")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    return entries


# ============================================================
#  第八部分：EarlyFinder 风格 - 增长信号探测
#  通过 GitHub 新星 + Twitter 提及量 + 网站流量变化来发现早期项目
# ============================================================

def fetch_growth_signals():
    """探测增长信号：近期 star 暴涨的 GitHub 项目"""
    print("📡 [8/8] 探测增长信号...")
    entries = []

    print(f"  → GitHub 新星项目（近7天 star 暴涨）...", end=" ")
    try:
        from datetime import timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        resp = httpx.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"created:>{week_ago} stars:>50",
                "sort": "stars", "order": "desc", "per_page": 20,
            },
            headers={
                **HEADERS_BOT,
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            gs_count = 0
            for repo in data.get("items", []):
                entries.append(make_entry(
                    source="GitHub新星",
                    title=repo.get("full_name", ""),
                    summary=repo.get("description", "")[:300],
                    url=repo.get("html_url", ""),
                    published=repo.get("created_at", TODAY),
                    lang="en", entry_type="signal",
                    meta={
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language", ""),
                        "createdDaysAgo": (datetime.now() - datetime.fromisoformat(
                            repo.get("created_at", TODAY).replace("Z", "+00:00")
                        ).replace(tzinfo=None)).days if repo.get("created_at") else 0,
                    },
                ))
                gs_count += 1
            print(f"{gs_count} 个")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"失败: {e}")

    return entries


# ============================================================
#  主流程
# ============================================================

def save_raw(data, filename):
    """保存原始数据"""
    filepath = RAW_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存: {filepath} ({len(data)} 条)")


def main():
    print(f"{'='*60}")
    print(f"  StartupRadar 全渠道数据抓取 - {TODAY}")
    print(f"{'='*60}\n")

    all_raw = []

    # 1. 创投媒体 RSS（10 个源）
    all_raw.extend(fetch_rss_feeds())

    # 2. 创投数据平台（IT 桔子、鲸准）
    all_raw.extend(fetch_itjuzi())

    # 3. 产品发现平台（Product Hunt、Indie Hackers）
    all_raw.extend(fetch_product_hunt())

    # 4. 开源社区（GitHub Trending、HuggingFace）
    all_raw.extend(fetch_opensource())

    # 5. 社交媒体热搜（微博、知乎、抖音、B站、小红书、Twitter）
    all_raw.extend(fetch_social_media())

    # 6. 垂直社区（雪球、V2EX）
    all_raw.extend(fetch_vertical_communities())

    # 7. Crunchbase（海外创投数据库）
    all_raw.extend(fetch_crunchbase())

    # 8. 增长信号探测（GitHub 新星）
    all_raw.extend(fetch_growth_signals())

    # ── 去重（按 URL） ──
    seen = set()
    deduped = []
    for item in all_raw:
        key = item.get("url", "") or hashlib.md5(item["title"].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # ── 保存 ──
    save_raw(deduped, f"{TODAY}-raw.json")

    # ── 统计 ──
    print(f"\n{'='*60}")
    print(f"  抓取完成！")
    print(f"{'='*60}")
    print(f"  原始数据: {len(all_raw)} 条")
    print(f"  去重后:   {len(deduped)} 条")
    print(f"\n  按来源统计:")
    source_counts = {}
    for item in deduped:
        src = item["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"    {src:15s} {count:4d} 条")

    return 0


if __name__ == "__main__":
    sys.exit(main())
