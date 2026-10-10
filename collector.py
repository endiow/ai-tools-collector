# -*- coding: utf-8 -*-
import time
import httpx
from bs4 import BeautifulSoup
from config import GITHUB_TOKEN

PROXY = "http://127.0.0.1:7993"


def _parse_num(text: str) -> int:
    if not text:
        return 0
    text = text.replace(",", "").strip()
    if text.endswith("k"):
        try:
            return int(float(text[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(text)
    except ValueError:
        return 0


def _fetch_trending(since: str) -> list[dict]:
    """通用 Trending 抓取，since 为 daily 或 weekly。"""
    url = f"https://github.com/trending?since={since}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    resp = None
    for attempt in range(3):
        try:
            resp = httpx.get(
                url, headers=headers, timeout=60,
                follow_redirects=True, proxy=PROXY,
            )
            resp.raise_for_status()
            break
        except Exception as e:
            print(f"[trending:{since}] 第 {attempt + 1} 次请求失败: {e}")
            if attempt == 2:
                return []
            time.sleep(5)

    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []

    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        full_name = h2["href"].strip("/")
        if "/" not in full_name:
            continue
        owner, name = full_name.split("/", 1)

        desc_el = article.select_one("p")
        lang_el = article.select_one('[itemprop="programmingLanguage"]')
        star_el = article.select_one('a[href$="/stargazers"]')
        fork_el = article.select_one('a[href$="/forks"]')
        today_el = article.select_one(".d-inline-block.float-sm-right")

        repos.append({
            "full_name": full_name,
            "owner": owner,
            "name": name,
            "url": f"https://github.com/{full_name}",
            "description": desc_el.get_text(strip=True) if desc_el else "",
            "language": lang_el.get_text(strip=True) if lang_el else "",
            "stars": _parse_num(star_el.get_text(strip=True)) if star_el else 0,
            "forks": _parse_num(fork_el.get_text(strip=True)) if fork_el else 0,
            "stars_today": today_el.get_text(strip=True) if today_el else "",
            "period": since,
        })

    print(f"  trending[all/{since}]: {len(repos)} 条")
    return repos


def fetch_trending_daily() -> list[dict]:
    """抓取 GitHub Trending 全语言日榜。"""
    return _fetch_trending("daily")


def fetch_trending_weekly() -> list[dict]:
    """抓取 GitHub Trending 全语言周榜。"""
    return _fetch_trending("weekly")


def fetch_repo_license(full_name: str) -> str:
    """通过 GitHub API 获取仓库 license。"""
    url = f"https://api.github.com/repos/{full_name}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/vnd.github+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    try:
        resp = httpx.get(
            url, headers=headers, timeout=30,
            follow_redirects=True, proxy=PROXY,
        )
        resp.raise_for_status()
        data = resp.json()
        lic = data.get("license")
        if lic:
            return lic.get("spdx_id") or lic.get("name") or "未知"
        return "无许可证"
    except Exception as e:
        print(f"[license] {full_name} 获取失败: {e}")
        return "未知"