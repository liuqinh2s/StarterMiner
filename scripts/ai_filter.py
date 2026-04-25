#!/usr/bin/env python3
"""
AI 筛选脚本：读取原始抓取数据，通过大模型识别初创公司信息，
生成结构化的项目数据和讨论数据。

支持的 AI 后端：
  - 智谱 AI (GLM-4-Plus) — 默认
  - OpenAI (GPT-4o)
  - DeepSeek
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 加载 .env 文件中的环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# ========== 配置 ==========
RAW_DIR = Path(__file__).parent.parent / "raw"
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")

def _is_real_key(env_var):
    """判断环境变量是否填了真实的 API Key（排除占位符）"""
    val = os.getenv(env_var, "").strip()
    if not val:
        return False
    # 排除 .env.example 中的占位符
    placeholders = ("your_", "sk-xxx", "xxx", "placeholder", "填入", "替换")
    return not any(val.lower().startswith(p) for p in placeholders)


# AI 模型配置（填了哪个 key 就用哪个）
def get_ai_client():
    """根据环境变量选择 AI 后端"""
    if _is_real_key("ZHIPU_API_KEY"):
        return OpenAI(
            api_key=os.getenv("ZHIPU_API_KEY").strip(),
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        ), "glm-4-plus"
    elif _is_real_key("DEEPSEEK_API_KEY"):
        return OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY").strip(),
            base_url="https://api.deepseek.com"
        ), "deepseek-v4-flash"
    elif _is_real_key("OPENAI_API_KEY"):
        return OpenAI(api_key=os.getenv("OPENAI_API_KEY").strip()), "gpt-4o"
    else:
        print("❌ 未配置 AI API Key。请设置 ZHIPU_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY")
        sys.exit(1)


# ========== 加载提示词 ==========
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def _load_prompt(name):
    """从 prompts/ 目录读取提示词文件"""
    filepath = PROMPTS_DIR / name
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

EXTRACT_PROMPT = _load_prompt("extract.md")
MERGE_PROMPT = _load_prompt("merge.md")


def load_raw_data():
    """加载今日原始数据"""
    filepath = RAW_DIR / f"{TODAY}-raw.json"
    if not filepath.exists():
        # 尝试找最近的
        files = sorted(RAW_DIR.glob("*-raw.json"), reverse=True)
        if files:
            filepath = files[0]
            print(f"⚠️ 未找到今日数据，使用最近的: {filepath.name}")
        else:
            print("❌ 没有原始数据可处理")
            return []

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_existing_report():
    """加载最近的报告（用于合并）"""
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    for f in files:
        if f.name != f"{TODAY}.json":
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                continue
    return {"projects": [], "discussions": []}


def chunk_data(data, chunk_size=10):
    """将数据分块，避免超出 token 限制"""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def ai_extract(client, model, raw_items):
    """调用 AI 提取结构化数据"""
    content = EXTRACT_PROMPT + json.dumps(raw_items, ensure_ascii=False, indent=2)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是初创公司分析专家，只返回 JSON 数据。"},
                {"role": "user", "content": content},
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️ AI 提取失败: {e}")
        return {"projects": [], "discussions": []}


def ai_merge(client, model, existing, new_data):
    """调用 AI 合并数据"""
    content = MERGE_PROMPT.format(
        existing=json.dumps(existing, ensure_ascii=False),
        new_data=json.dumps(new_data, ensure_ascii=False),
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是数据合并专家，只返回 JSON 数据。"},
                {"role": "user", "content": content},
            ],
            temperature=0.1,
            max_tokens=8000,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠️ AI 合并失败: {e}")
        # 简单合并
        return simple_merge(existing, new_data)


def simple_merge(existing, new_data):
    """简单合并（AI 失败时的降级方案）"""
    existing_ids = {p["id"] for p in existing.get("projects", [])}
    merged_projects = list(existing.get("projects", []))

    for p in new_data.get("projects", []):
        if p["id"] not in existing_ids:
            merged_projects.append(p)

    existing_urls = {d.get("url") for d in existing.get("discussions", [])}
    merged_discussions = list(existing.get("discussions", []))

    for d in new_data.get("discussions", []):
        if d.get("url") not in existing_urls:
            merged_discussions.append(d)

    return {"projects": merged_projects, "discussions": merged_discussions}


def compute_total_score(scores):
    """计算综合评分"""
    if not scores:
        return 50
    weights = {"tech": 0.3, "growth": 0.3, "team": 0.2, "market": 0.2}
    total = sum(scores.get(k, 50) * w for k, w in weights.items())
    return round(total)


def main():
    print(f"{'='*50}")
    print(f"StartupRadar AI 筛选 - {TODAY}")
    print(f"{'='*50}\n")

    # 1. 加载数据
    raw_data = load_raw_data()
    if not raw_data:
        return 1

    print(f"📊 原始数据: {len(raw_data)} 条\n")

    # 2. 初始化 AI
    client, model = get_ai_client()
    print(f"🤖 AI 后端: {model}\n")

    # 3. 分块提取
    all_projects = []
    all_discussions = []

    for i, chunk in enumerate(chunk_data(raw_data, 10)):
        print(f"🔍 处理第 {i+1} 批 ({len(chunk)} 条)...", end=" ")
        result = ai_extract(client, model, chunk)
        projects = result.get("projects", [])
        discussions = result.get("discussions", [])
        all_projects.extend(projects)
        all_discussions.extend(discussions)
        print(f"→ {len(projects)} 个项目, {len(discussions)} 条讨论")

    new_data = {"projects": all_projects, "discussions": all_discussions}
    print(f"\n📊 本次提取: {len(all_projects)} 个项目, {len(all_discussions)} 条讨论")

    # 4. 与历史数据合并
    existing = load_existing_report()
    if existing["projects"]:
        print(f"📂 历史数据: {len(existing['projects'])} 个项目")
        print("🔄 合并数据...")
        merged = ai_merge(client, model, existing, new_data)
    else:
        merged = new_data

    # 5. 计算综合评分
    for p in merged.get("projects", []):
        p["score"] = compute_total_score(p.get("scores", {}))
        p["discoveredAt"] = p.get("discoveredAt", TODAY)
        p["discussionCount"] = len([
            d for d in merged.get("discussions", [])
            if d.get("relatedProject") == p.get("id")
        ])

    # 6. 保存报告
    report_path = REPORTS_DIR / f"{TODAY}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n💾 报告已保存: {report_path}")
    print(f"✅ 最终数据: {len(merged.get('projects', []))} 个项目, {len(merged.get('discussions', []))} 条讨论")
    return 0


if __name__ == "__main__":
    sys.exit(main())
