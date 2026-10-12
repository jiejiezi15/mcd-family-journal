# 麦当劳 MCP 工具全景

服务端地址：`https://mcp.mcd.cn`（Streamable HTTP）
协议版本：仅支持 MCP 2025-06-18 及之前
限流：600 次/分钟，超限返回 429

## 工具清单（实测 35 个，官方文档列出 33 个）

### 点餐下单（11）

| 工具 | 用途 |
|---|---|
| `query-nearby-stores` | 到店场景查询附近门店（beType=1 自取 / 5 得来速） |
| `delivery-query-addresses` | 查询已有配送地址列表 |
| `delivery-create-address` | 新增配送地址 |
| `delivery-query-stores` | 外送场景按地址查可配送门店（beType=2 麦乐送 / 6 团餐） |
| `query-meals` | 查询门店可售餐品列表 |
| `query-meal-detail` | 按商品编码查套餐组成与特制项 |
| `calculate-price` | 计价，含优惠券与助餐服务 |
| `create-order` | 创建订单，返回支付链接 |
| `query-order` | 查询订单详情与状态 |
| `order-list` | 查询订单列表 |
| `cancel-order` | 取消订单 |

### 优惠券（6）

| 工具 | 用途 |
|---|---|
| `available-coupons` | 麦麦省可领券列表 |
| `auto-bind-coupons` | 一键领取全部可领券 |
| `query-my-coupons` | 我的优惠券 |
| `query-store-coupons` | 当前门店可用券 |
| `query-survey-coupon` | 问卷券（未文档化） |
| `query-promotions` | 促销活动（未文档化） |

### 积分与商城（9）

| 工具 | 用途 |
|---|---|
| `query-my-account` | 积分账户信息 |
| `mall-points-products` | 积分兑换商品列表 |
| `mall-product-detail` | 积分兑换商品详情 |
| `mall-create-order` | 积分兑换下单 |
| `mall-order-list` / `mall-order-detail` | 商城订单查询 |
| `draw-lottery` | 发起抽奖 |
| `query-lottery-info` | 抽奖活动信息 |
| `query-my-prizes` | 我的奖品 |

### 其他

| 业务域 | 工具 |
|---|---|
| 营养（1） | `list-nutrition-foods` |
| 活动派对（6） | `campaign-calendar`、`query-party-city`、`query-party-store`、`query-party-store-date`、`query-party-store-session`、`party-order-create` |
| 团餐（1） | `query-meal-assistance` |
| 基础（1） | `now-time-info` |

未文档化接口（`query-survey-coupon`、`query-promotions`）稳定性无保障，可做加分项，不作为核心依赖。

## 团餐链路参数细节

### beType / orderType 映射

| 场景 | beType | orderType | beCode 来源 | 是否传 beCode |
|---|---|---|---|---|
| 到店自取 | 1 | 1 | — | 不传，传了会报错 |
| 麦乐送 | 2 | 2 | `delivery-query-stores` | 必传 |
| 得来速 | 5 | 1 | `query-nearby-stores` | 必传 |
| 企业团餐 | 6 | 2 | `delivery-query-stores` | 必传 |

`storeCode` 与 `beCode` 必须成对传递，来源不同场景不可混用。

### 调用顺序（团餐）

```
delivery-query-addresses
  → delivery-query-stores(addressId, beType=6)      取 storeCode, beCode
  → query-meals(storeCode, orderType=2, beType=6, beCode)
  → query-meal-detail(...)                          套餐组成、modification
  → query-meal-assistance(storeCode, orderType=2, beType=6, beCode)  取 gmServiceCode
  → available-coupons / auto-bind-coupons           取 couponId, couponCode
  → calculate-price(..., gmServiceCode, items)      价格单位：分
  → 【用户确认】
  → create-order(..., addressId, gmServiceCode)     团餐不传 takeWayCode
```

### 易错点

1. **`gmServiceCode` 必须在 `calculate-price` 之前拿到**，且 `create-order` 同样必传，漏传导致计价或下单失败。
2. **价格单位为分**，展示前除以 100。
3. **特制项 `modification` 的 key 规则**：选中项用 `selectedKey`；同组中未选中项若 `unselectedKey` 非空，也必须传入该 key。缺项会计价报错。
4. **预约场景**全程携带 `reservationDate`（`yyyy-MM-dd HH:mm`），非预约场景不传。
5. **`takeWayCode`** 仅 `orderType=1` 必传，取值来自 `calculate-price` 返回的 `takeWayList[].code`。
6. **401 与 429 要分清**：401 是 Token 问题（常见原因是请求头少了 `Bearer ` 前缀），429 是限流。

## 官方团餐搭配建议

来自 `query-meals` 工具描述，按人均预算分档：

| 人均预算 | 搭配结构 |
|---|---|
| 20 元以下 | 小食 |
| 20–30 元 | 汉堡 + 小食，或汉堡 + 饮料 |
| 30–40 元 | 汉堡 + 薯条/小食 + 饮料 |
| 40–50 元 | 汉堡 + 薯条 + 小食 + 饮料 |
| 50 元以上 | 丰富组合，优先不重复小食 |
