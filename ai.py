# -*- coding: utf-8 -*-
import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

FIXED_CATEGORIES = [
    "MCP", "Skill", "插件", "CLI 工具", "Web 应用",
    "桌面应用", "SDK/库", "浏览器扩展", "框架", "其他",
]

SYSTEM_PROMPT = f"""你是一个 AI 项目分析助手。判断给定 GitHub 项目是否为 AI 相关的实用工具，并给出详细分析。

规则：
- 只保留可以直接使用、解决具体问题的 AI 工具类项目
- 排除：大模型本身、论文复现、纯学习资料、数据集、非 AI 项目

返回 JSON，包含以下字段：
{{
  "is_ai": true/false,
  "category": "工具的固定类别，只能从以下选择：{', '.join(FIXED_CATEGORIES)}",
  "domain": "具体应用领域，4-8 个中文字。例如：代码审查、代码补全、图像生成、视频生成、音频处理、上下文压缩、文档写作、翻译、语音识别、Agent 编排、数据可视化、RAG、测试、安全审计、爬虫、搜索、办公自动化、提示词管理、知识库 等",
  "summary": "项目介绍，100-200字中文。要说清楚三件事：(1) 这个工具是做什么的；(2) 主要功能/能力有哪些；(3) 适合什么人用。不要用'这是一个'开头，直接描述功能。非 AI 项目填空字符串"
}}
"""


def analyze_repo(repo: dict) -> dict:
    user_prompt = (
        f"项目名: {repo['full_name']}\n"
        f"描述: {repo['description']}\n"
        f"语言: {repo['language']}"
    )
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        is_ai = bool(data.get("is_ai", False))
        return {
            "is_ai": is_ai,
            "category": data.get("category", "") if is_ai else "",
            "domain": data.get("domain", "") if is_ai else "",
            "ai_summary": data.get("summary", "") if is_ai else "",
        }
    except Exception as e:
        print(f"[ai] 分析失败 {repo['full_name']}: {e}")
        return {"is_ai": False, "category": "", "domain": "", "ai_summary": ""}