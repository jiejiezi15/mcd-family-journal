#!/usr/bin/env python3
"""麦当劳 MCP 连接器自检脚本。

验证 Token 是否有效、服务端是否可达、团餐链路所需工具是否齐全。
仅用于本地排障，不写入任何凭证，不产生任何业务副作用。

用法:
    export MCD_MCP_TOKEN=<你的Token>
    python3 scripts/check_mcp.py

可选环境变量:
    MCD_MCP_URL  服务端地址，默认 https://mcp.mcd.cn
"""

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"

REQUIRED_TOOLS = [
    "delivery-query-addresses",
    "delivery-query-stores",
    "query-meals",
    "query-meal-detail",
    "query-meal-assistance",
    "available-coupons",
    "auto-bind-coupons",
    "calculate-price",
    "create-order",
    "query-my-account",
    "query-lottery-info",
]


def build_request(url, payload, session_id=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer " + os.environ["MCD_MCP_TOKEN"],
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    body = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(url, data=body, headers=headers, method="POST")


def parse_response(raw, content_type):
    text = raw.decode("utf-8", errors="replace")
    if "text/event-stream" in (content_type or ""):
        for line in text.splitlines():
            if line.startswith("data:"):
                text = line[5:].strip()
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"__raw__": text[:400]}


def call(url, method, params, session_id=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    req = build_request(url, payload, session_id)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return parse_response(resp.read(), resp.headers.get("Content-Type")), resp.headers.get("Mcp-Session-Id"), None
    except urllib.error.HTTPError as exc:
        return None, None, exc.code
    except urllib.error.URLError as exc:
        return None, None, str(exc.reason)


def main():
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        print("未读取到环境变量 MCD_MCP_TOKEN")
        print("先执行: export MCD_MCP_TOKEN=<你的Token>")
        return 1

    url = os.environ.get("MCD_MCP_URL", DEFAULT_URL)
    print("服务端: " + url)

    init_params = {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "mcd-crew-catering-checker", "version": "1.0.0"},
    }
    result, session_id, err = call(url, "initialize", init_params)
    if err == 401 or err == 403:
        print("连接失败: 鉴权被拒（HTTP " + str(err) + "）")
        print("常见原因: Authorization 头缺少 'Bearer ' 前缀，或 Token 已失效")
        return 1
    if err == 429:
        print("连接失败: 触发限流（HTTP 429），每分钟 600 次，稍后重试")
        return 1
    if err is not None:
        print("连接失败: " + str(err))
        return 1

    server_info = (result or {}).get("result", {}).get("serverInfo", {})
    name = server_info.get("name", "未知")
    version = server_info.get("version", "未知")
    print("连接成功: " + str(name) + " v" + str(version))

    call(url, "notifications/initialized", {}, session_id)

    result, _, err = call(url, "tools/list", {}, session_id)
    if err is not None:
        print("拉取工具列表失败: " + str(err))
        return 1

    tools = (result or {}).get("result", {}).get("tools", [])
    names = [t.get("name") for t in tools]
    print("工具总数: " + str(len(names)))

    missing = [t for t in REQUIRED_TOOLS if t not in names]
    if missing:
        print("团餐链路缺失工具: " + ", ".join(missing))
        return 1

    print("团餐链路所需工具齐全")
    extra = [t for t in ("query-survey-coupon", "query-promotions") if t in names]
    if extra:
        print("可用未文档化工具: " + ", ".join(extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
