<!-- About 简介（推送后填写到仓库 About 栏）：
网文写作专家：题材到逐章连载的写作流水线 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-fiction
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, fiction-writing, novel -->

# lhg-fiction：网文写作专家——题材到逐章连载的写作流水线

> **一句话介绍**：给 AI 助手装上"网文写作流水线"——题材立意、黄金三章、三层大纲、人设与伏笔台账、逐章写作、24 条确定性规则做人设/伏笔一致性自查，小白也能开出一本不断更、不崩设定的网文。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-fiction
> /plugin install lhg-fiction@lhg-plugs
> ```

## 它是什么

`lhg-fiction` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`fiction` 开新书一条龙（题材→梗概→大纲→人设→黄金三章），`fiction-chapter` 逐章/批量写作，`fiction-audit` 一致性体检，`fiction-opening` 黄金三章专项诊断
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：题材立意、三层大纲、人设与伏笔、逐章写作
- **3 个专家 agent**：执笔写手、毒舌编辑、世界观守夜人（设定/伏笔台账维护）
- **2 个硬门 hooks**：commit 前一致性审计拦截、章节写入后台账过期提醒（均可一键豁免：`LHG_FICTION_HOOKS_OFF=1`）
- **24 条确定性自查规则**：人设一致性、伏笔回收、章节字数、禁用词、视角统一、爽点节奏，纯 Python、零第三方依赖

## 方法论来源

本插件开书前做了生态深挖（2026-10-11）：调研了 7 个公开小说/网文写作 skill 与经典叙事理论，整合其**高层思路**（七步协作与作者拍板权、校验工程化、路由式技法树、黄金三章、爽点节奏、三层大纲、扫榜拆文、去 AI 味），**所有文案与代码均为原创**，未复制任何第三方原文。灵感来源与许可声明见 [ATTRIBUTION.md](ATTRIBUTION.md)。

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-fiction:fiction` | 开新书一条龙：题材立意→梗概→三层大纲→人设→黄金三章 | `/lhg-fiction:fiction "废柴修仙逆袭"` |
| `/lhg-fiction:fiction-chapter` | 按细纲逐章/批量写作，写完自动回写三件套 | `/lhg-fiction:fiction-chapter "第5章"` |
| `/lhg-fiction:fiction-audit` | 人设/伏笔一致性体检（脚本+人工评审） | `/lhg-fiction:fiction-audit` |
| `/lhg-fiction:fiction-opening` | 黄金三章专项：诊断/重写前三章 | `/lhg-fiction:fiction-opening 诊断` |

## 用户旅程

```
/fiction "题材" → 梗概确认 → 三层大纲 → 人设卡+伏笔台账 → 黄金三章
    → /fiction-chapter "第4-10章"（连载批次，每章自动回写）
    → /fiction-audit（定期体检：人设/伏笔/字数/视角）
    → 发现慢热 → /fiction-opening 诊断重写
```

## 项目文件约定

插件在小说项目目录下维护 6 类文件（`fiction` 命令自动创建骨架）：

```
fiction-<书名>/
├── 00-故事梗概.md      # 项目存在标志：题材/爽点/梗概/书名候选
├── 01-人设卡.md        # 人物条目：称呼/年龄/身份/能力/三锚点
├── 02-伏笔台账.md      # 伏笔：埋设章节/回收章节/状态
├── 03-细纲.md          # 章纲四要素：目标/冲突/爽点/钩子
├── writing-log.md      # 写作日志：断点续写用
└── chapters/           # 章节正文：第N章.md
```

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/fiction_audit.py --target <项目目录>`（24 条规则，零 LLM 成本）；
2. 发现分三级：**blocker**（必须修：人设矛盾、伏笔回收无埋设、严重缺字、命中禁用词；commit 前 hook 会拦截）、**warning**（修或写豁免理由：伏笔超期、视角混用、AI 味超标、章末无钩子）、**nit**（顺手修）；
3. 再按 `fiction-audit` 命令的人工评审清单过一遍脚本抓不到的（爽点间隔、战力崩坏、人物弧光、主线跑偏）。

blocker 清零才算体检通过；为清零改规则算作弊，不许。

## 目录结构

```
lhg-fiction/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：fiction / fiction-chapter / fiction-audit / fiction-opening
├── skills/                  # 4 个平台中立 skill（lhg-fic-premise/outline/character/chapter）
├── agents/                  # 3 个专家 agent（fiction-writer / fiction-editor / fiction-worldkeeper）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / 台账过期提醒）+ 豁免说明
├── scripts/audit/           # 24 条确定性自查规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（fiction-bad / fiction-good 对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你想写网文/小说，但不知道从题材、大纲到连载的全流程怎么走时 → 用 `/lhg-fiction:fiction` 开书
- 你连载到几十章，开始忘自己埋过什么伏笔、人物设定前后打架时 → 跑 `/lhg-fiction:fiction-audit` + 守夜人 agent
- 你的开头被说"慢热"、留存差时 → 用 `/lhg-fiction:fiction-opening` 诊断黄金三章
- 你想给写作立一套"不断更、不崩设定"的纪律时 → 它的 hooks 硬门与台账规范开箱即用

**什么时候不用：**

- 你写的是纯文学/严肃文学，不追求网文的爽点节奏与连载逻辑 → 本插件的方法论（黄金三章/爽点密度）是网文专用的，会水土不服
- 你只想让 AI 润色一段文字，不想建项目文件 → 太重了，直接对话让 AI 改就行
- 你希望 AI 完全自由发挥、不接受"先写细纲再写正文"的约束 → 它的流程纪律会让你烦（可关，但那就别装它）

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-wechat-article](https://github.com/lhg-plugs/lhg-wechat-article) | 公众号写作专家：选题到排版一气呵成 | `/plugin install lhg-wechat-article@lhg-plugs` |
| [lhg-xiaohongshu](https://github.com/lhg-plugs/lhg-xiaohongshu) | 小红书种草专家：卖点到爆款笔记一键生成 | `/plugin install lhg-xiaohongshu@lhg-plugs` |
| [lhg-resume](https://github.com/lhg-plugs/lhg-resume) | 简历优化专家：ATS诊断到模拟面试一条龙 | `/plugin install lhg-resume@lhg-plugs` |
| [lhg-ppt](https://github.com/lhg-plugs/lhg-ppt) | PPT制作专家：述职融资答辩一键成稿 | `/plugin install lhg-ppt@lhg-plugs` |
| [lhg-excel](https://github.com/lhg-plugs/lhg-excel) | 表格数据专家：清洗透视图表一条龙 | `/plugin install lhg-excel@lhg-plugs` |
| [lhg-thesis](https://github.com/lhg-plugs/lhg-thesis) | 毕业论文助手：开题到盲审的写作流水线 | `/plugin install lhg-thesis@lhg-plugs` |
| [lhg-miniprogram](https://github.com/lhg-plugs/lhg-miniprogram) | 小程序开发专家：一句话生成微信小程序 | `/plugin install lhg-miniprogram@lhg-plugs` |
| [lhg-contract](https://github.com/lhg-plugs/lhg-contract) | 合同审查助手：风险条款标红+修改建议 | `/plugin install lhg-contract@lhg-plugs` |
| [lhg-fiction](https://github.com/lhg-plugs/lhg-fiction) | 网文写作专家：题材到逐章连载的写作流水线 | `/plugin install lhg-fiction@lhg-plugs` |
| *（后续插件在此追加，保持表格格式一致）* | | |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、24 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-fiction/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
