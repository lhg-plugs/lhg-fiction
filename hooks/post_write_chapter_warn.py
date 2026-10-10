#!/usr/bin/env python3
"""lhg-fiction 硬门②：章节文件写入后，若伏笔台账/人设卡长期未更新则提醒。

触发：PostToolUse / Write|Edit。只关心 chapters/ 下的章节文件，
其他文件 0 开销直接放行。

逻辑：章节文件写入后，检查项目目录下 02-伏笔台账.md 与 01-人设卡.md
的修改时间；若任一台账比本次写入的章节文件旧超过 STALE_DAYS 天，
追加一条 additionalContext 提醒回写（不断更的连载最怕台账过期）。

逃生方式（按推荐度排序）：
  1. 按提醒更新台账（推荐）。
  2. 紧急情况：LHG_FICTION_HOOKS_OFF=1（单次豁免本次 hook）。
  3. /plugin disable lhg-fiction（整个插件停用，hooks 不再触发）。

设计原则：任何内部出错（找不到文件、解析失败等）都 fail-open 静默放行，
绝不因提醒脚本自身故障打断写作；本 hook 只提醒、不拦截。
零第三方依赖。
"""

import json
import os
import sys
import time

STALE_DAYS = 7
STALE_SECS = STALE_DAYS * 86400


def main() -> int:
    # 逃生开关
    if os.environ.get("LHG_FICTION_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""

    # 只关心章节文件
    norm = file_path.replace("\\", "/")
    if "/chapters/" not in norm:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    stale = []
    try:
        ch_mtime = os.path.getmtime(file_path)
    except OSError:
        return 0  # 章节文件不可读：fail-open

    for ledger in ("02-伏笔台账.md", "01-人设卡.md"):
        p = os.path.join(project_dir, ledger)
        try:
            age = ch_mtime - os.path.getmtime(p)
        except OSError:
            stale.append("%s（缺失）" % ledger)
            continue
        if age > STALE_SECS:
            stale.append("%s（已 %d 天未更新）" % (ledger, int(age // 86400)))

    if not stale:
        return 0

    msg = (
        "lhg-fiction 提醒：章节文件已写入，但以下台账超过 %d 天未更新：%s。"
        "连载最怕台账过期导致伏笔遗忘/人设崩坏，建议顺手回写；"
        "确认无变更可忽略本提醒。"
        % (STALE_DAYS, "、".join(stale))
    )
    sys.stdout.write(json.dumps({"additionalContext": msg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
