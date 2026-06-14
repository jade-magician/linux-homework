"""
摩斯密码 MCP 服务 — Morse Code MCP Server
==========================================
提供两个工具：
1. morse_encode — 将文本转换为"哈""基""咪"摩斯密码，需要 token 鉴权
2. get_token   — 返回鉴权所需的 token，无需鉴权

CherryStudio 配置方式（stdio 传输）：
  命令: python3
  参数: C:/Users/32102/linux-homework/linux_homework7/morse_server.py
"""

import secrets
import sys
from mcp.server.fastmcp import FastMCP

# ── 启动时生成随机 token ─────────────────────────────────────────────
AUTH_TOKEN = secrets.token_hex(16)
print(f"[INFO] Auth token generated: {AUTH_TOKEN}", file=sys.stderr)

# ── 摩斯密码对照表 ────────────────────────────────────────────────────
MORSE_TABLE = {
    'A': '.-',   'B': '-...', 'C': '-.-.', 'D': '-..',  'E': '.',
    'F': '..-.', 'G': '--.',  'H': '....', 'I': '..',   'J': '.---',
    'K': '-.-',  'L': '.-..', 'M': '--',   'N': '-.',   'O': '---',
    'P': '.--.', 'Q': '--.-', 'R': '.-.',  'S': '...',  'T': '-',
    'U': '..-',  'V': '...-', 'W': '.--',  'X': '-..-', 'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.',  '(': '-.--.',  ')': '-.--.-',
    '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-',
    '+': '.-.-.',  '-': '-....-', '_': '..--.-', '"': '.-..-.',
    '$': '...-..-', '@': '.--.-.',
}

# ── 映射规则 ──────────────────────────────────────────────────────────
# 点 (.)   → 哈
# 横 (-)   → 基
# 字符之间 → 米
# 单词之间 → 米米（两字符间多一个米）
DOT  = '哈'
DASH = '基'
SEP  = '米'


def _text_to_morse(text: str) -> str:
    """将文本转换为摩斯密码（用 . 和 - 表示）"""
    result_parts = []
    words = text.upper().split()
    for wi, word in enumerate(words):
        chars = []
        for ch in word:
            if ch in MORSE_TABLE:
                chars.append(MORSE_TABLE[ch])
        if chars:
            result_parts.append(' '.join(chars))
        if wi < len(words) - 1 and chars:
            result_parts.append('/')
    return ' '.join(result_parts)


def _morse_to_hajimi(morse: str) -> str:
    """将 .- 摩斯密码转换为 哈基米 表示"""
    result = []
    for i, ch in enumerate(morse):
        if ch == '.':
            result.append(DOT)
        elif ch == '-':
            result.append(DASH)
        elif ch == ' ':
            result.append(SEP)
        elif ch == '/':
            if result and result[-1] != SEP:
                result.append(SEP)
            result.append(SEP)
    return ''.join(result)


# ── 创建 MCP 服务器 ───────────────────────────────────────────────────
mcp = FastMCP("摩斯密码转换器")


# ── 工具 1：摩斯密码编码（需鉴权） ─────────────────────────────────────
@mcp.tool()
def morse_encode(text: str, token: str) -> str:
    """
    把任意一段话按照摩斯密码转换成"哈""基""咪"三个字符。
    需要提供有效的鉴权 token。

    :param text: 要转换的文本（支持英文、数字、标点）
    :param token: 鉴权 token，通过 get_token 工具获取
    :return: 哈基咪格式的摩斯密码字符串
    """
    if token != AUTH_TOKEN:
        return "[错误] 鉴权失败：token 无效，请使用 get_token 工具获取正确的 token"
    if not text or not text.strip():
        return "[错误] 输入文本不能为空"

    morse = _text_to_morse(text)
    if not morse.strip():
        return "[提示] 输入文本中没有可转换的字符（仅支持英文、数字和常见标点）"

    result = _morse_to_hajimi(morse)
    return result


# ── 工具 2：获取 token（无需鉴权） ─────────────────────────────────────
@mcp.tool()
def get_token() -> str:
    """
    返回鉴权所需的 token。此工具不需要鉴权即可调用。

    :return: 当前有效的鉴权 token
    """
    return AUTH_TOKEN


# ── 启动入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
