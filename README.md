# 🚀 StartupRadar - 初创公司发现平台

AI 驱动的初创公司/团队发现平台。自动从全网抓取初创公司信息，通过 AI 大模型分析评分，生成每日报告并发布为静态网站。

## 在线访问

部署后通过 GitHub Pages 访问：`https://<username>.github.io/startup-radar/`

## 工作原理

1. **GitHub Actions** 定时任务（北京时间每天 8:00 / 20:00）触发
2. `scripts/fetch_startups.py` 从 RSS 源、Product Hunt、GitHub Trending 等渠道抓取数据
3. `scripts/ai_filter.py` 通过 AI 大模型识别初创公司，生成结构化数据和增长评分
4. `scripts/build.py` 将数据整理到 `site/data/`，生成索引
5. **GitHub Pages** 自动部署 `site/` 目录

## 数据源（22 个渠道）

**创投媒体 RSS（10 源）：** 36氪、虎嗅、少数派、铅笔道、创业邦、投资界、TechCrunch、TechNode、The Verge、Hacker News

**创投数据平台：** IT 桔子（每日新收录）、鲸准（36氪旗下）、Crunchbase（全球融资数据库）

**产品发现平台：** Product Hunt（全球首发）、Indie Hackers（独立开发者）

**开源社区：** GitHub Trending、GitHub 新星（7 天内 star 暴涨）、HuggingFace Trending

**社交媒体热搜：** 微博热搜、知乎热榜、抖音热搜、B站热搜、小红书、Twitter/X

**垂直社区：** 雪球（投资社区）、V2EX（开发者社区）

## 核心功能

- **项目库**：展示初创公司/团队，支持按赛道、阶段、城市筛选
- **增长评分**：AI 从技术实力、增长速度、团队背景、市场前景四个维度打分
- **全网讨论**：自动聚合知乎、微博、36氪、Twitter 等平台的相关讨论
- **项目详情**：团队信息、融资情况、产品链接、评分明细

## 项目结构

```
├── .github/workflows/
│   └── daily-report.yml        # GitHub Actions 定时任务
├── raw/                         # 原始抓取数据
├── reports/                     # AI 生成的结构化报告（JSON）
├── scripts/
│   ├── fetch_startups.py        # 数据抓取脚本
│   ├── ai_filter.py             # AI 筛选与评分脚本
│   ├── build.py                 # 构建网站数据
│   └── generate_report.py       # 一键生成（抓取 + 筛选 + 构建）
├── site/                        # 静态网站（部署到 GitHub Pages）
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/                    # 构建后的数据文件
│       ├── projects-index.json
│       ├── discussions-index.json
│       └── *.json
├── package.json
├── requirements.txt
└── .env.example
```

## 前端特性

- 移动端优先适配
- 热门项目卡片展示 + 增长评分
- 多维度筛选（赛道、阶段、城市、排序）
- 项目详情弹窗（团队、评分、讨论）
- 全网讨论聚合
- 亮色/暗色主题切换，自动记忆偏好
- 每 60 秒自动检测数据更新

## 本地开发

### 环境准备

```bash
# 安装 Python 依赖
pip3 install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key
```

### 运行

```bash
# 一键生成报告（抓取 + AI 筛选 + 构建）
python3 scripts/generate_report.py

# 或分步执行：
python3 scripts/fetch_startups.py   # 1. 抓取数据
python3 scripts/ai_filter.py        # 2. AI 筛选
python3 scripts/build.py            # 3. 构建网站

# 本地预览
python3 -m http.server 8080 -d site
# 或
npm install && npm run dev
```

## GitHub Secrets 配置

在仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 | 必需 |
|--------|------|------|
| `ZHIPU_API_KEY` | 智谱 AI API 密钥 | 三选一 |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 三选一 |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 三选一 |
| `PH_TOKEN` | Product Hunt API Token | 可选 |
| `ITJUZI_COOKIE` | IT 桔子登录 Cookie | 可选 |
| `JINGDATA_TOKEN` | 鲸准 API Token | 可选 |
| `CRUNCHBASE_API_KEY` | Crunchbase API Key | 可选 |
| `ZHIHU_COOKIE` | 知乎登录 Cookie | 可选 |
| `TWITTER_BEARER_TOKEN` | Twitter API Bearer Token | 可选 |
| `XUEQIU_COOKIE` | 雪球登录 Cookie | 可选 |

## 技术栈

- **Python 3.11** + feedparser + httpx + openai SDK
- **AI 后端**：智谱 GLM-4-Plus / DeepSeek / GPT-4o（三选一）
- **GitHub Actions**（定时任务）
- **GitHub Pages**（静态网站托管）
- **原生 HTML/CSS/JS**（前端，无框架依赖）

## 评分标准

| 维度 | 权重 | 说明 |
|------|------|------|
| 技术实力 (tech) | 30% | 技术壁垒、创新性、开源贡献、论文发表 |
| 增长速度 (growth) | 30% | 用户增长、社区活跃度、媒体曝光 |
| 团队背景 (team) | 20% | 创始人履历、核心团队、顾问阵容 |
| 市场前景 (market) | 20% | 市场规模、竞争格局、时机判断 |
