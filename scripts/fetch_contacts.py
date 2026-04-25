#!/usr/bin/env python3
"""
StartupRadar 招聘与联系方式抓取脚本

针对已发现的初创公司，从多渠道补全招聘信息和联系方式：

  ── 招聘平台 ──
  1. Boss直聘     - 搜索公司名，获取在招职位
  2. 拉勾         - 搜索公司名，获取在招职位
  3. 猎聘         - 搜索公司名

  ── 公司官网 ──
  4. 官网 /careers、/jobs、/join 页面
  5. 官网 /about、/contact 页面（邮箱、社交账号）

  ── 开发者平台 ──
  6. GitHub       - org 成员公开 profile（邮箱、Twitter、博客）
  7. LinkedIn     - 公司页（公开信息）

  ── 工商信息 ──
  8. 天眼查/企查查 - 法人、注册邮箱、电话（公开工商数据）

运行方式：
  python scripts/fetch_contacts.py
  或在 ai_filter.py 之后自动调用
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

import httpx

# ========== 配置 ==========
REPORTS_DIR = Path(__file__).parent.parent / "reports"
RAW_DIR = Path(__file__).parent.parent / "raw"
RAW_DIR.mkdir(exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# 邮箱正则
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

# 社交账号正则
SOCIAL_PATTERNS = {
    "twitter": re.compile(r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]{1,15})", re.I),
    "linkedin": re.compile(r"linkedin\.com/(?:in|company)/([a-zA-Z0-9\-]+)", re.I),
    "github": re.compile(r"github\.com/([a-zA-Z0-9\-]+)", re.I),
    "wechat": re.compile(r"(?:微信|wechat)[：:\s]*([a-zA-Z0-9_\-]+)", re.I),
}

# 招聘页面路径关键词
CAREER_PATHS = [
    "/careers", "/jobs", "/join", "/join-us", "/hiring",
    "/career", "/work-with-us", "/positions", "/opportunities",
    "/zh/careers", "/en/careers",
]

CONTACT_PATHS = [
    "/about", "/about-us", "/contact", "/contact-us",
    "/team", "/zh/about", "/en/about",
]


# ============================================================
#  1. 公司官网：招聘页 + 联系页
# ============================================================

def fetch_website_info(company_name, website_url):
    """从公司官网抓取招聘信息和联系方式"""
    if not website_url:
        return {}

    result = {
        "website": website_url,
        "emails": [],
        "socials": {},
        "careerPage": None,
        "jobListings": [],
    }

    parsed = urlparse(website_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # --- 抓取招聘页 ---
    for path in CAREER_PATHS:
        try:
            url = base_url + path
            resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 500:
                result["careerPage"] = url
                # 提取职位信息（简单的文本匹配）
                text = resp.text
                # 常见职位关键词
                job_keywords = [
                    "工程师", "开发", "产品", "设计", "运营", "市场",
                    "Engineer", "Developer", "Product", "Design", "Marketing",
                    "Backend", "Frontend", "Full Stack", "Data", "AI", "ML",
                    "算法", "研究员", "架构师", "总监",
                ]
                for kw in job_keywords:
                    # 找包含关键词的行
                    for line in text.split("\n"):
                        clean = re.sub(r"<[^>]+>", "", line).strip()
                        if kw in clean and 5 < len(clean) < 100:
                            if clean not in result["jobListings"]:
                                result["jobListings"].append(clean)
                result["jobListings"] = result["jobListings"][:20]  # 限制数量
                break
        except Exception:
            continue

    # --- 抓取联系页 ---
    pages_to_scan = [website_url] + [base_url + p for p in CONTACT_PATHS]
    for url in pages_to_scan[:5]:  # 最多扫 5 个页面
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
            if resp.status_code != 200:
                continue
            text = resp.text

            # 提取邮箱
            emails = EMAIL_RE.findall(text)
            for email in emails:
                # 过滤掉图片和常见无效邮箱
                if any(x in email.lower() for x in [".png", ".jpg", ".svg", "example.com", "sentry"]):
                    continue
                if email not in result["emails"]:
                    result["emails"].append(email)

            # 提取社交账号
            for platform, pattern in SOCIAL_PATTERNS.items():
                matches = pattern.findall(text)
                if matches and platform not in result["socials"]:
                    result["socials"][platform] = matches[0]

        except Exception:
            continue

    result["emails"] = result["emails"][:10]  # 限制数量
    return result


# ============================================================
#  2. GitHub：组织成员公开信息
# ============================================================

def fetch_github_contacts(github_url):
    """从 GitHub 获取组织/项目成员的公开联系信息"""
    if not github_url:
        return {}

    result = {"members": [], "orgEmail": None}

    # 解析 GitHub URL
    match = re.search(r"github\.com/([a-zA-Z0-9\-]+)(?:/([a-zA-Z0-9\-_.]+))?", github_url)
    if not match:
        return result

    owner = match.group(1)
    gh_headers = {
        **HEADERS,
        "Accept": "application/vnd.github.v3+json",
    }
    gh_token = os.getenv("GITHUB_TOKEN", "")
    if gh_token:
        gh_headers["Authorization"] = f"token {gh_token}"

    try:
        # 先尝试作为 org 获取成员
        resp = httpx.get(
            f"https://api.github.com/orgs/{owner}/members",
            params={"per_page": 10},
            headers=gh_headers, timeout=10,
        )

        members_data = []
        if resp.status_code == 200:
            members_data = resp.json()
        else:
            # 不是 org，尝试获取 repo 贡献者
            repo = match.group(2)
            if repo:
                resp = httpx.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contributors",
                    params={"per_page": 5},
                    headers=gh_headers, timeout=10,
                )
                if resp.status_code == 200:
                    members_data = resp.json()

        # 获取每个成员的详细信息
        for member in members_data[:5]:
            login = member.get("login", "")
            if not login:
                continue
            try:
                user_resp = httpx.get(
                    f"https://api.github.com/users/{login}",
                    headers=gh_headers, timeout=10,
                )
                if user_resp.status_code == 200:
                    user = user_resp.json()
                    member_info = {
                        "name": user.get("name") or login,
                        "github": f"https://github.com/{login}",
                        "email": user.get("email"),
                        "twitter": user.get("twitter_username"),
                        "blog": user.get("blog"),
                        "bio": user.get("bio"),
                        "company": user.get("company"),
                        "location": user.get("location"),
                    }
                    # 清理空值
                    member_info = {k: v for k, v in member_info.items() if v}
                    result["members"].append(member_info)
            except Exception:
                continue

        # 获取 org 信息
        resp = httpx.get(
            f"https://api.github.com/orgs/{owner}",
            headers=gh_headers, timeout=10,
        )
        if resp.status_code == 200:
            org = resp.json()
            result["orgEmail"] = org.get("email")
            if org.get("blog"):
                result["orgBlog"] = org["blog"]
            if org.get("twitter_username"):
                result["orgTwitter"] = org["twitter_username"]

    except Exception:
        pass

    return result


# ============================================================
#  3. 招聘平台：Boss直聘、拉勾
# ============================================================

def fetch_boss_zhipin(company_name):
    """Boss直聘 - 搜索公司在招职位"""
    result = {"platform": "Boss直聘", "jobs": [], "companyUrl": None}

    try:
        resp = httpx.get(
            "https://www.zhipin.com/wapi/zpCommon/search/company",
            params={"query": company_name, "page": 1, "pageSize": 5},
            headers={
                **HEADERS,
                "Referer": "https://www.zhipin.com/",
                "Cookie": os.getenv("BOSS_COOKIE", ""),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            companies = data.get("zpData", {}).get("companyList", [])
            if companies:
                company = companies[0]
                result["companyUrl"] = f"https://www.zhipin.com/gongsi/{company.get('encryptBrandId', '')}.html"
                result["companyInfo"] = {
                    "name": company.get("brandName", ""),
                    "industry": company.get("industryName", ""),
                    "scale": company.get("scaleName", ""),
                    "stage": company.get("stageName", ""),
                    "city": company.get("cityName", ""),
                }

                # 获取在招职位
                enc_id = company.get("encryptBrandId", "")
                if enc_id:
                    job_resp = httpx.get(
                        f"https://www.zhipin.com/wapi/zpCommon/search/jobList",
                        params={"encryptBrandId": enc_id, "page": 1, "pageSize": 10},
                        headers={
                            **HEADERS,
                            "Referer": "https://www.zhipin.com/",
                            "Cookie": os.getenv("BOSS_COOKIE", ""),
                        },
                        timeout=10,
                    )
                    if job_resp.status_code == 200:
                        job_data = job_resp.json()
                        for job in job_data.get("zpData", {}).get("jobList", []):
                            result["jobs"].append({
                                "title": job.get("jobName", ""),
                                "salary": job.get("salaryDesc", ""),
                                "city": job.get("cityName", ""),
                                "experience": job.get("jobExperience", ""),
                                "education": job.get("jobDegree", ""),
                                "url": f"https://www.zhipin.com/job_detail/{job.get('encryptJobId', '')}.html",
                            })
    except Exception:
        pass

    return result


def fetch_lagou(company_name):
    """拉勾 - 搜索公司在招职位"""
    result = {"platform": "拉勾", "jobs": [], "companyUrl": None}

    try:
        resp = httpx.post(
            "https://www.lagou.com/jobs/positionAjax.json",
            params={"needAddtionalResult": "false"},
            data={
                "first": "true",
                "pn": 1,
                "kd": company_name,
            },
            headers={
                **HEADERS,
                "Referer": "https://www.lagou.com/",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": os.getenv("LAGOU_COOKIE", ""),
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            positions = data.get("content", {}).get("positionResult", {}).get("result", [])
            for pos in positions[:10]:
                if company_name.lower() in pos.get("companyFullName", "").lower() or \
                   company_name.lower() in pos.get("companyShortName", "").lower():
                    result["jobs"].append({
                        "title": pos.get("positionName", ""),
                        "salary": pos.get("salary", ""),
                        "city": pos.get("city", ""),
                        "experience": pos.get("workYear", ""),
                        "education": pos.get("education", ""),
                        "advantage": pos.get("positionAdvantage", ""),
                    })
                    if not result["companyUrl"]:
                        result["companyUrl"] = f"https://www.lagou.com/gongsi/{pos.get('companyId', '')}.html"
    except Exception:
        pass

    return result


# ============================================================
#  4. 工商信息：天眼查（公开数据）
# ============================================================

def fetch_tianyancha(company_name):
    """天眼查 - 获取公开工商信息"""
    result = {"legalPerson": None, "regEmail": None, "regPhone": None, "url": None}

    token = os.getenv("TIANYANCHA_TOKEN", "")
    if not token:
        return result

    try:
        resp = httpx.get(
            "https://open.api.tianyancha.com/services/open/search/2.0",
            params={"word": company_name, "pageSize": 1, "pageNum": 1},
            headers={"Authorization": token},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("result", {}).get("items", [])
            if items:
                company = items[0]
                result["legalPerson"] = company.get("legalPersonName")
                result["regEmail"] = company.get("email")
                result["regPhone"] = company.get("phoneNumber")
                result["url"] = f"https://www.tianyancha.com/company/{company.get('id', '')}"
                result["regCapital"] = company.get("regCapital")
                result["establishDate"] = company.get("estiblishTime")
    except Exception:
        pass

    return result


# ============================================================
#  主流程：为已发现的项目补全联系信息
# ============================================================

def load_latest_report():
    """加载最新报告"""
    files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
    if not files:
        return None
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f), files[0]


def enrich_project(project):
    """为单个项目补全招聘和联系信息"""
    name = project.get("name", "")
    product_url = project.get("product", "")
    github_url = ""

    # 从 tags 或 meta 中找 GitHub 链接
    for tag in project.get("tags", []):
        if "github.com" in tag.lower():
            github_url = tag

    print(f"\n  🔍 {name}")
    contacts = {
        "fetchedAt": TODAY,
        "website": {},
        "github": {},
        "hiring": [],
        "businessInfo": {},
    }

    # 1. 官网信息
    if product_url:
        print(f"    → 官网...", end=" ")
        website_info = fetch_website_info(name, product_url)
        contacts["website"] = website_info
        email_count = len(website_info.get("emails", []))
        job_count = len(website_info.get("jobListings", []))
        career = "✓" if website_info.get("careerPage") else "✗"
        print(f"邮箱 {email_count} 个, 招聘页 {career}, 职位 {job_count} 个")

    # 2. GitHub 信息
    if github_url:
        print(f"    → GitHub...", end=" ")
        gh_info = fetch_github_contacts(github_url)
        contacts["github"] = gh_info
        print(f"成员 {len(gh_info.get('members', []))} 人")

    # 3. 招聘平台
    boss_cookie = os.getenv("BOSS_COOKIE", "")
    if boss_cookie:
        print(f"    → Boss直聘...", end=" ")
        boss = fetch_boss_zhipin(name)
        if boss["jobs"]:
            contacts["hiring"].append(boss)
            print(f"{len(boss['jobs'])} 个职位")
        else:
            print("未找到")

    lagou_cookie = os.getenv("LAGOU_COOKIE", "")
    if lagou_cookie:
        print(f"    → 拉勾...", end=" ")
        lagou = fetch_lagou(name)
        if lagou["jobs"]:
            contacts["hiring"].append(lagou)
            print(f"{len(lagou['jobs'])} 个职位")
        else:
            print("未找到")

    # 4. 工商信息
    tyc_token = os.getenv("TIANYANCHA_TOKEN", "")
    if tyc_token:
        print(f"    → 天眼查...", end=" ")
        biz = fetch_tianyancha(name)
        contacts["businessInfo"] = biz
        print(f"法人: {biz.get('legalPerson', '未知')}")

    return contacts


def main():
    print(f"{'='*60}")
    print(f"  StartupRadar 招聘与联系方式抓取 - {TODAY}")
    print(f"{'='*60}")

    result = load_latest_report()
    if not result:
        print("❌ 没有报告数据，请先运行 ai_filter.py")
        return 1

    report, report_path = result
    projects = report.get("projects", [])
    print(f"\n📂 报告: {report_path.name} ({len(projects)} 个项目)")

    # 为每个项目补全联系信息
    for project in projects:
        contacts = enrich_project(project)
        project["contacts"] = contacts

    # 汇总统计
    stats = {
        "withEmail": 0,
        "withCareerPage": 0,
        "withJobs": 0,
        "withGithubMembers": 0,
        "totalJobs": 0,
    }
    for p in projects:
        c = p.get("contacts", {})
        if c.get("website", {}).get("emails"):
            stats["withEmail"] += 1
        if c.get("website", {}).get("careerPage"):
            stats["withCareerPage"] += 1
        hiring = c.get("hiring", [])
        job_count = sum(len(h.get("jobs", [])) for h in hiring)
        if job_count > 0:
            stats["withJobs"] += 1
            stats["totalJobs"] += job_count
        if c.get("github", {}).get("members"):
            stats["withGithubMembers"] += 1

    # 保存更新后的报告
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 同时保存一份独立的联系信息文件
    contacts_data = []
    for p in projects:
        contacts_data.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "contacts": p.get("contacts", {}),
        })
    contacts_path = RAW_DIR / f"{TODAY}-contacts.json"
    with open(contacts_path, "w", encoding="utf-8") as f:
        json.dump(contacts_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  抓取完成！")
    print(f"{'='*60}")
    print(f"  有邮箱的项目:     {stats['withEmail']}/{len(projects)}")
    print(f"  有招聘页的项目:   {stats['withCareerPage']}/{len(projects)}")
    print(f"  有在招职位的项目: {stats['withJobs']}/{len(projects)} (共 {stats['totalJobs']} 个职位)")
    print(f"  有 GitHub 成员:   {stats['withGithubMembers']}/{len(projects)}")
    print(f"\n💾 报告已更新: {report_path}")
    print(f"💾 联系信息: {contacts_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
