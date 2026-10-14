# mcd-family-journal · 我与麦当劳

> 一句话：把麦当劳账号里零散的历史订单，变成一份可点击、可切换、能截图分享的消费档案。

一个基于 [麦当劳官方 MCP](https://github.com/M-China/mcd-mcp-server) 的 WorkBuddy Skill。它拉取你账号里**真实的历史订单**，算出吃了多少顿、花了多少钱、最常去哪家店、最爱点什么、口味偏哪一类，然后渲染成一张交互式 HTML 档案页。

---

## 先看效果

没有 MCP Token 也能看：[examples/demo.html](./examples/demo.html)

这是用 12 笔**虚构订单**生成的完整示例，下载后双击打开即可，包含娃的成长册、AI 观察、常点搭配等全部模块。

想看自己的，一条命令：

```bash
export MCD_MCP_TOKEN=<你的Token>
python3 scripts/build_journal.py --out ~/Desktop
```

版式一样，数据换成你自己的。

---

## 页面能做什么

它不是一张静态图，而是一个可以点的页面：

| 操作 | 效果 |
|---|---|
| 点顶部「个人版 / 家庭版」 | 切换档案视角，标题、徽章、文案随之变化 |
| 点四张概览卡片 | 下方展开明细：每月吃了几顿 / 最近几笔花费 / 去得最多的门店 / 点得最多的单品 |
| 再点一次同一张卡片 | 收起明细 |

**个人版**：「我与麦当劳」「你的口味画像」，适合一个人复盘自己的饮食习惯。

**家庭版**：「我家与麦当劳」「一家人的口味画像」。如果订单里有开心乐园餐，会额外长出一份**娃的麦当劳成长册** —— 第一次带娃吃是哪天在哪家店、带娃吃过几次、娃最常点哪一款。没有儿童餐记录时，显示引导文案而不是报错。

---

## 档案里有什么

| 模块 | 内容 |
|---|---|
| 概览卡片 | 总顿数、累计花费、最常去的门店、最爱的单品（可点开看明细） |
| 娃的麦当劳成长册 | 仅家庭版：第一次带娃的时间与门店、带娃次数、娃最常点的儿童餐、最近一次 |
| 口味画像 | 辣党 / 鸡肉派 / 牛肉党 / 薯条控 / 甜品胃 / 咖啡因 / 汽水党，按频次排序 |
| 餐盘构成 | 汉堡、小食、饮料、甜品的占比条 |
| 月度节奏 | 按月统计的柱状节奏，最近一个月高亮 |
| 点得最多的单品 | Top 6 排行 |

示例（虚构数据，仅示意版式）：

```
共 32 顿 · ¥1,286 · 最常去的店：XX 中心餐厅 · 最爱的单品：麦辣鸡腿汉堡
口味：鸡肉派 ×48　辣党 ×22　牛肉党 ×15　汽水党 ×14　甜品胃 ×9
娃的成长册：第一次 2024-06-01 · 带娃 11 次 · 最爱麦乐鸡开心乐园餐
```

---

## 为什么做这个

麦当劳 MCP 上的多数作品是省钱凑单、营养计算、点餐助手 —— 都是**工具型**的：有用，但用完就走。

这个技能走的是另一条路：**输出即内容**。它不解决"这顿吃什么"，而是把已经发生的事讲成一个故事，产出一个你愿意截图发出去的页面。

技术上也不含糊：真实订单解析、套餐子项展开、儿童餐识别、口味关键词打分、分类统计，全部基于真实接口返回，没有模拟数据。页面是单文件、无外部依赖、纯原生 JS，双击就能打开。

---

## 快速开始

### 1. 申请 MCP Token

访问 <https://open.mcd.cn/mcp>，手机号验证码登录 → 控制台 → 激活，复制生成的 Token。

### 2. 配置 MCP 连接器

在 WorkBuddy 中走「自定义连接器 → 配置 MCP」：

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

1. `Authorization` 必须是 `Bearer <Token>`，**`Bearer ` 前缀不能少**
2. `url` 只能是 `https://mcp.mcd.cn`，旧路径连不上
3. 改完配置需在 WorkBuddy 中**关闭再开启一次连接器**才生效

### 3. 安装 Skill

```bash
git clone https://github.com/<your-username>/mcd-family-journal.git
cp -r mcd-family-journal ~/.workbuddy/skills/
```

### 4. 生成档案页

```bash
export MCD_MCP_TOKEN=<你的Token>
python3 ~/.workbuddy/skills/mcd-family-journal/scripts/build_journal.py --out ~/Desktop
```

得到单个文件 `mcd-journal.html`，双击打开即可。

想指定默认视角：

```bash
python3 scripts/build_journal.py --mode family    # 默认打开家庭版
python3 scripts/build_journal.py --mode personal  # 默认打开个人版
```

默认 `--mode auto`：有开心乐园餐订单就开家庭版，否则个人版。两种视角都在文件里，随时可切。

先跑自检确认环境：

```bash
python3 scripts/check_mcp.py
```

也可以直接在 WorkBuddy 里说一句：「帮我看看我这一年吃了多少顿麦当劳」。

---

## 隐私

这件事值得单独说清楚：

- 全部数据只在本机处理，脚本**不上传任何内容**，产物保存在你指定的本地目录
- 档案页含真实门店、金额与时间，**属于个人信息**，请勿提交到公开仓库
- 本仓库不包含任何示例订单、真实数据或 Token；README 中的示例均为虚构
- `.gitignore` 已排除所有可能含凭证的文件

---

## 目录结构

```
mcd-family-journal/
├── SKILL.md                          技能主文件
├── scripts/
│   ├── build_journal.py              拉数据 + 统计 + 渲染档案页
│   ├── make_demo.py                  用虚构数据生成示例页（无需 Token）
│   └── check_mcp.py                  连通性自检
├── assets/
│   └── journal-template.html         页面模板（含交互逻辑）
├── examples/
│   └── demo.html                     示例档案页，可直接双击打开
├── references/
│   ├── mcp-tools.md                  MCP 工具全景与订单数据结构
│   └── crew-catering-playbook.md     团餐实战手册（早期方向留存）
├── legacy/
│   └── crew-catering-SKILL.md        早期团餐版本完整存档
├── mcp-config.example.json           脱敏配置示例
├── MCP_INTEGRATION.md                MCP 集成说明
├── CONTEST_DECLARATION.md            参赛声明（官方原文）
└── workbuddy.md                      开发过程对话记录
```

---

## 使用的 MCP 工具

| 工具 | 用途 |
|---|---|
| `order-list` | 拉取历史订单，全部统计的数据源 |
| `query-my-account` | 账号积分，用于页脚 |
| `query-my-prizes` | 抽奖奖品，可选扩展 |
| `campaign-calendar` | 活动日历，用于解读消费密集期 |
| `list-nutrition-foods` | 营养数据，可选扩展 |

详见 [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)。

---

## 说明

本项目为「麦当劳程序员节创意开发大赛」参赛作品，由参赛者独立开发，非麦当劳官方产品。输出仅供参考，餐品信息、价格及供应状态以麦当劳官方渠道的实时结果为准。

- 赛事仓库：<https://github.com/M-China/mcd-developer-innovation-challenge>
- MCP 官方文档：<https://github.com/M-China/mcd-mcp-server>

## License

MIT
