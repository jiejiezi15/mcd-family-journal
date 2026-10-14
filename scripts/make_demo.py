#!/usr/bin/env python3
"""用虚构数据生成示例档案页。

供没有麦当劳 MCP Token 的人预览效果，不需要联网、不需要凭证。
数据全部虚构，不含任何真实订单。

用法:
    python3 scripts/make_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_journal import analyze, build_html

DEMO_ORDERS = [
    {"orderId": "demo01", "createTime": "2025-11-08 12:20:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "62.5", "orderProductList": [
         {"productName": "麦辣鸡腿汉堡", "quantity": 2},
         {"productName": "薯条", "quantity": 1}, {"productName": "可口可乐", "quantity": 2}]},
    {"orderId": "demo02", "createTime": "2025-12-14 18:40:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "78.0", "orderProductList": [
         {"productName": "板烧鸡腿堡", "quantity": 2},
         {"productName": "麦乐鸡开心乐园餐", "quantity": 1},
         {"productName": "香芋派", "quantity": 2}]},
    {"orderId": "demo03", "createTime": "2026-01-03 11:50:00", "storeName": "示例·滨江路店",
     "realTotalAmount": "45.0", "orderProductList": [
         {"productName": "双层吉士汉堡", "quantity": 2}, {"productName": "雪碧", "quantity": 2}]},
    {"orderId": "demo04", "createTime": "2026-02-21 12:05:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "88.5", "orderProductList": [
         {"productName": "巨无霸", "quantity": 2}, {"productName": "麦辣鸡翅2块", "quantity": 1},
         {"productName": "汉堡开心乐园餐", "quantity": 1}, {"productName": "纯牛奶(盒装)", "quantity": 1}]},
    {"orderId": "demo05", "createTime": "2026-03-16 19:10:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "52.0", "orderProductList": [
         {"productName": "麦辣鸡腿汉堡", "quantity": 2}, {"productName": "薯条", "quantity": 1},
         {"productName": "奥利奥麦旋风", "quantity": 1}]},
    {"orderId": "demo06", "createTime": "2026-04-05 12:30:00", "storeName": "示例·滨江路店",
     "realTotalAmount": "67.0", "orderProductList": [
         {"productName": "培根芝士双牛堡", "quantity": 2},
         {"productName": "麦乐鸡开心乐园餐", "quantity": 1}, {"productName": "可乐", "quantity": 1}]},
    {"orderId": "demo07", "createTime": "2026-05-01 13:00:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "95.5", "orderProductList": [
         {"productName": "安格斯厚牛堡", "quantity": 2}, {"productName": "那么大鸡排", "quantity": 1},
         {"productName": "脆脆薯条", "quantity": 1}, {"productName": "鱼排堡开心乐园餐", "quantity": 1}]},
    {"orderId": "demo08", "createTime": "2026-06-13 12:15:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "58.0", "orderProductList": [
         {"productName": "麦辣鸡腿汉堡", "quantity": 2}, {"productName": "菠萝派", "quantity": 2}]},
    {"orderId": "demo09", "createTime": "2026-07-19 18:55:00", "storeName": "示例·滨江路店",
     "realTotalAmount": "71.5", "orderProductList": [
         {"productName": "双层深海鳕鱼堡", "quantity": 2}, {"productName": "麦辣鸡翅2块", "quantity": 1},
         {"productName": "麦乐鸡开心乐园餐", "quantity": 1}]},
    {"orderId": "demo10", "createTime": "2026-08-09 12:00:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "49.0", "orderProductList": [
         {"productName": "麦辣鸡腿汉堡", "quantity": 2}, {"productName": "薯条", "quantity": 1},
         {"productName": "锡兰红茶", "quantity": 1}]},
    {"orderId": "demo11", "createTime": "2026-09-12 12:40:00", "storeName": "示例·城市广场餐厅",
     "realTotalAmount": "83.0", "orderProductList": [
         {"productName": "板烧鸡腿堡", "quantity": 2}, {"productName": "薯条", "quantity": 1},
         {"productName": "汉堡开心乐园餐", "quantity": 1}, {"productName": "可乐", "quantity": 2}]},
    {"orderId": "demo12", "createTime": "2026-10-04 11:30:00", "storeName": "示例·滨江路店",
     "realTotalAmount": "56.5", "orderProductList": [
         {"productName": "麦香鱼", "quantity": 2}, {"productName": "香芋派", "quantity": 1},
         {"productName": "纯牛奶(盒装)", "quantity": 1}]},
]


def main():
    stat = analyze(DEMO_ORDERS)
    html = build_html(stat, 1286, "family", DEMO_ORDERS, False)
    out = Path(__file__).resolve().parent.parent / "examples" / "demo.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("示例订单 " + str(len(DEMO_ORDERS)) + " 笔，含儿童餐 "
          + str(len(stat["kid_orders"])) + " 笔")
    print("示例页面已生成: " + str(out))


if __name__ == "__main__":
    main()
