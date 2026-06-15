"""
简易 MCP Server — 提供几个实用工具：
  - 计算器（加减乘除）
  - 获取当前时间
  - 文本反转/大小写转换

使用 FastMCP 框架，通过 HTTP (SSE) 对外暴露服务。
"""

import datetime
from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器实例（host="0.0.0.0" 允许外部访问）
mcp = FastMCP("My Tools Server", host="0.0.0.0", port=8080)


# ============ 工具1: 计算器 ============
@mcp.tool()
def calculator(expression: str) -> str:
    """
    安全计算数学表达式。支持 + - * / ** 和括号。

    示例:
        calculator("2 + 3 * 4")   → "14"
        calculator("(10 - 2) / 4") → "2.0"
    """
    allowed = set("0123456789+-*/(). ")
    if not all(c in allowed for c in expression):
        return f"错误：表达式包含不允许的字符。仅支持: {''.join(sorted(allowed))}"
    try:
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"计算出错: {e}"


# ============ 工具2: 获取当前时间 ============
@mcp.tool()
def current_time(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前日期时间。

    参数:
        format_str: 时间格式字符串，默认 "%Y-%m-%d %H:%M:%S"
                    常用格式:
                      %Y-%m-%d          → 2026-06-15
                      %Y-%m-%d %H:%M:%S → 2026-06-15 14:30:00
                      %A, %B %d %Y      → Monday, June 15 2026
    """
    return datetime.datetime.now().strftime(format_str)


# ============ 工具3: 文本处理 ============
@mcp.tool()
def text_tool(text: str, action: str = "reverse") -> str:
    """
    文本处理工具。

    参数:
        text:   要处理的文本
        action: 操作类型 — "reverse"(反转), "upper"(全大写), "lower"(全小写), "length"(长度)
    """
    actions = {
        "reverse": lambda t: t[::-1],
        "upper":   lambda t: t.upper(),
        "lower":   lambda t: t.lower(),
        "length":  lambda t: str(len(t)),
    }
    if action not in actions:
        return f"未知操作: {action}，支持: {', '.join(actions.keys())}"
    return actions[action](text)


# ============ 启动服务 ============
if __name__ == "__main__":
    print("=" * 50)
    print("  MCP Server 启动中...")
    print("  HTTP (SSE) 端点: http://0.0.0.0:8080/sse")
    print("=" * 50)
    mcp.run(transport="sse")
