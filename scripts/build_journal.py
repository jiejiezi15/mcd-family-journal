#!/usr/bin/env python3
"""生成「我家与麦当劳」家庭消费档案海报。

直接调用麦当劳 MCP 拉取真实历史订单，统计后渲染成一张可分享的 HTML 海报。
全部数据来自用户本人账号，脚本不上传任何内容，产物仅保存在本地。

用法:
    export MCD_MCP_TOKEN=<你的Token>
    python3 scripts/build_journal.py                    # 输出到当前目录
    python3 scripts/build_journal.py --out ~/Desktop    # 指定输出目录

注意: 产物包含真实消费记录，属于个人信息，不要提交到公开仓库。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

DEFAULT_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-06-18"

KID_KEYWORDS = ("开心乐园", "乐园餐")

CATEGORY_RULES = [
    ("汉堡", ("堡", "汉堡")),
    ("小食", ("薯条", "鸡翅", "麦乐鸡", "鸡块", "鸡排", "薯饼", "玉米", "脆汁鸡", "鸡球", "鸡柳", "酥酥")),
    ("饮料", ("可乐", "雪碧", "咖啡", "茶", "牛奶", "果汁", "麦炫酷", "怡泉", "柠", "纯悦", "奶铁", "美式", "可可")),
    ("甜品", ("派", "麦旋风", "新地", "冰淇淋", "脆脆")),
]

TASTE_RULES = [
    ("辣党", ("辣",)),
    ("鸡肉派", ("鸡",)),
    ("牛肉党", ("牛", "安格斯")),
    ("鱼鲜党", ("鱼", "鳕")),
    ("薯条控", ("薯条", "薯饼")),
    ("甜品胃", ("派", "麦旋风", "新地", "冰淇淋")),
    ("咖啡因", ("咖啡", "奶铁", "美式")),
    ("汽水党", ("可乐", "雪碧", "怡泉", "麦炫酷")),
]


MODE_TEXT = {
    "personal": {
        "title": "我与麦当劳",
        "badge": "麦当劳个人档案",
        "taste": "你的口味画像",
        "plate": "你的餐盘构成",
        "first_stat": "你吃过",
    },
    "family": {
        "title": "我家与麦当劳",
        "badge": "麦当劳家庭档案",
        "taste": "一家人的口味画像",
        "plate": "这家人的餐盘构成",
        "first_stat": "全家吃过",
    },
}


class McpClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.session_id = None

    def _post(self, payload, expect_session=False):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.token,
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
                if expect_session:
                    self.session_id = resp.headers.get("Mcp-Session-Id") or self.session_id
        except urllib.error.HTTPError as exc:
            raise RuntimeError("HTTP " + str(exc.code)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

        text = raw.decode("utf-8", errors="replace")
        if "text/event-stream" in ctype:
            for line in text.splitlines():
                if line.startswith("data:"):
                    text = line[5:].strip()
                    break
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def start(self):
        self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcd-family-journal", "version": "1.0.0"},
                },
            },
            expect_session=True,
        )
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def call_tool(self, name, arguments=None):
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        content = (resp.get("result") or {}).get("content") or []
        for item in content:
            if item.get("type") == "text":
                return extract_json(item.get("text", ""))
        return {}


def extract_json(text):
    """MCP 工具返回的文本带 Markdown 说明，真正的 JSON 在 Original Response 之后。"""
    body = text.strip()
    marker = "## Original Response"
    if marker in body:
        body = body.split(marker, 1)[1].strip()
    body = body.strip("`").strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        pass
    start = body.find("{")
    end = body.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(body[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def classify(name):
    for label, keys in CATEGORY_RULES:
        for key in keys:
            if key in name:
                return label
    return "其他"


def is_kid_item(name):
    return any(k in name for k in KID_KEYWORDS)


def analyze(orders):
    stores = Counter()
    items = Counter()
    cats = Counter()
    months = Counter()
    kid_orders = []
    kid_flavor = Counter()
    total_amount = 0.0
    times = []

    for order in orders:
        store = order.get("storeName") or "未知门店"
        stores[store] += 1
        created = order.get("createTime") or ""
        if created:
            times.append(created)
            months[created[:7]] += 1
        try:
            total_amount += float(order.get("realTotalAmount") or 0)
        except ValueError:
            pass

        has_kid = False
        for prod in order.get("orderProductList") or []:
            pname = prod.get("productName") or ""
            qty = int(prod.get("quantity") or 1)
            items[pname] += qty
            cats[classify(pname)] += qty
            if is_kid_item(pname):
                has_kid = True
                kid_flavor[pname] += qty
            for sub in prod.get("comboItemList") or []:
                sname = sub.get("name") or sub.get("productName") or ""
                sqty = int(sub.get("quantity") or 1)
                if sname:
                    items[sname] += sqty
                    cats[classify(sname)] += sqty
                    if is_kid_item(sname):
                        has_kid = True
                        kid_flavor[sname] += sqty
        if has_kid:
            kid_orders.append(order)

    kid_orders.sort(key=lambda o: o.get("createTime") or "")
    return {
        "stores": stores,
        "items": items,
        "cats": cats,
        "months": months,
        "kid_orders": kid_orders,
        "kid_flavor": kid_flavor,
        "total_amount": total_amount,
        "times": sorted(times),
        "count": len(orders),
    }


def render_stat(value, unit, label):
    return (
        '<div class="stat"><div class="n">' + str(value) + "<small>" + unit + "</small></div>"
        '<div class="l">' + label + "</div></div>"
    )


def render_bars(counter, unit="份"):
    total = sum(counter.values()) or 1
    colors = {"汉堡": "#DA291C", "小食": "#FFC72C", "饮料": "#4A90D9", "甜品": "#E88BB0", "其他": "#B8B0A5"}
    html = []
    for name, value in counter.most_common():
        pct = value / total * 100
        html.append(
            '<div class="bar"><div class="t"><span>' + name + "</span><span>"
            + str(value) + " " + unit + " · " + str(round(pct)) + "%</span></div>"
            '<div class="track"><div class="fill" style="width:' + str(round(pct)) + "%;background:"
            + colors.get(name, "#B8B0A5") + '"></div></div></div>'
        )
    return "".join(html)


def render_months(counter):
    if not counter:
        return ""
    keys = sorted(counter.keys())
    peak = max(counter.values()) or 1
    latest = keys[-1]
    html = []
    for key in keys:
        height = max(3, round(counter[key] / peak * 70))
        cls = "m now" if key == latest else "m"
        html.append(
            '<div class="' + cls + '"><i style="height:' + str(height) + 'px"></i><b>'
            + key[5:7] + "月</b></div>"
        )
    return "".join(html)


def render_top_items(counter, limit=6):
    html = []
    for i, (name, value) in enumerate(counter.most_common(limit)):
        pct = 0
        top = counter.most_common(1)[0][1] if counter else 1
        pct = round(value / top * 100)
        html.append(
            '<div class="bar"><div class="t"><span>' + str(i + 1) + ". " + name
            + "</span><span>" + str(value) + " 份</span></div>"
            '<div class="track"><div class="fill" style="width:' + str(pct)
            + '%;background:#FFC72C"></div></div></div>'
        )
    return "".join(html) or '<div class="empty">暂无数据</div>'


def render_taste(items):
    scores = []
    for label, keys in TASTE_RULES:
        score = sum(qty for name, qty in items.items() if any(k in name for k in keys))
        if score > 0:
            scores.append((label, score))
    scores.sort(key=lambda x: -x[1])
    if not scores:
        return '<span class="tag">数据太少，再吃几顿看看</span>'
    top = scores[0][1]
    out = []
    for label, score in scores[:7]:
        cls = "tag hot" if score == top else "tag"
        out.append('<span class="' + cls + '">' + label + " ×" + str(score) + "</span>")
    return "".join(out)


def render_kid_block(stat, mode):
    if mode != "family":
        return ""
    kid_orders = stat["kid_orders"]
    if not kid_orders:
        return (
            '<div class="sec"><h2>带娃记录</h2><div class="empty">账号里还没有开心乐园餐订单。'
            "下次带娃吃麦当劳时点一份儿童餐，这里就会长出娃的成长册。</div></div>"
        )
    first = kid_orders[0]
    first_time = (first.get("createTime") or "")[:10]
    first_store = first.get("storeName") or "未知门店"
    flavor = stat["kid_flavor"].most_common(1)
    flavor_text = flavor[0][0] + " ×" + str(flavor[0][1]) if flavor else "暂无"
    rows = [
        ("第一次带娃吃", first_time + " · " + first_store),
        ("带娃吃过", str(len(kid_orders)) + " 次"),
        ("娃最常点", flavor_text),
        ("最近一次", (kid_orders[-1].get("createTime") or "")[:10]),
    ]
    body = "".join(
        '<div class="row"><span>' + k + "</span><span>" + v + "</span></div>" for k, v in rows
    )
    return '<div class="sec"><h2>娃的麦当劳成长册</h2><div class="kid">' + body + "</div></div>"


def build_html(stat, points, mode):
    text = MODE_TEXT[mode]
    times = stat["times"]
    span = ""
    if times:
        span = times[0][:10] + " 至 " + times[-1][:10]
    top_store = stat["stores"].most_common(1)
    top_item = stat["items"].most_common(1)
    amount = round(stat["total_amount"], 1)

    stats = "".join(
        [
            render_stat(stat["count"], " 顿", text["first_stat"]),
            render_stat(amount, " 元", "累计花费"),
            render_stat(top_store[0][0][:6] if top_store else "—", "", "最常去的店"),
            render_stat(top_item[0][0][:6] if top_item else "—", "", "最爱的单品"),
        ]
    )

    template = (Path(__file__).resolve().parent.parent / "assets" / "journal-template.html").read_text(
        encoding="utf-8"
    )
    foot_note = "账号积分 " + str(points) + " · 数据来自麦当劳官方 MCP" if points else "数据来自麦当劳官方 MCP"
    return (
        template.replace("{{BADGE}}", text["badge"])
        .replace("{{TITLE}}", text["title"])
        .replace("{{SUBTITLE}}", span + " · 共 " + str(stat["count"]) + " 顿")
        .replace("{{STATS}}", stats)
        .replace("{{KID_BLOCK}}", render_kid_block(stat, mode))
        .replace("{{TASTE_TITLE}}", text["taste"])
        .replace("{{PLATE_TITLE}}", text["plate"])
        .replace("{{TASTE_TAGS}}", render_taste(stat["items"]))
        .replace("{{NUTRITION}}", render_bars(stat["cats"]))
        .replace("{{MONTH_BARS}}", render_months(stat["months"]))
        .replace("{{TOP_ITEMS}}", render_top_items(stat["items"]))
        .replace("{{FOOT_NOTE}}", foot_note)
        .replace("{{FOOT_TIME}}", "生成于 " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    )


def main():
    parser = argparse.ArgumentParser(description="生成麦当劳家庭消费档案海报")
    parser.add_argument("--out", default=".", help="输出目录，默认当前目录")
    parser.add_argument(
        "--mode",
        choices=["auto", "personal", "family"],
        default="auto",
        help="auto=有儿童餐订单则出家庭版，否则个人版；personal=强制个人版；family=强制家庭版",
    )
    parser.add_argument("--url", default=os.environ.get("MCD_MCP_URL", DEFAULT_URL))
    args = parser.parse_args()

    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        print("未读取到环境变量 MCD_MCP_TOKEN")
        print("先执行: export MCD_MCP_TOKEN=<你的Token>")
        return 1

    client = McpClient(args.url, token)
    try:
        client.start()
    except RuntimeError as exc:
        print("连接 MCP 失败: " + str(exc))
        if "401" in str(exc) or "403" in str(exc):
            print("常见原因: Authorization 头缺少 'Bearer ' 前缀，或 Token 已失效")
        return 1

    raw_orders = client.call_tool("order-list")
    orders = (raw_orders.get("data") or {}).get("list") or []
    if not orders:
        print("账号中没有历史订单，无法生成档案")
        return 1

    points = ""
    try:
        account = client.call_tool("query-my-account")
        data = account.get("data") or {}
        points = data.get("availablePoints") or data.get("points") or ""
    except Exception:
        points = ""

    stat = analyze(orders)
    mode = args.mode
    if mode == "auto":
        mode = "family" if stat["kid_orders"] else "personal"
    html = build_html(stat, points, mode)

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / ("mcd-journal-" + mode + ".html")
    out_file.write_text(html, encoding="utf-8")

    print("模式: " + ("个人版" if mode == "personal" else "家庭版"))
    print("已读取 " + str(len(orders)) + " 笔历史订单")
    print("带娃订单: " + str(len(stat["kid_orders"])) + " 笔")
    print("海报已生成: " + str(out_file))
    print("提示: 含真实消费记录，请勿提交到公开仓库")
    return 0


if __name__ == "__main__":
    sys.exit(main())
