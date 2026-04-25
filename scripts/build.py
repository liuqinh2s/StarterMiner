#!/usr/bin/env python3
"""
构建脚本：将报告数据整理到 site/data/ 目录，生成索引文件。
供静态网站前端读取。
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "reports"
SITE_DATA_DIR = Path(__file__).parent.parent / "site" / "data"

TODAY = datetime.now().strftime("%Y-%m-%d")


def main():
    print(f"{'='*50}")
    print(f"StartupRadar 构建网站数据 - {TODAY}")
    print(f"{'='*50}\n")

    # 确保目录存在
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 找到所有报告
    report_files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    if not report_files:
        print("⚠️ 没有报告数据，生成空索引")
        write_empty_index()
        return 0

    print(f"📂 找到 {len(report_files)} 份报告")

    # 使用最新报告作为主数据
    latest = report_files[0]
    print(f"📄 最新报告: {latest.name}")

    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)

    projects = data.get("projects", [])
    discussions = data.get("discussions", [])

    print(f"   → {len(projects)} 个项目, {len(discussions)} 条讨论")

    # 1. 写入项目数据（按日期分文件，便于增量更新）
    projects_file = f"projects-{latest.stem}.json"
    projects_path = SITE_DATA_DIR / projects_file
    with open(projects_path, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, ensure_ascii=False, indent=2)
    print(f"💾 项目数据: {projects_path}")

    # 同时写一份 latest 用于快速访问
    latest_projects_path = SITE_DATA_DIR / "projects-latest.json"
    with open(latest_projects_path, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, ensure_ascii=False, indent=2)

    # 2. 写入讨论数据
    discussions_file = f"discussions-{latest.stem}.json"
    discussions_path = SITE_DATA_DIR / discussions_file
    with open(discussions_path, "w", encoding="utf-8") as f:
        json.dump({"discussions": discussions}, f, ensure_ascii=False, indent=2)
    print(f"💾 讨论数据: {discussions_path}")

    latest_discussions_path = SITE_DATA_DIR / "discussions-latest.json"
    with open(latest_discussions_path, "w", encoding="utf-8") as f:
        json.dump({"discussions": discussions}, f, ensure_ascii=False, indent=2)

    # 3. 生成项目索引
    all_project_files = sorted(SITE_DATA_DIR.glob("projects-2*.json"), reverse=True)
    projects_index = {
        "lastUpdate": latest.stem,
        "totalProjects": len(projects),
        "files": [f.name for f in all_project_files],
        "generatedAt": datetime.now().isoformat(),
    }
    index_path = SITE_DATA_DIR / "projects-index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(projects_index, f, ensure_ascii=False, indent=2)
    print(f"💾 项目索引: {index_path}")

    # 4. 生成讨论索引
    all_disc_files = sorted(SITE_DATA_DIR.glob("discussions-2*.json"), reverse=True)
    discussions_index = {
        "lastUpdate": latest.stem,
        "totalDiscussions": len(discussions),
        "files": [f.name for f in all_disc_files],
        "generatedAt": datetime.now().isoformat(),
    }
    disc_index_path = SITE_DATA_DIR / "discussions-index.json"
    with open(disc_index_path, "w", encoding="utf-8") as f:
        json.dump(discussions_index, f, ensure_ascii=False, indent=2)
    print(f"💾 讨论索引: {disc_index_path}")

    # 5. 生成统计摘要（可选，用于首页展示）
    tracks = {}
    stages = {}
    cities = {}
    for p in projects:
        tracks[p.get("track", "other")] = tracks.get(p.get("track", "other"), 0) + 1
        stages[p.get("stage", "unknown")] = stages.get(p.get("stage", "unknown"), 0) + 1
        cities[p.get("city", "other")] = cities.get(p.get("city", "other"), 0) + 1

    summary = {
        "totalProjects": len(projects),
        "totalDiscussions": len(discussions),
        "byTrack": tracks,
        "byStage": stages,
        "byCity": cities,
        "avgScore": round(sum(p.get("score", 50) for p in projects) / max(len(projects), 1), 1),
        "lastUpdate": latest.stem,
    }
    summary_path = SITE_DATA_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"💾 统计摘要: {summary_path}")

    print(f"\n✅ 构建完成！网站数据已更新到 site/data/")
    return 0


def write_empty_index():
    """生成空索引"""
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for name in ["projects-index.json", "discussions-index.json"]:
        path = SITE_DATA_DIR / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "lastUpdate": None,
                "files": [],
                "generatedAt": datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)

    summary_path = SITE_DATA_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "totalProjects": 0,
            "totalDiscussions": 0,
            "lastUpdate": None,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
