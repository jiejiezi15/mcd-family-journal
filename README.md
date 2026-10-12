# mcd-crew-catering · 麦当劳班组团餐助手

> 一句话：给十几个人订麦当劳，不用再挨个问、不用手算预算。报人数和人均预算，三套可直接下单的方案就出来了。

一个基于 [麦当劳官方 MCP](https://github.com/M-China/mcd-mcp-server) 的 WorkBuddy Skill，专攻**企业团餐（beType=6）**场景 —— 这是麦当劳 MCP 里唯一带「助餐服务」、也是官方唯一主动要求「引导用户提供人数与预算」的业务形态。

---

## 它解决什么

班组加班订餐，真实的麻烦从来不是「吃什么」，而是这四件事：

- 十几个人口味不一，凑不出一套能落地的组合
- 预算是死的，凑完单不知道人均超没超
- 优惠券散在各处，不知道哪些能用在团餐上
- 团餐有专属的助餐服务（分装、集中配送等），普通点餐流程根本不会走到那一步

本技能把这条链路整个跑通：**人数 + 预算 → 可配送门店 → 菜单与套餐 → 助餐服务 → 领券 → 人均实付 → Top3 方案 → 确认后下单**。

---

## 对话示例

```
> 班组 12 个人加班，订个麦当劳，人均 30 左右

人数 12、人均预算 30 元，总预算 360 元。
已定位可配送门店：青岛 XX 餐厅（支持团餐配送）
该门店助餐服务：统一分装 / 集中配送 / 提供餐具

| 项         | A 省钱档 | B 均衡档  | C 加料档 |
|-----------|---------|----------|---------|
| 套餐构成    | 汉堡+饮料 | 汉堡+薯条+饮料 | 汉堡+薯条+小食+饮料 |
| 单份价     | 24.5    | 29.4     | 38.0    |
| 优惠       | 满100减15 | 满100减15 | 满150减20 |
| 配送费     | 9       | 9        | 9       |
| 总价       | 303     | 361.8    | 465     |
| 人均实付    | 25.3    | 30.2     | 38.8    |

推荐方案 B，人均 30.2 元，最贴合预算且结构均衡。
确认下单请回复「方案 B 下单」。
```

下单前会完整复述门店、构成、份数、优惠、总价、人均、地址与时间，**得到明确确认才会创建订单**。

---

## 亮点

- **吃透团餐专属链路**：`query-meal-assistance` 取 `gmServiceCode`，一路带到计价与下单。绝大多数同类项目根本不会走到这一步。
- **官方搭配规则内置**：直接采用 `query-meals` 描述中的预算分档规则（20 元以下 / 20–30 / 30–40 / 40–50 / 50 以上），不靠拍脑袋。
- **强制确认闸门**：`create-order` 之前必须有明确确认，杜绝误下单。
- **参数坑全部记进技能**：`beType` / `orderType` / `beCode` 配对规则、价格单位为分、401 与 429 的区分，都写进了参考文档，不靠模型现场猜。
- **自带连通性自检**：`scripts/check_mcp.py` 一条命令定位 Token、限流、工具缺失问题。

---

## 快速开始

### 1. 申请 MCP Token

访问 <https://open.mcd.cn/mcp>，手机号验证码登录 → 控制台 → 激活，复制生成的 Token。

### 2. 配置 MCP 连接器

在 WorkBuddy 中走「自定义连接器 → 配置 MCP」，填入（把占位符换成真实 Token）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer <你的Token>"
      }
    }
  }
}
```

三个易错点：

1. `Authorization` 必须是 `Bearer <Token>`，**`Bearer ` 前缀不能少**，否则服务端判无效
2. `url` 只能是 `https://mcp.mcd.cn`，旧路径连不上
3. 改完配置需在 WorkBuddy 中**关闭再开启一次连接器**才生效

仓库中的 `mcp-config.example.json` 为脱敏示例，占位符为 `${MCD_MCP_TOKEN}`。

### 3. 安装 Skill

```bash
git clone https://github.com/<your-username>/mcd-crew-catering.git
cp -r mcd-crew-catering ~/.workbuddy/skills/
```

重启 WorkBuddy 后即可触发。

### 4. 验证

```bash
export MCD_MCP_TOKEN=<你的Token>
python3 ~/.workbuddy/skills/mcd-crew-catering/scripts/check_mcp.py
```

输出工具总数与「团餐链路所需工具齐全」即安装成功。

---

## 会触发它的说法

- 「班组 12 个人加班，订个麦当劳，人均 30 左右」
- 「明天中午给项目部订团餐，20 人，预算 800」
- 「十几个人夜班加餐，帮我配几套方案对比」
- 「这个门店团餐有什么助餐服务」

---

## 目录结构

```
mcd-crew-catering/
├── SKILL.md                          技能主文件
├── references/
│   ├── mcp-tools.md                  35 个工具全景 + 团餐链路参数细节
│   └── crew-catering-playbook.md     搭配策略、预算算法、实战话术
├── scripts/
│   └── check_mcp.py                  连通性自检
├── assets/
│   └── plan-template.md              Top3 方案输出模板
├── mcp-config.example.json           脱敏配置示例
├── MCP_INTEGRATION.md                MCP 集成说明
├── CONTEST_DECLARATION.md            参赛声明（官方原文）
└── workbuddy.md                      开发过程对话记录
```

---

## 使用的 MCP 工具

| 环节 | 工具 |
|---|---|
| 配送地址 | `delivery-query-addresses`、`delivery-create-address` |
| 可配送门店 | `delivery-query-stores`（`beType=6`） |
| 菜单与套餐 | `query-meals`、`query-meal-detail` |
| 助餐服务 | `query-meal-assistance` |
| 优惠券 | `available-coupons`、`auto-bind-coupons`、`query-my-coupons` |
| 计价 | `calculate-price` |
| 下单 | `create-order`（需确认） |
| 积分与抽奖 | `query-my-account`、`query-lottery-info` |

完整清单与调用流程见 [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)。

---

## 安全

- 本仓库**不包含任何 Token、密钥或账号凭证**，配置文件仅使用环境变量占位符。
- Token 等同麦当劳账户钥匙（可领券、可下单），请勿提交到任何公开位置。
- 未经用户明确确认，技能不会调用 `create-order`。

---

## 说明

本项目为「麦当劳程序员节创意开发大赛」参赛作品，由参赛者独立开发，非麦当劳官方产品。输出仅供参考，餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。

- 赛事仓库：<https://github.com/M-China/mcd-developer-innovation-challenge>
- MCP 官方文档：<https://github.com/M-China/mcd-mcp-server>

## License

MIT
