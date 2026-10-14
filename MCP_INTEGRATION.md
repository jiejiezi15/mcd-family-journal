# MCP 集成说明

本技能基于麦当劳官方 MCP 服务（`https://mcp.mcd.cn`，Streamable HTTP）构建，全部统计基于真实接口返回的真实历史订单，无任何模拟或编造数据。

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

脚本 `scripts/build_journal.py` 直接以 JSON-RPC 访问 MCP，不依赖任何第三方库（仅标准库 `urllib`）：

```
initialize                            建立会话
  → notifications/initialized         完成握手
  → tools/call  order-list            全部历史订单（核心数据源）
  → tools/call  query-my-account      账号积分（页脚展示）
  → 本地统计：门店 / 单品 / 品类 / 口味 / 月度 / 儿童餐
  → 生成两套视角（个人版、家庭版）的 HTML 片段
  → 注入 assets/journal-template.html
  → 输出单文件 mcd-journal.html
```

## 工具明细

### order-list（核心）

无入参，返回 `data.list[]`，单条结构：

| 字段 | 说明 |
|---|---|
| `orderId` | 订单编码 |
| `createTime` | 下单时间，用于月度节奏与时间跨度 |
| `storeName` / `storeCode` | 门店，用于统计最常去的店 |
| `orderProductList[]` | 商品列表，含 `productName`、`quantity`、`comboItemList` |
| `comboItemList[]` | 套餐子项，含 `name`、`quantity` |
| `realTotalAmount` | 实付金额，单位元 |

统计时套餐会展开子项，因此"最爱的单品"可能来自套餐内部。

### query-my-account

取账号积分，仅用于页脚展示，失败时静默跳过、不影响主流程。

### 可选扩展

| 工具 | 可扩展方向 |
|---|---|
| `query-order` | 按订单号取详情，补充单笔订单的配送与状态信息 |
| `query-my-prizes` | 抽奖奖品记录，可加入"这一年薅到的玩具"模块 |
| `mall-order-list` | 积分商城订单，可区分"买的"与"兑的" |
| `campaign-calendar` | 活动日历，用于解释消费密集期（某月吃得多的原因） |
| `list-nutrition-foods` | 营养库，可把"餐盘构成"升级为营养结构 |

## 响应解析的关键点

MCP 工具返回的 `content[0].text` **不是纯 JSON**，而是带 Markdown 说明的文本，真正的 JSON 位于末尾 `## Original Response` 之后。直接用 `json.loads` 解析会失败。

处理策略：

1. 按 `## Original Response` 切分，取其后内容
2. 去除可能的代码围栏
3. 尝试 `json.loads`
4. 失败则退化为截取首个 `{` 到最后一个 `}` 之间的内容再解析

这个坑在纯对话式调用中不会遇到（模型能读懂说明文本），但脚本化调用必须处理。

## 统计口径

| 指标 | 规则 |
|---|---|
| 顿数 | 订单条数 |
| 累计花费 | `realTotalAmount` 求和 |
| 常去门店 | `storeName` 计数取最高 |
| 最爱单品 | 展开商品与套餐子项后按 `quantity` 计数 |
| 口味画像 | 商品名关键词匹配：辣 / 鸡 / 牛 / 鱼 / 薯条 / 甜品 / 咖啡 / 汽水 |
| 餐盘构成 | 汉堡、小食、饮料、甜品四类占比 |
| 带娃订单 | 商品名含「开心乐园」或「乐园餐」 |

## 交互实现

两种视角的 HTML 片段在生成时一次性算出，以 JSON 注入页面，由原生 JS 完成切换与展开，因此：

- 单文件、无外部依赖、离线可用
- 切换视角不需要重新请求 MCP
- 注入时对 `</` 做转义，避免提前终止 `<script>`

## 错误处理

| 现象 | 原因 | 处理 |
|---|---|---|
| 401 / 403 | Token 无效，或请求头缺 `Bearer ` 前缀 | 检查 Authorization 格式 |
| 429 | 超过 600 次/分钟 | 稍后重试 |
| 返回空订单 | 账号无历史订单 | 如实告知，不生成空档案 |
| 解析为空 | 响应格式变更 | 检查 `## Original Response` 标记是否仍存在 |

## 数据流向

所有数据只在本机内存中处理，脚本不发起任何除 MCP 之外的网络请求，产物仅写入用户指定的本地目录。
