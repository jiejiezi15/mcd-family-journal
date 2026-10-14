---
name: mcd-crew-catering
description: 麦当劳企业团餐（班组 / 团队订餐）方案助手。基于麦当劳官方 MCP 的团餐场景（beType=6），按人数与预算自动搭配套餐、查询助餐服务、领取可用优惠券、计算人均实付，输出可直接对比的 Top3 方案，并在下单前强制二次确认。当用户提出班组订餐、团餐、加班订餐、给若干人订麦当劳、团餐预算规划、助餐服务查询等需求时使用本技能。
agent_created: true
---

# 麦当劳班组团餐助手

## Overview

把「十几个人加班，订什么麦当劳」这类模糊需求，变成三套可对比、可直接下单的团餐方案。

覆盖完整链路：确认人数与预算 → 定位可配送门店 → 拉取菜单与套餐详情 → 查询团餐助餐服务 → 领取优惠券 → 计算人均实付 → 输出 Top3 方案 → 用户确认后下单 → 提示可用积分与抽奖。

差异化在于吃透官方团餐场景（`beType=6`）：这是麦当劳 MCP 中唯一带 **助餐服务（`gmServiceCode`）** 的业务形态，也是唯一由官方主动要求「引导用户提供人数与预算」的场景。

## 前置条件

开始流程前，确认麦当劳 MCP 连接器（服务名 `mcd-mcp`）已启用。若工具调用返回鉴权失败，提示用户在 WorkBuddy 中关闭再开启一次连接器后重试；仍失败则运行自检脚本定位：

```bash
python3 scripts/check_mcp.py
```

## 核心流程

### Step 1 · 收集四项输入

必须拿到四项信息才可继续，缺哪项补问哪项，一次只问一项：

| 输入 | 说明 | 缺失时的处理 |
|---|---|---|
| 人数 | 参与订餐总人数 | 必问，用于计算份数与人均 |
| 人均预算 | 单位：元 | 必问，官方团餐场景要求提供预算与人数 |
| 配送地址 | 从已有地址中选择，或新建 | 调 `delivery-query-addresses` 列出 |
| 就餐时间 | 立即配送或预约时间 | 预约时全程携带 `reservationDate`，格式 `yyyy-MM-dd HH:mm` |

### Step 2 · 定位可配送门店

1. 调 `delivery-query-addresses` 取得 `addressId`。列表为空则引导 `delivery-create-address` 新建。
2. 调 `delivery-query-stores`，传 `addressId` 与 `beType=6`（企业团餐）。
3. 从返回中取 `storeCode` 与 `beCode`，后续所有调用都要带上这两个值。

### Step 3 · 拉取菜单与套餐详情

1. 调 `query-meals`，传 `storeCode`、`orderType=2`、`beType=6`、`beCode`。
2. 对候选套餐调 `query-meal-detail` 取套餐组成与特制项（`modification`）。

团餐场景按预算带搭配，规则如下：

| 人均预算 | 搭配结构 |
|---|---|
| 20 元以下 | 小食 |
| 20–30 元 | 汉堡 + 小食，或汉堡 + 饮料 |
| 30–40 元 | 汉堡 + 薯条/小食 + 饮料 |
| 40–50 元 | 汉堡 + 薯条 + 小食 + 饮料 |
| 50 元以上 | 丰富组合，优先不重复小食 |

### Step 4 · 查询助餐服务（团餐关键步骤）

调 `query-meal-assistance`，传 `storeCode`、`orderType=2`、`beType=6`、`beCode`，取回 `gmServiceCode`。

该编码是团餐专属参数，`calculate-price` 与 `create-order` 都必须携带，缺失会导致计价或下单失败。

### Step 5 · 领取优惠券

先调 `available-coupons` 列出可领券，再调 `auto-bind-coupons` 一键领取，随后用 `query-my-coupons` 确认券已到账。记录 `couponId` 与 `couponCode`，供计价使用。

### Step 6 · 计价

调 `calculate-price`，携带 `storeCode`、`orderType=2`、`beType=6`、`beCode`、`gmServiceCode`、`items`（含 `productCode`、`quantity`、`couponId`、`couponCode`）、`needTableware`。

**返回的价格字段单位为分，展示前必须除以 100 转为元。**

返回中的 `enjoyable.balance` 是「再凑多少可享下一档优惠」的门槛差额（同样为分），`enjoyable.realDiscount` 是对应的折扣值。团餐金额大，差额往往不大，提示用户是否追加到门槛，**由用户决定，不擅自加购**。

实测样例：巨无霸 ×2 + 可口可乐中杯 ×2，商品 8000 分、配送费 600 分、打包费 220 分，应付 8820 分（88.20 元），提示「再凑 220 元可享 7.8 折」。

### Step 7 · 输出 Top3 方案

按人均实付从低到高输出三套方案，每套包含：门店名称、套餐构成、单份价格、份数、优惠明细、配送费、总价、人均实付、与预算的差额。

用表格呈现，并标出推荐项与理由。模板见 `assets/plan-template.md`。

### Step 8 · 下单确认闸门

**未经用户明确确认，绝不调用 `create-order`。**

确认前需完整复述：门店、套餐构成、份数、优惠券、总价、人均实付、配送地址与时间。收到明确确认后再调 `create-order`，此时 `gmServiceCode` 与 `addressId` 为必传，团餐场景不传 `takeWayCode`。

下单成功后引导用户通过支付链接完成支付，并提示可回复「支付完成」以查询最新订单状态。

### Step 9 · 积分与抽奖提示

下单完成后，调 `query-my-account` 查询积分，调 `query-lottery-info` 查询在跑的抽奖活动，顺带提示可用积分是否够兑换或参与。此环节仅作提示，不代用户操作兑换。

## 参数传递速查

同一个门店的两个编码必须成对传递，顺序不可颠倒：

| 场景 | beType | orderType | beCode | 特殊参数 |
|---|---|---|---|---|
| 团餐 | 6 | 2 | 必传，来自 `delivery-query-stores` | `gmServiceCode` 必传 |
| 麦乐送 | 2 | 2 | 必传，来自 `delivery-query-stores` | — |
| 到店自取 | 1 | 1 | 不传 | `takeWayCode` 必传 |
| 得来速 | 5 | 1 | 必传，来自 `query-nearby-stores` | `takeWayCode` 必传 |

完整工具清单见 `references/mcp-tools.md`。

## 错误处理

| 现象 | 判断 | 处理 |
|---|---|---|
| 401 | Token 无效、过期或缺失 `Bearer ` 前缀 | 检查请求头格式为 `Bearer <token>`（中间一个空格） |
| 429 | 触发限流，600 次/分钟 | 降低调用频率，批量拉菜单时加间隔，勿误判为 Token 失效 |
| 门店列表为空 | 地址不在配送范围 | 换地址或改用到店场景 |
| 计价失败 | 多为 `gmServiceCode` 缺失或商品编码失效 | 重跑 Step 4，并重新拉取菜单确认编码 |

## 边界

- 不代用户完成支付，不代用户兑换积分或参与抽奖。
- 不记录、不缓存、不输出用户的 Token 与账号凭证。
- 未文档化接口稳定性无保障，不作为核心依赖。

## Resources

- `references/mcp-tools.md` — 麦当劳 MCP 工具全景与团餐链路参数细节
- `references/crew-catering-playbook.md` — 团餐搭配策略、预算算法与实战话术
- `scripts/check_mcp.py` — 连接器连通性自检
- `assets/plan-template.md` — Top3 方案输出模板
