# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下优秀的开源项目与公开资料，**所有实现代码、检测规则与文案均为原创**，未复制任何第三方的原文案或代码。

| 项目 | 作者 / 来源 | 许可 | 链接 | 借鉴了什么思路 |
|---|---|---|---|---|
| novel-create-skill | shuozhe-liang | 未声明（仅借鉴高层思路） | https://github.com/shuozhe-liang/novel-create-skill | "作者拍板权"的协作模式（AI 执笔、作者掌握关键决策）、断点续写、伏笔管理、一致性自查的流程思想 |
| novel-writing-skill | lenmo181 | Apache-2.0 | https://github.com/lenmo181/novel-writing-skill | "把写作变成可验证的工程流程"的校验工程化思路（硬卡校验）；爽感闭环、打脸节奏、金手指设计、去 AI 味的问题意识 |
| speckit-preset-chinese-web-fiction-writing | sigentech | 未明确（仅借鉴高层思路） | https://github.com/sigentech/speckit-preset-chinese-web-fiction-writing | 路由式技法树（按场景分发：开篇/节奏/大纲/人设/单章/扑街诊断）；黄金三章、爽点节奏、三层大纲、"十大死法"扑街诊断的框架思想 |
| novel-assistant-skill | duiniwukenaihe | MIT | https://github.com/duiniwukenaihe/novel-assistant-skill | 单入口编排（一个命令覆盖规划/写作/审校/去 AI 味）、短篇优先打磨的思路 |
| oh-story-claudecode | worldwonderer（现 zenstory-ai） | MIT | https://github.com/worldwonderer/oh-story-claudecode | 扫榜拆文（对标爆款拆解）、去 AI 味、文件化连续性追踪的思路 |
| creative-writing-skills | sh1ny | Apache-2.0 | https://github.com/sh1ny/creative-writing-skills | novel-init → pitch → codex → outline → style → beat → critique 的分层写作流程思想 |
| ai_writer（story-coach） | elegarmco | MIT | https://github.com/elegarmco/ai_writer | 教练式提问（用诊断性问题引导作者自己发现答案，而非直接给答案）的约束思想 |
| 三幕式结构 | 经典叙事理论（公共领域） | — | — | 开端 / 对抗 / 结局三幕框架，用于总纲的宏观结构校验 |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上项目的具体文案、规则原文、代码实现均未被复制。本插件的 skill 方法论文案、审计规则、命令流程均为独立撰写。
2. **许可合规**：MIT / Apache-2.0 许可的项目允许在保留声明的前提下进行思路借鉴与二次创作，本文件即为保留声明的一部分；许可未声明的项目仅借鉴其公开文档中的高层思路，未复制任何具体内容。
3. **未核实项**：各仓库的 star 数、更新频率等动态数据未收录（避免编造）；仓库迁移（如 oh-story-claudecode 迁移至 zenstory-ai 名下）以 2026-10-11 实查为准。
4. **商标与归属**：各项目名称与作者署名归其各自所有者所有。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
