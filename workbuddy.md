# workbuddy.md · 开发过程对话记录

本项目全程使用腾讯 WorkBuddy 开发。以下为关键对话与决策记录，用于说明项目由 WorkBuddy 驱动完成。

## 背景

参加「麦当劳程序员创意开发大赛」，要求基于麦当劳官方 MCP 开发一个 Skill，开源到 GitHub，按 Star 数排名。

## 对话记录

### 1. 学习官方 Skill 开发规范

**用户**：@场景「Skill 开发」，学习一下这个文件夹的内容。

**WorkBuddy**：定位到内置 `skill-creator` 技能包，通读 SKILL.md 规范与三个配套脚本（`init_skill.py`、`package_skill.py`、`quick_validate.py`），归纳出：

- 包结构：SKILL.md 必需 + 可选 scripts / references / assets
- 三层渐进加载：metadata 常驻 → SKILL.md 触发时加载 → 打包资源按需加载
- frontmatter 必须含 name + description，description 用第三人称写清触发场景
- 命名限 hyphen-case、≤40 字符、不含尖括号
- 正文用祈使句，细节下沉到 references

同时修正了两处环境差异：本机 Skill 存放路径为 `~/.workbuddy/skills/`（规范文档里的 `~/.codebuddy/` 为上游模板遗留），以及 frontmatter 需带 `agent_created: true`。

### 2. 确认比赛要求

**用户**：我要参加麦当劳的比赛，让我学习这个文件夹的内容，官方是让咱们开发一个 Skill 好用的技能吧。

**WorkBuddy**：读取《麦当劳大赛备战手册》与《麦当劳 MCP 接入指南》，确认判断正确 —— 比赛要求基于麦当劳官方 MCP 开发 Skill 并开源。同时汇总了已有情报：35 个 MCP 工具清单、榜单竞争分析（第 100 名门槛仅 5 Star）、已定方向为企业团餐 + 积分抽奖钩子、红线（严禁刷 Star、Token 不外泄、下单须二次确认）。

### 3. 生成项目骨架

使用 `skill-creator` 自带的 `init_skill.py` 生成 `mcd-crew-catering` 骨架，随后删除示例文件，写入正式内容。

### 4. 编写技能本体

从 MCP 服务端拉取真实工具 schema，据此编写：

- `SKILL.md`：九步流程（收集输入 → 定位门店 → 拉菜单 → 查助餐服务 → 领券 → 计价 → 出 Top3 → 确认下单 → 积分提示），含参数配对速查表、错误处理表、边界约束
- `references/mcp-tools.md`：35 个工具全景 + 团餐链路参数细节
- `references/crew-catering-playbook.md`：搭配策略、预算算法、实战话术、踩坑记录
- `scripts/check_mcp.py`：连通性自检脚本
- `assets/plan-template.md`：Top3 方案输出模板

### 5. 本地联调与验证

**自检脚本实测**：连接 `https://mcp.mcd.cn` 成功，返回 `mcd-mcp v1.0.0`，工具总数 35，团餐链路所需工具全部齐全，并识别出两个未文档化工具（`query-survey-coupon`、`query-promotions`）。

**核心链路实测**（团餐场景 `beType=6`）：

1. `delivery-query-addresses` → 返回 3 个配送地址，取青岛黄岛区地址 ID
2. `delivery-query-stores(beType=6)` → 返回 2 家支持团餐配送的门店（青岛黄岛梦乐城餐厅、青岛海信嘉年华餐厅），均支持预约，可选早餐/午餐/下午茶/夜市时段
3. `query-meals(orderType=2, beType=6)` → 返回完整菜单（人气热卖、主食、小食甜品、饮品、麦咖啡、开心乐园六类）
4. `query-meal-assistance(beType=6)` → 返回三档助餐服务，实测发现 `GMS002` 专人分餐与 `GMS003` 专人摆台仅在送达时间 07:00–20:00 可选，夜班订餐只能用 `GMS001` 保鲜速达

第 4 条是联调中发现的、官方文档未记载的约束，已补写进 `references/crew-catering-playbook.md`。

### 6. 补齐仓库必交文件

`README.md`、`CONTEST_DECLARATION.md`（官方原文，经两次独立抓取核对一致）、`MCP_INTEGRATION.md`、`mcp-config.example.json`（仅环境变量占位符）、`LICENSE`、`.gitignore`。

## WorkBuddy 在本项目中的作用

- 通读并内化官方 Skill 开发规范，据此生成规范的项目骨架
- 直接从 MCP 服务端提取真实工具 schema，保证参数说明不是猜测
- 驱动自检脚本与核心链路实跑，验证接口可用性并记录未文档化的行为
- 生成 README、MCP 集成说明等面向开源受众的交付文档

## 安全说明

全程未将任何 Token、密钥或账号凭证写入本项目文件。配置文件仅使用 `${MCD_MCP_TOKEN}` 环境变量占位符，`.gitignore` 已排除所有可能含凭证的文件。
