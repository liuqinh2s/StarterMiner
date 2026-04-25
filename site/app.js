/**
 * StartupRadar - 初创公司发现平台
 * 纯静态前端，从 data/ 目录加载 JSON 数据
 */

(function () {
  'use strict';

  // ========== 状态 ==========
  const state = {
    projects: [],
    discussions: [],
    filters: { track: '', stage: '', city: '', sort: 'score' },
    page: 1,
    pageSize: 15,
    lastDataHash: '',
  };

  // ========== 工具函数 ==========
  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return document.querySelectorAll(sel); }

  function scoreClass(score) {
    if (score >= 75) return 'score-high';
    if (score >= 50) return 'score-mid';
    return 'score-low';
  }

  function scoreColor(score) {
    if (score >= 75) return 'var(--green)';
    if (score >= 50) return 'var(--orange)';
    return 'var(--red)';
  }

  function formatDate(dateStr) {
    if (!dateStr) return '--';
    const d = new Date(dateStr);
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function showToast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
  }

  // ========== 主题切换 ==========
  function initTheme() {
    const saved = localStorage.getItem('sr-theme');
    const prefer = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', prefer);
    $('#themeToggle').textContent = prefer === 'dark' ? '☀️' : '🌙';

    $('#themeToggle').addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('sr-theme', next);
      $('#themeToggle').textContent = next === 'dark' ? '☀️' : '🌙';
    });
  }

  // ========== 导航 ==========
  function initNav() {
    $$('.nav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        $$('.nav-link').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const section = link.dataset.section;
        const el = document.getElementById(section);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  // ========== 数据加载 ==========
  async function loadJSON(url) {
    try {
      const res = await fetch(url + '?t=' + Date.now());
      if (!res.ok) throw new Error(res.status);
      return await res.json();
    } catch (e) {
      console.warn('加载失败:', url, e);
      return null;
    }
  }

  async function loadData() {
    const index = await loadJSON('data/projects-index.json');
    if (!index) {
      // 使用示例数据
      useDemoData();
      return;
    }

    // 加载所有项目数据
    const allProjects = [];
    for (const file of (index.files || [])) {
      const data = await loadJSON('data/' + file);
      if (data && Array.isArray(data.projects)) {
        allProjects.push(...data.projects);
      } else if (data && Array.isArray(data)) {
        allProjects.push(...data);
      }
    }

    state.projects = allProjects;

    // 加载讨论数据
    const disc = await loadJSON('data/discussions-index.json');
    if (disc && Array.isArray(disc.files)) {
      const allDisc = [];
      for (const file of disc.files) {
        const data = await loadJSON('data/' + file);
        if (data && Array.isArray(data.discussions)) {
          allDisc.push(...data.discussions);
        } else if (data && Array.isArray(data)) {
          allDisc.push(...data);
        }
      }
      state.discussions = allDisc;
    }

    if (index.lastUpdate) {
      $('#lastUpdate').textContent = formatDate(index.lastUpdate);
    }

    render();
  }

  // ========== 示例数据（开发/演示用） ==========
  function useDemoData() {
    state.projects = getDemoProjects();
    state.discussions = getDemoDiscussions();
    $('#lastUpdate').textContent = '2026-04-25 (示例数据)';
    render();
  }

  function getDemoProjects() {
    return [
      {
        id: 'moonshot-ai',
        name: 'Moonshot AI (月之暗面)',
        desc: '专注于通用人工智能的初创公司，推出了 Kimi 智能助手，支持超长上下文对话。',
        track: 'ai', stage: 'a', city: 'beijing',
        score: 92, scores: { tech: 95, growth: 90, team: 93, market: 88 },
        tags: ['AI', '大模型', 'AGI'],
        team: [
          { name: '杨植麟', role: '创始人 & CEO', bg: '清华大学 / CMU / Google Brain' },
          { name: '周昕宇', role: '联合创始人', bg: '清华大学 / Nvidia Research' },
        ],
        product: 'https://kimi.moonshot.cn',
        founded: '2023-03',
        funding: 'A 轮，超 10 亿美元估值',
        discoveredAt: '2026-04-20',
        discussionCount: 328,
        contacts: {
          website: {
            emails: ['hr@moonshot.cn', 'contact@moonshot.cn'],
            socials: { twitter: 'MoonshotAI', github: 'MoonshotAI' },
            careerPage: 'https://moonshot.cn/careers',
            jobListings: ['大模型算法工程师', '后端开发工程师', '产品经理', 'AI 安全研究员'],
          },
          github: {
            members: [
              { name: '杨植麟', github: 'https://github.com/Yangzhilin', twitter: 'YangZhilin', email: null },
            ],
          },
          hiring: [
            {
              platform: 'Boss直聘',
              jobs: [
                { title: '大模型算法工程师', salary: '50-80K·16薪', city: '北京', experience: '3-5年', url: 'https://www.zhipin.com' },
                { title: '后端开发工程师 (Go)', salary: '40-70K·16薪', city: '北京', experience: '3-5年', url: 'https://www.zhipin.com' },
              ],
            },
          ],
          businessInfo: {},
        },
      },
      {
        id: 'minimax',
        name: 'MiniMax (稀宇科技)',
        desc: '通用大模型公司，产品包括海螺AI、星野等，在多模态和语音合成领域领先。',
        track: 'ai', stage: 'b+', city: 'shanghai',
        score: 88, scores: { tech: 90, growth: 85, team: 90, market: 86 },
        tags: ['AI', '大模型', '多模态'],
        team: [
          { name: '闫俊杰', role: '创始人 & CEO', bg: '中科院 / 商汤科技' },
        ],
        product: 'https://hailuoai.com',
        founded: '2021-12',
        funding: 'B+ 轮，超 25 亿美元估值',
        discoveredAt: '2026-04-18',
        discussionCount: 215,
      },
      {
        id: 'deepseek',
        name: 'DeepSeek (深度求索)',
        desc: '幻方量化孵化的 AI 研究公司，开源 DeepSeek 系列模型，在推理能力上表现突出。',
        track: 'ai', stage: 'seed', city: 'hangzhou',
        score: 95, scores: { tech: 98, growth: 95, team: 92, market: 94 },
        tags: ['AI', '开源', '大模型'],
        team: [
          { name: '梁文锋', role: '创始人', bg: '浙江大学 / 幻方量化' },
        ],
        product: 'https://deepseek.com',
        founded: '2023-05',
        funding: '种子轮（幻方量化全资）',
        discoveredAt: '2026-04-22',
        discussionCount: 567,
        contacts: {
          website: {
            emails: ['hr@deepseek.com', 'contact@deepseek.com'],
            socials: { twitter: 'deepseek_ai', github: 'deepseek-ai' },
            careerPage: 'https://deepseek.com/careers',
            jobListings: ['大模型预训练研究员', '强化学习研究员', 'MLE', '前端工程师'],
          },
          github: {
            members: [
              { name: 'DeepSeek Team', github: 'https://github.com/deepseek-ai', email: null },
            ],
          },
          hiring: [
            {
              platform: 'Boss直聘',
              jobs: [
                { title: '大模型预训练研究员', salary: '60-100K·15薪', city: '杭州', experience: '不限', url: 'https://www.zhipin.com' },
                { title: '强化学习研究员', salary: '60-100K·15薪', city: '杭州', experience: '不限', url: 'https://www.zhipin.com' },
                { title: '系统工程师 (CUDA)', salary: '50-80K·15薪', city: '杭州', experience: '3-5年', url: 'https://www.zhipin.com' },
              ],
            },
          ],
          businessInfo: {},
        },
      },
      {
        id: 'zhipu-ai',
        name: '智谱 AI',
        desc: '清华系 AI 公司，推出 GLM 系列大模型和智谱清言对话产品，技术实力深厚。',
        track: 'ai', stage: 'b+', city: 'beijing',
        score: 86, scores: { tech: 92, growth: 80, team: 90, market: 82 },
        tags: ['AI', '大模型', '清华系'],
        team: [
          { name: '张鹏', role: 'CEO', bg: '清华大学计算机系' },
        ],
        product: 'https://chatglm.cn',
        founded: '2019-06',
        funding: 'B+ 轮，超 100 亿人民币估值',
        discoveredAt: '2026-04-15',
        discussionCount: 189,
      },
      {
        id: 'stepfun',
        name: '阶跃星辰',
        desc: '前微软亚洲研究院副院长姜大昕创立，专注多模态大模型研发。',
        track: 'ai', stage: 'a', city: 'beijing',
        score: 82, scores: { tech: 88, growth: 78, team: 85, market: 76 },
        tags: ['AI', '多模态', '大模型'],
        team: [
          { name: '姜大昕', role: '创始人 & CEO', bg: '微软亚洲研究院' },
        ],
        product: 'https://www.stepfun.com',
        founded: '2023-04',
        funding: 'A 轮，数亿美元',
        discoveredAt: '2026-04-12',
        discussionCount: 98,
      },
      {
        id: 'ppio-cloud',
        name: 'PPIO 派欧云',
        desc: '去中心化 GPU 算力平台，为 AI 开发者提供低成本推理和训练服务。',
        track: 'ai', stage: 'seed', city: 'shenzhen',
        score: 76, scores: { tech: 80, growth: 75, team: 72, market: 78 },
        tags: ['AI', '云计算', '算力'],
        team: [
          { name: '王闻宇', role: '创始人 & CEO', bg: 'PPTV 联合创始人' },
        ],
        product: 'https://ppio.ai',
        founded: '2023-08',
        funding: '种子轮',
        discoveredAt: '2026-04-10',
        discussionCount: 45,
      },
      {
        id: 'manus-ai',
        name: 'Manus AI',
        desc: '通用 AI Agent 平台，能自主完成复杂任务，引发全球关注。',
        track: 'ai', stage: 'pre-seed', city: 'overseas',
        score: 84, scores: { tech: 88, growth: 90, team: 78, market: 80 },
        tags: ['AI Agent', 'AGI', '自动化'],
        team: [
          { name: '肖弘', role: '联合创始人', bg: 'Monica.im' },
        ],
        product: 'https://manus.im',
        founded: '2024-11',
        funding: 'Pre-Seed',
        discoveredAt: '2026-04-23',
        discussionCount: 412,
      },
      {
        id: 'baiyi-tech',
        name: '百译科技',
        desc: '专注于 AI 翻译和跨语言沟通的初创公司，产品覆盖文档翻译、实时对话翻译。',
        track: 'ai', stage: 'angel', city: 'hangzhou',
        score: 65, scores: { tech: 70, growth: 62, team: 68, market: 60 },
        tags: ['AI', '翻译', 'NLP'],
        team: [
          { name: '李明', role: '创始人', bg: '阿里达摩院' },
        ],
        product: 'https://example.com',
        founded: '2024-06',
        funding: '天使轮，数百万人民币',
        discoveredAt: '2026-04-08',
        discussionCount: 23,
      },
      {
        id: 'chain-ml',
        name: 'ChainML',
        desc: '去中心化 AI 推理网络，结合区块链和机器学习，提供可验证的 AI 服务。',
        track: 'web3', stage: 'seed', city: 'overseas',
        score: 71, scores: { tech: 78, growth: 68, team: 70, market: 67 },
        tags: ['Web3', 'AI', '去中心化'],
        team: [
          { name: 'Ron Bodkin', role: 'CEO', bg: 'Google / Think Big Analytics' },
        ],
        product: 'https://chainml.net',
        founded: '2023-01',
        funding: '种子轮，$6.2M',
        discoveredAt: '2026-04-05',
        discussionCount: 56,
      },
      {
        id: 'coze-shop',
        name: '扣子商店',
        desc: '基于字节跳动扣子平台的 AI Bot 应用商店，聚合各类 AI 智能体。',
        track: 'saas', stage: 'pre-a', city: 'beijing',
        score: 73, scores: { tech: 75, growth: 78, team: 70, market: 68 },
        tags: ['SaaS', 'AI Agent', '平台'],
        team: [
          { name: '团队', role: '字节跳动内部孵化', bg: '字节跳动' },
        ],
        product: 'https://www.coze.cn',
        founded: '2024-01',
        funding: 'Pre-A（内部孵化）',
        discoveredAt: '2026-04-19',
        discussionCount: 134,
      },
    ];
  }

  function getDemoDiscussions() {
    return [
      {
        id: 'd1', source: '知乎', sourceIcon: '知',
        title: '如何评价 DeepSeek 最新发布的 R2 模型？',
        url: 'https://zhihu.com',
        snippet: 'DeepSeek R2 在多项基准测试中超越了 GPT-4o，特别是在数学推理和代码生成方面表现突出...',
        date: '2026-04-24', likes: 2345, comments: 567, relatedProject: 'deepseek',
      },
      {
        id: 'd2', source: '36氪', sourceIcon: '36',
        title: 'Manus AI 完成新一轮融资，估值超 5 亿美元',
        url: 'https://36kr.com',
        snippet: '通用 AI Agent 公司 Manus AI 近日完成新一轮融资，由红杉资本领投...',
        date: '2026-04-23', likes: 890, comments: 234, relatedProject: 'manus-ai',
      },
      {
        id: 'd3', source: '微博', sourceIcon: '微',
        title: '#月之暗面Kimi# 上线多模态功能，支持图片和视频理解',
        url: 'https://weibo.com',
        snippet: 'Kimi 智能助手今日更新，新增图片理解和视频分析功能，用户可以直接上传图片进行对话...',
        date: '2026-04-22', likes: 5678, comments: 1234, relatedProject: 'moonshot-ai',
      },
      {
        id: 'd4', source: 'Twitter', sourceIcon: 'X',
        title: 'ChainML announces partnership with major cloud providers',
        url: 'https://twitter.com',
        snippet: 'Excited to announce our partnership with AWS and GCP to bring decentralized AI inference to enterprise customers...',
        date: '2026-04-21', likes: 456, comments: 89, relatedProject: 'chain-ml',
      },
      {
        id: 'd5', source: '虎嗅', sourceIcon: '虎',
        title: '2026 年最值得关注的 10 家 AI 初创公司',
        url: 'https://huxiu.com',
        snippet: '从大模型到 AI Agent，从算力平台到垂直应用，这 10 家公司正在重新定义 AI 行业的格局...',
        date: '2026-04-20', likes: 3456, comments: 678, relatedProject: null,
      },
      {
        id: 'd6', source: '少数派', sourceIcon: '少',
        title: '智谱清言深度体验：GLM-5 到底好不好用？',
        url: 'https://sspai.com',
        snippet: '作为国产大模型的代表之一，智谱清言最近更新了 GLM-5 模型，我们进行了为期一周的深度体验...',
        date: '2026-04-19', likes: 789, comments: 156, relatedProject: 'zhipu-ai',
      },
      {
        id: 'd7', source: 'Product Hunt', sourceIcon: 'PH',
        title: 'PPIO Cloud - Affordable GPU cloud for AI developers',
        url: 'https://producthunt.com',
        snippet: 'PPIO Cloud offers decentralized GPU computing at 60% lower cost than traditional cloud providers...',
        date: '2026-04-18', likes: 234, comments: 45, relatedProject: 'ppio-cloud',
      },
    ];
  }

  // ========== 渲染：热门项目卡片 ==========
  function renderHotCards() {
    const hot = [...state.projects]
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);

    const container = $('#hotCards');
    if (hot.length === 0) {
      container.innerHTML = '<div class="loading">暂无数据</div>';
      return;
    }

    container.innerHTML = hot.map(p => `
      <div class="card" data-id="${p.id}">
        <div class="card-header">
          <span class="card-name">${esc(p.name)}</span>
          <span class="card-score ${scoreClass(p.score)}">⚡ ${p.score}</span>
        </div>
        <div class="card-desc">${esc(p.desc)}</div>
        <div class="card-tags">
          ${(p.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join('')}
        </div>
        <div class="card-meta">
          <span>📍 ${cityLabel(p.city)}</span>
          <span>🏷️ ${stageLabel(p.stage)}</span>
          <span>💬 ${p.discussionCount || 0} 讨论</span>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.card').forEach(card => {
      card.addEventListener('click', () => openModal(card.dataset.id));
    });
  }

  // ========== 渲染：项目列表 ==========
  function renderProjectList() {
    let filtered = [...state.projects];

    // 筛选
    if (state.filters.track) {
      filtered = filtered.filter(p => p.track === state.filters.track);
    }
    if (state.filters.stage) {
      filtered = filtered.filter(p => p.stage === state.filters.stage);
    }
    if (state.filters.city) {
      filtered = filtered.filter(p => p.city === state.filters.city);
    }

    // 排序
    switch (state.filters.sort) {
      case 'score':
        filtered.sort((a, b) => b.score - a.score);
        break;
      case 'newest':
        filtered.sort((a, b) => new Date(b.discoveredAt) - new Date(a.discoveredAt));
        break;
      case 'discussed':
        filtered.sort((a, b) => (b.discussionCount || 0) - (a.discussionCount || 0));
        break;
    }

    // 分页
    const total = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / state.pageSize));
    state.page = Math.min(state.page, totalPages);
    const start = (state.page - 1) * state.pageSize;
    const paged = filtered.slice(start, start + state.pageSize);

    const container = $('#projectList');
    if (paged.length === 0) {
      container.innerHTML = '<div class="loading">没有找到匹配的项目</div>';
      $('#pagination').innerHTML = '';
      return;
    }

    container.innerHTML = paged.map((p, i) => {
      const rank = start + i + 1;
      return `
        <div class="project-row" data-id="${p.id}">
          <span class="project-rank ${rank <= 3 ? 'top3' : ''}">${rank}</span>
          <div class="project-info">
            <div class="project-info-name">${esc(p.name)}</div>
            <div class="project-info-desc">${esc(p.desc)}</div>
          </div>
          <div class="project-tags">
            ${(p.tags || []).slice(0, 2).map(t => `<span class="tag">${esc(t)}</span>`).join('')}
          </div>
          <span class="project-score-badge" style="color:${scoreColor(p.score)}">${p.score}</span>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.project-row').forEach(row => {
      row.addEventListener('click', () => openModal(row.dataset.id));
    });

    // 分页
    renderPagination(totalPages);
  }

  function renderPagination(totalPages) {
    const container = $('#pagination');
    if (totalPages <= 1) {
      container.innerHTML = '';
      return;
    }

    let html = '';
    if (state.page > 1) {
      html += `<button data-page="${state.page - 1}">‹</button>`;
    }
    for (let i = 1; i <= totalPages; i++) {
      if (totalPages > 7 && Math.abs(i - state.page) > 2 && i !== 1 && i !== totalPages) {
        if (i === state.page - 3 || i === state.page + 3) html += `<button disabled>…</button>`;
        continue;
      }
      html += `<button data-page="${i}" class="${i === state.page ? 'active' : ''}">${i}</button>`;
    }
    if (state.page < totalPages) {
      html += `<button data-page="${state.page + 1}">›</button>`;
    }

    container.innerHTML = html;
    container.querySelectorAll('button[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.page = parseInt(btn.dataset.page);
        renderProjectList();
        $('#explore').scrollIntoView({ behavior: 'smooth' });
      });
    });
  }

  // ========== 渲染：全网讨论 ==========
  function renderDiscussions() {
    const container = $('#discussionList');
    const items = state.discussions.slice(0, 20);

    if (items.length === 0) {
      container.innerHTML = '<div class="loading">暂无讨论数据</div>';
      return;
    }

    container.innerHTML = items.map(d => `
      <div class="discussion-item">
        <div class="discussion-header">
          <span class="discussion-source">${esc(d.sourceIcon || d.source)}</span>
          <span class="discussion-source" style="background:transparent;color:var(--text-secondary);padding:0">${esc(d.source)}</span>
          <span class="discussion-date">${formatDate(d.date)}</span>
          ${d.relatedProject ? `<span class="tag" style="margin-left:auto;cursor:pointer" data-id="${d.relatedProject}">查看项目 →</span>` : ''}
        </div>
        <div class="discussion-title"><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a></div>
        <div class="discussion-snippet">${esc(d.snippet)}</div>
        <div class="discussion-stats">
          <span>👍 ${d.likes || 0}</span>
          <span>💬 ${d.comments || 0}</span>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.tag[data-id]').forEach(tag => {
      tag.addEventListener('click', () => openModal(tag.dataset.id));
    });
  }

  // ========== 项目详情弹窗 ==========
  function openModal(projectId) {
    const p = state.projects.find(x => x.id === projectId);
    if (!p) return;

    const relatedDisc = state.discussions.filter(d => d.relatedProject === projectId);

    const body = $('#modalBody');
    body.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">
        <h2>${esc(p.name)}</h2>
        <span class="card-score ${scoreClass(p.score)}">⚡ ${p.score}</span>
      </div>
      <p style="color:var(--text-secondary);font-size:0.9rem">${esc(p.desc)}</p>

      <div class="card-tags" style="margin-top:12px">
        ${(p.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join('')}
        <span class="tag">📍 ${cityLabel(p.city)}</span>
        <span class="tag">🏷️ ${stageLabel(p.stage)}</span>
      </div>

      <div class="modal-section">
        <h3>📊 增长评分</h3>
        ${renderScoreBars(p.scores || {})}
      </div>

      <div class="modal-section">
        <h3>👥 核心团队</h3>
        <div class="team-list">
          ${(p.team || []).map(m => `
            <div class="team-member">
              <div class="team-avatar">${(m.name || '?')[0]}</div>
              <div>
                <div class="team-name">${esc(m.name)}</div>
                <div class="team-role">${esc(m.role)}${m.bg ? ' · ' + esc(m.bg) : ''}</div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="modal-section">
        <h3>📋 基本信息</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.88rem">
          <div><span style="color:var(--text-secondary)">成立时间：</span>${esc(p.founded || '--')}</div>
          <div><span style="color:var(--text-secondary)">融资情况：</span>${esc(p.funding || '--')}</div>
          <div><span style="color:var(--text-secondary)">发现时间：</span>${formatDate(p.discoveredAt)}</div>
          <div><span style="color:var(--text-secondary)">产品链接：</span>${p.product ? `<a href="${esc(p.product)}" target="_blank" rel="noopener" style="color:var(--accent)">${esc(p.product)}</a>` : '--'}</div>
        </div>
      </div>

      ${relatedDisc.length > 0 ? `
        <div class="modal-section">
          <h3>💬 相关讨论 (${relatedDisc.length})</h3>
          <div class="modal-discussions">
            ${relatedDisc.map(d => `
              <div class="modal-discussion-item">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                  <span class="discussion-source">${esc(d.source)}</span>
                  <span style="font-size:0.78rem;color:var(--text-secondary)">${formatDate(d.date)}</span>
                </div>
                <a href="${esc(d.url)}" target="_blank" rel="noopener" style="color:var(--text);font-weight:500;text-decoration:none;font-size:0.9rem">${esc(d.title)}</a>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${renderContactsSection(p)}
    `;

    $('#modalOverlay').classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  // ========== 渲染：联系方式与招聘信息 ==========
  function renderContactsSection(p) {
    const c = p.contacts;
    if (!c) return '';

    let html = '';

    // 联系方式
    const emails = (c.website && c.website.emails) || [];
    const socials = (c.website && c.website.socials) || {};
    const ghMembers = (c.github && c.github.members) || [];
    const hasContact = emails.length > 0 || Object.keys(socials).length > 0 || ghMembers.length > 0;

    if (hasContact) {
      html += `<div class="modal-section"><h3>📧 联系方式</h3><div class="contact-grid">`;

      if (emails.length > 0) {
        html += `<div class="contact-item">
          <span class="contact-label">邮箱</span>
          ${emails.slice(0, 3).map(e => `<a href="mailto:${esc(e)}" class="contact-link">${esc(e)}</a>`).join('')}
        </div>`;
      }

      const socialLabels = { twitter: 'Twitter/X', linkedin: 'LinkedIn', github: 'GitHub', wechat: '微信' };
      for (const [platform, handle] of Object.entries(socials)) {
        const label = socialLabels[platform] || platform;
        let url = handle;
        if (platform === 'twitter') url = 'https://x.com/' + handle;
        else if (platform === 'linkedin') url = 'https://linkedin.com/in/' + handle;
        else if (platform === 'github') url = 'https://github.com/' + handle;
        html += `<div class="contact-item">
          <span class="contact-label">${esc(label)}</span>
          <a href="${esc(url)}" target="_blank" rel="noopener" class="contact-link">${esc(handle)}</a>
        </div>`;
      }

      // GitHub 团队成员联系方式
      for (const m of ghMembers.slice(0, 3)) {
        const links = [];
        if (m.email) links.push(`<a href="mailto:${esc(m.email)}" class="contact-link">${esc(m.email)}</a>`);
        if (m.twitter) links.push(`<a href="https://x.com/${esc(m.twitter)}" target="_blank" rel="noopener" class="contact-link">@${esc(m.twitter)}</a>`);
        if (m.github) links.push(`<a href="${esc(m.github)}" target="_blank" rel="noopener" class="contact-link">GitHub</a>`);
        if (links.length > 0) {
          html += `<div class="contact-item">
            <span class="contact-label">${esc(m.name)}</span>
            ${links.join(' ')}
          </div>`;
        }
      }

      html += `</div></div>`;
    }

    // 招聘信息
    const hiring = c.hiring || [];
    const careerPage = c.website && c.website.careerPage;
    const websiteJobs = (c.website && c.website.jobListings) || [];
    const allJobs = [];
    for (const h of hiring) {
      for (const j of (h.jobs || [])) {
        allJobs.push({ ...j, platform: h.platform });
      }
    }

    if (allJobs.length > 0 || careerPage || websiteJobs.length > 0) {
      html += `<div class="modal-section"><h3>💼 招聘信息</h3>`;

      if (careerPage) {
        html += `<p style="margin-bottom:12px"><a href="${esc(careerPage)}" target="_blank" rel="noopener" style="color:var(--accent)">🔗 官网招聘页</a></p>`;
      }

      if (allJobs.length > 0) {
        html += `<div class="job-list">`;
        for (const job of allJobs.slice(0, 10)) {
          html += `<div class="job-item">
            <div class="job-title">${esc(job.title)}</div>
            <div class="job-meta">
              ${job.salary ? `<span class="job-salary">${esc(job.salary)}</span>` : ''}
              ${job.city ? `<span>📍 ${esc(job.city)}</span>` : ''}
              ${job.experience ? `<span>${esc(job.experience)}</span>` : ''}
              <span class="tag">${esc(job.platform)}</span>
            </div>
            ${job.url ? `<a href="${esc(job.url)}" target="_blank" rel="noopener" class="job-apply">查看详情 →</a>` : ''}
          </div>`;
        }
        html += `</div>`;
      } else if (websiteJobs.length > 0) {
        html += `<div class="job-list">`;
        for (const title of websiteJobs.slice(0, 8)) {
          html += `<div class="job-item"><div class="job-title">${esc(title)}</div></div>`;
        }
        html += `</div>`;
      }

      html += `</div>`;
    }

    return html;
  }

  function closeModal() {
    $('#modalOverlay').classList.remove('open');
    document.body.style.overflow = '';
  }

  function renderScoreBars(scores) {
    const dims = [
      { key: 'tech', label: '技术实力' },
      { key: 'growth', label: '增长速度' },
      { key: 'team', label: '团队背景' },
      { key: 'market', label: '市场前景' },
    ];
    return dims.map(d => {
      const val = scores[d.key] || 0;
      return `
        <div class="score-bar">
          <span class="score-bar-label">${d.label}</span>
          <div class="score-bar-track">
            <div class="score-bar-fill" style="width:${val}%;background:${scoreColor(val)}"></div>
          </div>
          <span class="score-bar-value" style="color:${scoreColor(val)}">${val}</span>
        </div>
      `;
    }).join('');
  }

  // ========== 标签映射 ==========
  function cityLabel(city) {
    const map = {
      beijing: '北京', shanghai: '上海', shenzhen: '深圳',
      hangzhou: '杭州', guangzhou: '广州', chengdu: '成都',
      overseas: '海外', other: '其他',
    };
    return map[city] || city || '未知';
  }

  function stageLabel(stage) {
    const map = {
      idea: '概念期', 'pre-seed': 'Pre-Seed', seed: '种子轮',
      angel: '天使轮', 'pre-a': 'Pre-A', a: 'A 轮', 'b+': 'B 轮+',
    };
    return map[stage] || stage || '未知';
  }

  function trackLabel(track) {
    const map = {
      ai: 'AI', saas: 'SaaS', web3: 'Web3', ecommerce: '跨境电商',
      hardtech: '硬科技', consumer: '消费互联网', biotech: '生物医药',
      fintech: '金融科技', other: '其他',
    };
    return map[track] || track || '未知';
  }

  function esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ========== 筛选事件 ==========
  function initFilters() {
    ['filterTrack', 'filterStage', 'filterCity', 'filterSort'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('change', () => {
        state.filters.track = $('#filterTrack').value;
        state.filters.stage = $('#filterStage').value;
        state.filters.city = $('#filterCity').value;
        state.filters.sort = $('#filterSort').value;
        state.page = 1;
        renderProjectList();
      });
    });
  }

  // ========== 弹窗事件 ==========
  function initModal() {
    $('#modalClose').addEventListener('click', closeModal);
    $('#modalOverlay').addEventListener('click', (e) => {
      if (e.target === $('#modalOverlay')) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });
  }

  // ========== 自动刷新 ==========
  function initAutoRefresh() {
    setInterval(async () => {
      const index = await loadJSON('data/projects-index.json');
      if (index && index.lastUpdate && index.lastUpdate !== state.lastDataHash) {
        if (state.lastDataHash) {
          showToast('📡 数据已更新，正在刷新...');
          setTimeout(() => loadData(), 1000);
        }
        state.lastDataHash = index.lastUpdate;
      }
    }, 60000);
  }

  // ========== 总渲染 ==========
  function render() {
    renderHotCards();
    renderProjectList();
    renderDiscussions();
  }

  // ========== 初始化 ==========
  function init() {
    initTheme();
    initNav();
    initFilters();
    initModal();
    loadData();
    initAutoRefresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
