#!/usr/bin/env python3
"""
一键生成报告：依次调用 fetch_startups + ai_filter + build
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script_name):
    """运行脚本"""
    script = SCRIPTS_DIR / script_name
    print(f"\n{'='*60}")
    print(f"▶ 运行: {script_name}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(SCRIPTS_DIR.parent),
    )
    return result.returncode


def main():
    # 1. 抓取数据
    code = run("fetch_startups.py")
    if code != 0:
        print("⚠️ 抓取脚本返回非零，继续尝试...")

    # 2. AI 筛选
    code = run("ai_filter.py")
    if code != 0:
        print("❌ AI 筛选失败")
        return code

    # 3. 补全招聘与联系方式
    code = run("fetch_contacts.py")
    if code != 0:
        print("⚠️ 联系方式抓取返回非零，继续...")

    # 4. 构建网站
    code = run("build.py")
    if code != 0:
        print("❌ 构建失败")
        return code

    print(f"\n{'='*60}")
    print("✅ 全部完成！")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
