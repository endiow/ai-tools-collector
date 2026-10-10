# -*- coding: utf-8 -*-
import hashlib
import streamlit as st
from datetime import date
from sqlalchemy import desc, or_
from db import init_db, SessionLocal, Project
from collector import fetch_trending_daily, fetch_trending_weekly, fetch_repo_license
from ai import analyze_repo

st.set_page_config(
    page_title="AI 工具 Trending",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()

if "page" not in st.session_state:
    st.session_state.page = "today"

# ---------- 全局样式 ----------
st.markdown("""
<style>
/* 隐藏侧边栏折叠按钮 */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stBaseButton-headerNoPadding"] {
    display: none !important;
    visibility: hidden !important;
}

/* 隐藏侧边栏拖拽手柄 */
[data-testid="stSidebarResizeHandle"],
[data-testid="stSidebarResizer"],
[data-testid="stResizeHandle"],
div[data-testid="stSidebar"] > div:last-child,
section[data-testid="stSidebar"] > div:last-child {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    max-width: 0 !important;
    pointer-events: none !important;
}

/* 侧边栏固定宽度 */
section[data-testid="stSidebar"] {
    width: 230px !important;
    min-width: 230px !important;
    max-width: 230px !important;
    resize: none !important;
}
section[data-testid="stSidebar"] > div:first-child {
    width: 230px !important;
    padding-top: 40px;
}

/* 侧边栏导航按钮 - 默认状态 */
.st-key-nav_today button,
.st-key-nav_week button,
.st-key-nav_all button {
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 12px 16px !important;
    border: none !important;
    background: transparent !important;
    color: #374151 !important;
    font-size: 17px !important;
    font-weight: 400 !important;
    border-radius: 8px !important;
    margin-bottom: 6px !important;
    box-shadow: none !important;
}
.st-key-nav_today button:hover,
.st-key-nav_week button:hover,
.st-key-nav_all button:hover {
    background: #f0f2f6 !important;
    color: #111827 !important;
}

/* 侧边栏导航按钮 - 选中状态（加粗） */
.st-key-nav_today button[kind="primary"],
.st-key-nav_week button[kind="primary"],
.st-key-nav_all button[kind="primary"] {
    background: #d1e7dd !important;
    color: #0f5132 !important;
    font-weight: 700 !important;
    font-size: 17px !important;
    box-shadow: none !important;
}
.st-key-nav_today button[kind="primary"]:hover,
.st-key-nav_week button[kind="primary"]:hover,
.st-key-nav_all button[kind="primary"]:hover {
    background: #c3e0d3 !important;
    color: #0f5132 !important;
}

/* 按钮内部 p 标签 */
.st-key-nav_today button p,
.st-key-nav_week button p,
.st-key-nav_all button p {
    text-align: left !important;
    width: 100% !important;
    margin: 0 !important;
    font-size: 17px !important;
    font-weight: inherit !important;
}
.st-key-nav_today button[kind="primary"] p,
.st-key-nav_week button[kind="primary"] p,
.st-key-nav_all button[kind="primary"] p {
    font-weight: 700 !important;
    font-size: 17px !important;
    color: #0f5132 !important;
}

/* 抓取按钮 - 蓝紫色 */
.st-key-collect_btn button,
.st-key-collect_week_btn button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35) !important;
}
.st-key-collect_btn button:hover,
.st-key-collect_week_btn button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(102, 126, 234, 0.55) !important;
    color: white !important;
}

/* expander 卡片 */
div[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    margin-bottom: 12px !important;
    background: #ffffff;
    transition: box-shadow 0.2s ease;
}
div[data-testid="stExpander"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}
div[data-testid="stExpander"] summary {
    padding: 16px 20px !important;
    font-size: 15px !important;
}

/* 日志 */
.log-box {
    background: #0e1117;
    color: #e6e6e6;
    padding: 16px;
    border-radius: 10px;
    font-family: 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.8;
    max-height: 500px;
    overflow-y: auto;
    border: 1px solid #333;
}
.log-box .ok { color: #4ade80; }
.log-box .no { color: #9ca3af; }
.log-box .err { color: #f87171; }
.log-box .info { color: #60a5fa; }
</style>
""", unsafe_allow_html=True)


def fmt_stars(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def _hash(full_name: str) -> str:
    return hashlib.md5(full_name.encode("utf-8")).hexdigest()


# ---------- 抓取 ----------
def collect(container, period: str):
    """period: daily 或 weekly"""
    today = date.today()
    logs = []

    def log(msg, cls="info"):
        logs.append(f'<div class="{cls}">{msg}</div>')
        container.markdown(
            f'<div class="log-box">{"".join(logs)}</div>',
            unsafe_allow_html=True,
        )

    label = "日榜" if period == "daily" else "周榜"
    log(f"▶ 开始抓取 GitHub Trending {label}...", "info")

    repos = fetch_trending_daily() if period == "daily" else fetch_trending_weekly()
    if not repos:
        log("✗ 抓取失败，请检查网络或代理", "err")
        return 0, 0, "抓取失败"

    log(f"✓ 抓到 {len(repos)} 个项目", "ok")

    session = SessionLocal()
    try:
        ai_count = 0
        new_count = 0
        updated_count = 0

        for i, repo in enumerate(repos, 1):
            h = _hash(repo["full_name"])
            existing = session.query(Project).filter(Project.hash == h).first()

            if existing:
                # 合并 period
                periods = set((existing.period or "").split(","))
                periods.discard("")
                periods.add(period)
                existing.period = ",".join(sorted(periods))

                # 按榜单写入对应字段
                existing.stars = repo["stars"]
                if period == "daily":
                    existing.stars_today = repo["stars_today"]
                else:
                    existing.stars_week = repo["stars_today"]

                existing.collected_date = today
                session.commit()
                updated_count += 1
                continue

            # 新项目 → AI 分析
            log(f"[{i}/{len(repos)}] 新项目 {repo['full_name']}", "info")
            license_type = fetch_repo_license(repo["full_name"])
            log(f"　　· 许可证：{license_type}", "info")

            result = analyze_repo(repo)
            project = Project(
                hash=h,
                full_name=repo["full_name"],
                name=repo["name"],
                owner=repo["owner"],
                url=repo["url"],
                description=repo["description"],
                language=repo["language"],
                stars=repo["stars"],
                forks=repo["forks"],
                stars_today=repo["stars_today"] if period == "daily" else None,
                stars_week=repo["stars_today"] if period == "weekly" else None,
                period=period,
                is_ai=result["is_ai"],
                category=result["category"],
                domain=result["domain"],
                ai_summary=result["ai_summary"],
                license_type=license_type,
                collected_date=today,
            )
            session.add(project)
            session.commit()
            new_count += 1
            if result["is_ai"]:
                ai_count += 1
                log(
                    f"　　✓ AI 工具 | {result['category']} · {result['domain']}",
                    "ok",
                )
            else:
                log("　　— 非 AI 相关", "no")

        log(
            f"✓ 完成！新增 {new_count} 个，更新 {updated_count} 个，"
            f"其中 {ai_count} 个是新 AI 工具",
            "ok",
        )
        return new_count, ai_count, None
    except Exception as e:
        log(f"✗ 处理出错：{e}", "err")
        return 0, 0, str(e)
    finally:
        session.close()


# ---------- 卡片 ----------
def render_card(p):
    stars = fmt_stars(p.stars)
    label = (
        f"⭐ **{stars}**　　**{p.full_name}**　　"
        f"`{p.category or '未分类'}`　`{p.domain or '其他'}`"
    )
    with st.expander(label, expanded=False):
        st.markdown(
            f"<div style='color:#374151;font-size:14px;line-height:1.9;'>"
            f"{p.ai_summary or p.description or '（暂无介绍）'}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"- **许可证**：`{p.license_type or '未知'}`")
            st.markdown(f"- **语言**：{p.language or '未知'}")
            if p.stars_today:
                st.markdown(f"- **今日新增 Star**：{p.stars_today}")
            if p.stars_week:
                st.markdown(f"- **本周新增 Star**：{p.stars_week}")
        with c2:
            st.markdown(f"- **收录日期**：{p.collected_date}")
            st.markdown(f"- **原始描述**：{p.description or '（无）'}")
            st.markdown(f"- **链接**：[{p.url}]({p.url})")


# ---------- 侧边栏 ----------
with st.sidebar:
    if st.button(
        "🔥 今日热榜",
        use_container_width=True,
        type="primary" if st.session_state.page == "today" else "secondary",
        key="nav_today",
    ):
        st.session_state.page = "today"
        st.rerun()

    if st.button(
        "📈 每周趋势",
        use_container_width=True,
        type="primary" if st.session_state.page == "week" else "secondary",
        key="nav_week",
    ):
        st.session_state.page = "week"
        st.rerun()

    if st.button(
        "📚 全部项目",
        use_container_width=True,
        type="primary" if st.session_state.page == "all" else "secondary",
        key="nav_all",
    ):
        st.session_state.page = "all"
        st.rerun()


# ---------- 主区域 ----------
if st.session_state.page == "today":
    st.title("今日热榜")

    col1, col2 = st.columns([1, 4])
    with col1:
        collect_btn = st.button(
            "🚀 立即抓取",
            type="primary",
            use_container_width=True,
            key="collect_btn",
        )
    with col2:
        show_all = st.checkbox("显示所有项目（包括非 AI）", value=False)

    if collect_btn:
        with st.status("正在抓取日榜...", expanded=True) as status:
            log_container = st.empty()
            n_total, n_ai, err = collect(log_container, "daily")
            if err:
                status.update(label=f"抓取失败：{err}", state="error")
            else:
                status.update(
                    label=f"完成！新增 {n_total} 个，{n_ai} 个新 AI 工具",
                    state="complete",
                )
        st.rerun()

    today = date.today()
    with SessionLocal() as session:
        query = session.query(Project).filter(
            Project.period.like("%daily%"),
            Project.collected_date == today,
        )
        if not show_all:
            query = query.filter(Project.is_ai == True)
        projects = query.order_by(desc(Project.stars)).all()

    st.write(f"共 **{len(projects)}** 个项目")

    if not projects:
        st.info("今日暂无数据，点击上方「🚀 立即抓取」按钮获取数据。")

    for p in projects:
        render_card(p)


elif st.session_state.page == "week":
    st.title("每周趋势")

    col1, col2 = st.columns([1, 4])
    with col1:
        collect_week_btn = st.button(
            "🚀 立即抓取",
            type="primary",
            use_container_width=True,
            key="collect_week_btn",
        )
    with col2:
        show_all_week = st.checkbox("显示所有项目（包括非 AI）", value=False)

    if collect_week_btn:
        with st.status("正在抓取周榜...", expanded=True) as status:
            log_container = st.empty()
            n_total, n_ai, err = collect(log_container, "weekly")
            if err:
                status.update(label=f"抓取失败：{err}", state="error")
            else:
                status.update(
                    label=f"完成！新增 {n_total} 个，{n_ai} 个新 AI 工具",
                    state="complete",
                )
        st.rerun()

    today = date.today()
    with SessionLocal() as session:
        query = session.query(Project).filter(
            Project.period.like("%weekly%"),
            Project.collected_date == today,
        )
        if not show_all_week:
            query = query.filter(Project.is_ai == True)
        projects = query.order_by(desc(Project.stars)).all()

    st.write(f"共 **{len(projects)}** 个项目")

    if not projects:
        st.info("今日暂无数据，点击上方「🚀 立即抓取」按钮获取数据。")

    for p in projects:
        render_card(p)


elif st.session_state.page == "all":
    st.title("全部项目")

    keyword = st.text_input(
        "筛选",
        placeholder="输入关键词，筛选项目名、介绍、领域或分类…",
        label_visibility="collapsed",
    )

    with SessionLocal() as session:
        query = session.query(Project).filter(Project.is_ai == True)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    Project.full_name.like(pattern),
                    Project.description.like(pattern),
                    Project.ai_summary.like(pattern),
                    Project.category.like(pattern),
                    Project.domain.like(pattern),
                )
            )
        projects = query.order_by(
            desc(Project.collected_date), desc(Project.stars)
        ).all()

    st.write(f"共 **{len(projects)}** 个项目")

    current_date = None
    for p in projects:
        if p.collected_date != current_date:
            current_date = p.collected_date
            st.markdown(
                f"<div style='color:#6b7280;font-size:13px;font-weight:600;"
                f"margin:20px 0 10px 0;'>{current_date}</div>",
                unsafe_allow_html=True,
            )
        render_card(p)