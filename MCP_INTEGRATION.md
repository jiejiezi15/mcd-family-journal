# MCP 集成说明

本技能基于麦当劳官方 MCP 服务（`https://mcp.mcd.cn`，Streamable HTTP）构建，全部能力来自真实接口调用，无本地模拟数据。

## 接入配置

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

协议版本：MCP 2025-06-18 及之前。限流：600 次/分钟，超限返回 429。

## 调用流程

```
┌─ 输入：人数 + 人均预算 + 地址 + 时间
│
├─ 1. delivery-query-addresses          取 addressId
│     └─ 无地址 → delivery-create-address 新建
│
├─ 2. delivery-query-stores(beType=6)   取 storeCode + beCode
│
├─ 3. query-meals(orderType=2, beType=6, beCode)
│     └─ 按预算分档挑选候选商品
│
├─ 4. query-meal-detail(...)            套餐组成、特制项 modification
│
├─ 5. query-meal-assistance(beType=6)   取 gmServiceCode  ★ 团餐专属
│
├─ 6. available-coupons → auto-bind-coupons → query-my-coupons
│     └─ 取 couponId + couponCode
│
├─ 7. calculate-price(gmServiceCode, items, coupon)
│     └─ 返回单位为「分」，展示前 ÷100
│
├─ 8. 输出 Top3 方案（省钱 / 均衡 / 加料）
│
├─ 9. ★ 用户明确确认 ★
│
├─ 10. create-order(addressId, gmServiceCode, items)
│
└─ 11. query-my-account + query-lottery-info  积分与抽奖提示
```

## 工具明细

### 地址与门店

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `delivery-query-addresses` | 无 | 列出已有配送地址，团餐场景的起点 |
| `delivery-create-address` | 地址信息 | 无地址时引导新建，避免流程中断 |
| `delivery-query-stores` | `addressId`、`beType=6` | 按地址筛出支持团餐配送的门店 |
| `query-nearby-stores` | `city`、`keyword`、`beType` | 到店场景备用路径 |

### 菜单与详情

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `query-meals` | `storeCode`、`orderType=2`、`beType=6`、`beCode` | 取当前门店可售餐品，工具描述内含官方团餐预算分档规则 |
| `query-meal-detail` | 商品编码 | 取套餐组成与特制项，供 `modification` 传参 |

### 助餐服务（核心差异点）

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `query-meal-assistance` | `storeCode`、`orderType=2`、`beType=6`、`beCode` | 返回门店支持的团餐助餐服务，产出 `gmServiceCode` |

`gmServiceCode` 是团餐场景的强制参数，`calculate-price` 与 `create-order` 都必须携带。绝大多数同类项目不涉及该接口，这是本技能的主要差异化来源。

### 优惠券

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `available-coupons` | — | 列出可领券，判断哪些适用当前组合 |
| `auto-bind-coupons` | — | 一键领取，幂等 |
| `query-my-coupons` | — | 确认到账状态，避免谎报优惠 |

### 计价与下单

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `calculate-price` | `storeCode`、`beCode`、`beType`、`gmServiceCode`、`items[]`、`needTableware` | 含券、含助餐服务的准确价格 |
| `create-order` | 同上 + `addressId`、`gmServiceCode` | 创建订单并返回支付链接 |

计价返回字段单位为**分**，展示前除以 100 转为元。团餐场景 `orderType=2`，**不传** `takeWayCode`（该参数仅到店场景 `orderType=1` 必传）。

### 积分与抽奖

| 工具 | 参数 | 业务价值 |
|---|---|---|
| `query-my-account` | — | 查询可用积分，判断够不够兑换 |
| `query-lottery-info` | — | 查询在跑的抽奖活动，下单后顺带提示 |

此环节仅作提示，不代用户操作兑换或抽奖。

## 参数配对规则

`storeCode` 与 `beCode` 必须成对传递，不同场景来源不同：

| 场景 | beType | orderType | beCode 来源 | 特殊参数 |
|---|---|---|---|---|
| 企业团餐 | 6 | 2 | `delivery-query-stores` | `gmServiceCode` 必传 |
| 麦乐送 | 2 | 2 | `delivery-query-stores` | — |
| 到店自取 | 1 | 1 | 不传 | `takeWayCode` 必传 |
| 得来速 | 5 | 1 | `query-nearby-stores` | `takeWayCode` 必传 |

## 错误处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 401 | Token 无效、过期，或请求头缺 `Bearer ` 前缀 | 检查 Authorization 格式 |
| 429 | 超过 600 次/分钟 | 降低调用频率，勿误判为 Token 失效 |
| 门店列表为空 | 地址不在配送范围 | 换地址或转用其他场景 |
| 计价失败 | `gmServiceCode` 缺失或商品编码失效 | 重取助餐服务并刷新菜单 |

## 未文档化接口

实测服务端暴露 35 个工具，官方文档列出 33 个，多出 `query-survey-coupon` 与 `query-promotions`。二者稳定性无保障，本技能不作为核心依赖，仅在自检脚本中提示其可用性。
