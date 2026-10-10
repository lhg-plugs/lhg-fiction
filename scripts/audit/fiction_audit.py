#!/usr/bin/env python3
"""lhg-fiction 确定性小说一致性审计：24 条规则，零第三方依赖。

扫描小说项目目录（约定文件：00-故事梗概.md / 01-人设卡.md /
02-伏笔台账.md / 03-细纲.md / chapters/*.md / writing-log.md），
检查人设一致性、伏笔回收、章节字数、禁用词、视角统一、爽点节奏。

用法：
    python3 fiction_audit.py --target <项目目录> [--format json|text]
                             [--fail-on blocker|warning|nit]

有 >= fail-on 级别发现时以 exit code 2 退出（供 hooks 与 CI 使用）。

规则文案均为本项目原创（思路受 novel-create-skill、novel-writing-skill、
oh-story-claudecode 等开源项目启发，未复制任何第三方原文）。
"""

import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-fiction/fiction-audit"

SKIP_DIRS = {".git", "__pycache__", "docs", "node_modules"}

# 敏感词示例清单（生产使用请替换为目标平台的正式词库）
BANNED_SAMPLE = ["开膛破肚", "碎尸万段", "赤身裸体"]
META_WORDS = ["读者", "本章", "主角", "作者", "上帝视角"]
AI_WORDS = ["不由得", "忍不住", "仿佛", "似乎", "缓缓", "嘴角勾起",
            "一抹", "深邃", "美眸", "剑眉星目"]
SHUANGDIAN_WORDS = ["打脸", "突破", "碾压", "震惊", "反杀", "复仇",
                    "狂喜", "求饶", "扬眉吐气", "一鸣惊人", "打爆", "跪"]
SUSPENSE_WORDS = ["悬念", "秘密", "真相", "竟然", "难道", "阴谋", "究竟"]
SPEAKER_VERBS = ("说道", "笑道", "冷笑道", "问道", "喝道", "喊道",
                 "低声道", "大笑道", "怒道", "轻声道")
PERSONA_FIELDS = ["称呼", "年龄", "身份", "能力"]
CH_NO_RE = re.compile(r"第\s*(\d+)\s*章")


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file",
                 "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def char_count(text):
    return len(re.sub(r"\s", "", text))


# ---------------- 项目文件解析 ----------------

def parse_personas(path):
    """解析 01-人设卡.md → {人名: {field: value}}。"""
    text = read_text(path)
    personas = {}
    cur = None
    for ln in text.split("\n"):
        m = re.match(r"^##\s*(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip()
            personas[cur] = {}
            continue
        if cur is not None:
            m2 = re.match(r"^\s*[-*]\s*([^：:]+)[：:]\s*(.+?)\s*$", ln)
            if m2:
                personas[cur][m2.group(1).strip()] = m2.group(2).strip()
    return personas


def parse_ledger(path):
    """解析 02-伏笔台账.md 的 markdown 表格 → [{伏笔, 埋设, 回收, 状态}]。"""
    text = read_text(path)
    rows = []
    bad_rows = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            bad_rows.append(ln.strip()[:80])
            continue
        if re.match(r"^[-:]+$", cells[0]) or cells[0] in ("伏笔", "埋设章节"):
            continue  # 表头 / 分隔行

        def chap_no(v):
            m = CH_NO_RE.search(v or "")
            return int(m.group(1)) if m else None

        rows.append({"伏笔": cells[0], "埋设": chap_no(cells[1]),
                     "回收": chap_no(cells[2]), "状态": cells[3],
                     "埋设原文": cells[1], "回收原文": cells[2]})
    return rows, bad_rows


def parse_outline(path):
    """解析 03-细纲.md → 有章纲的章节号集合。"""
    text = read_text(path)
    return {int(m.group(1)) for m in
            re.finditer(r"^##\s*第\s*(\d+)\s*章", text, re.M)}


def collect_chapters(target):
    out = []
    ch_dir = os.path.join(target, "chapters")
    if not os.path.isdir(ch_dir):
        return out
    for f in sorted(os.listdir(ch_dir)):
        if f.endswith(".md"):
            p = os.path.join(ch_dir, f)
            m = CH_NO_RE.search(f)
            out.append({"path": p, "name": f,
                        "no": int(m.group(1)) if m else None,
                        "text": read_text(p)})
    return out


# ---------------- 规则：人设一致性 ----------------

@rule("FIC-CHAR-001", "blocker", "人设一致性", "人设属性前后矛盾",
      "正文中出现的人物属性（年龄等）与人设卡登记不一致，属于崩设定，修文或改卡二选一。")
def r_char_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-CHAR-001"]
    for name, fields in ctx["personas"].items():
        age = fields.get("年龄", "")
        m = re.match(r"^\d+$", age.strip())
        if not m:
            continue
        want = int(age)
        for ch in ctx["chapters"]:
            for mm in re.finditer(r"(\d{1,3})\s*岁", ch["text"]):
                if int(mm.group(1)) == want:
                    continue
                window = ch["text"][max(0, mm.start() - 30):mm.start()]
                if name in window:
                    hits.append(Finding(
                        rule["id"], rule["severity"], rule["category"],
                        rule["title"], ch["rel"], 1,
                        window[-20:] + mm.group(0),
                        "人设卡登记%s年龄 %d 岁，正文写成 %s 岁。" % (
                            name, want, mm.group(1))))
                    break
    return hits


@rule("FIC-CHAR-002", "warning", "人设一致性", "人物称呼混用",
      "同一人物在正文中出现 2 种以上称呼变体（如阿晚/小晚混用），读者会出戏，统一为一种。")
def r_char_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-CHAR-002"]
    all_text = "\n".join(c["text"] for c in ctx["chapters"])
    for name in ctx["personas"]:
        if len(name) < 2:
            continue
        stem = name[-1]
        variants = set(re.findall(r"[阿小老]" + re.escape(stem) + r"[儿]?",
                                  all_text))
        variants |= set(re.findall(re.escape(stem) + r"{2}", all_text))
        if len(variants) >= 2:
            hits.append(Finding(rule["id"], rule["severity"], rule["category"],
                                rule["title"], "chapters/", 0,
                                "、".join(sorted(variants)),
                                "%s 的称呼出现多种变体：%s。" % (
                                    name, "、".join(sorted(variants)))))
    return hits


@rule("FIC-CHAR-003", "warning", "人设一致性", "登场人物未登记",
      "正文里开口说话的人物在人设卡里没有条目，长篇连载中这种'裸奔'人物最容易写崩，补登记。")
def r_char_003(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-CHAR-003"]
    known = set(ctx["personas"])
    for fields in ctx["personas"].values():
        if fields.get("称呼"):
            known.add(fields["称呼"].strip())
    verbs = "|".join(SPEAKER_VERBS)
    seen = set()
    for ch in ctx["chapters"]:
        for m in re.finditer(r"([\u4e00-\u9fa5]{2,4})(?:" + verbs + r")",
                             ch["text"]):
            sp = m.group(1)
            if sp not in known and sp not in seen:
                seen.add(sp)
                hits.append(Finding(
                    rule["id"], rule["severity"], rule["category"],
                    rule["title"], ch["rel"], 1, m.group(0),
                    "说话人物「%s」未在人设卡登记。" % sp))
    return hits


@rule("FIC-CHAR-004", "nit", "人设一致性", "人设卡缺关键字段",
      "人物条目缺少 2 项以上关键字段（称呼/年龄/身份/能力），卡太薄，后续容易写飘。")
def r_char_004(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-CHAR-004"]
    for name, fields in ctx["personas"].items():
        missing = [f for f in PERSONA_FIELDS if not fields.get(f)]
        if len(missing) >= 2:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                "01-人设卡.md", 0, name,
                "「%s」缺少字段：%s。" % (name, "、".join(missing))))
    return hits


@rule("FIC-CHAR-005", "warning", "人设一致性", "注册人物从未登场",
      "人设卡里登记的人物在全部正文中一次都没出现过，可能是被遗忘的配角，确认是删是留。")
def r_char_005(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-CHAR-005"]
    all_text = "\n".join(c["text"] for c in ctx["chapters"])
    for name in ctx["personas"]:
        if name not in all_text:
            hits.append(Finding(rule["id"], rule["severity"], rule["category"],
                                rule["title"], "01-人设卡.md", 0, name,
                                "「%s」登记了但从未在正文登场。" % name))
    return hits


# ---------------- 规则：伏笔 ----------------

@rule("FIC-FORE-001", "blocker", "伏笔", "伏笔回收无埋设登记",
      "台账里某伏笔'回收章节'填了但'埋设章节'是空的——回收一个没埋过的伏笔，读者只会觉得莫名其妙。")
def r_fore_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-FORE-001"]
    for row in ctx["ledger"]:
        if row["回收"] is not None and row["埋设"] is None:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                "02-伏笔台账.md", 0, row["伏笔"],
                "伏笔「%s」登记了回收（%s）却没有埋设记录。" % (
                    row["伏笔"], row["回收原文"])))
    return hits


@rule("FIC-FORE-002", "warning", "伏笔", "伏笔超期未回收",
      "伏笔埋设后超过 10 章仍未回收，读者早忘了，回收时冲击力归零；超 30 章建议直接废弃并记录原因。")
def r_fore_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-FORE-002"]
    if ctx["max_chapter"] is None:
        return hits
    for row in ctx["ledger"]:
        if row["埋设"] is None or row["状态"] in ("已回收", "废弃"):
            continue
        gap = ctx["max_chapter"] - row["埋设"]
        if gap >= 10:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                "02-伏笔台账.md", 0, row["伏笔"],
                "伏笔「%s」第 %d 章埋设，至今 %d 章未回收。" % (
                    row["伏笔"], row["埋设"], gap)))
    return hits


@rule("FIC-FORE-003", "warning", "伏笔", "埋设章节正文无伏笔痕迹",
      "台账登记了埋设章节，但对应章节文件里找不到该伏笔关键词——可能是埋了但没写进去，或章节文件丢失。")
def r_fore_003(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-FORE-003"]
    by_no = {c["no"]: c for c in ctx["chapters"] if c["no"] is not None}
    for row in ctx["ledger"]:
        if row["埋设"] is None:
            continue
        ch = by_no.get(row["埋设"])
        if ch is None:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                "02-伏笔台账.md", 0, row["伏笔"],
                "伏笔「%s」登记埋设于第 %d 章，但该章节文件不存在。" % (
                    row["伏笔"], row["埋设"])))
        elif row["伏笔"] not in ch["text"]:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, row["伏笔"],
                "伏笔「%s」登记埋设于第 %d 章，但正文无该关键词。" % (
                    row["伏笔"], row["埋设"])))
    return hits


@rule("FIC-FORE-004", "nit", "伏笔", "伏笔台账格式行解析失败",
      "台账表格有解析失败的行（列数不足），可能是手误改坏了表格，检查一下。")
def r_fore_004(ctx):
    rule = _RULE_BY_ID["FIC-FORE-004"]
    return [Finding(rule["id"], rule["severity"], rule["category"],
                    rule["title"], "02-伏笔台账.md", 0, b,
                    "该行表格列数不足 4 列，无法解析。")
            for b in ctx["ledger_bad"]]


# ---------------- 规则：章节长度 ----------------

@rule("FIC-LEN-001", "blocker", "章节长度", "章节严重缺字",
      "单章正文不足 800 字（不计空白），连载平台会被判为'水章/断更式更新'，补足或合并。")
def r_len_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-LEN-001"]
    for ch in ctx["chapters"]:
        n = char_count(ch["text"])
        if n < 800:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"],
                "本章仅 %d 字，不足 800 字下限。" % n))
    return hits


@rule("FIC-LEN-002", "warning", "章节长度", "章节偏短",
      "单章 800-1500 字：对长篇连载偏短，读者会觉得'刚看两眼就没了'，建议 2000-3000 字。")
def r_len_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-LEN-002"]
    for ch in ctx["chapters"]:
        n = char_count(ch["text"])
        if 800 <= n < 1500:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"], "本章 %d 字，偏短。" % n))
    return hits


@rule("FIC-LEN-003", "warning", "章节长度", "章节过长",
      "单章超过 6000 字：手机端阅读疲劳，考虑拆成两章（多一个钩子位）。")
def r_len_003(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-LEN-003"]
    for ch in ctx["chapters"]:
        n = char_count(ch["text"])
        if n > 6000:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"], "本章 %d 字，过长。" % n))
    return hits


@rule("FIC-LEN-004", "nit", "章节长度", "章节文件命名不规范",
      "章节文件名不含'第N章'，按章号排序、伏笔定位都会受影响，建议重命名。")
def r_len_004(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-LEN-004"]
    for ch in ctx["chapters"]:
        if ch["no"] is None:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"], "文件名无章号。"))
    return hits


# ---------------- 规则：禁用词 ----------------

@rule("FIC-BAN-001", "blocker", "禁用词", "命中示例敏感词",
      "正文命中示例敏感词。注意：内置的只是极简示例清单，"
      "正式发布前务必替换为目标平台的完整词库重扫。")
def r_ban_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-BAN-001"]
    for ch in ctx["chapters"]:
        lines = ch["text"].split("\n")
        for i, ln in enumerate(lines):
            for w in BANNED_SAMPLE:
                if w in ln:
                    hits.append(Finding(
                        rule["id"], rule["severity"], rule["category"],
                        rule["title"], ch["rel"], i + 1,
                        ln.strip()[:80],
                        "命中示例敏感词「%s」，请改写或删除。" % w))
                    break
    return hits


# ---------------- 规则：视角 ----------------

@rule("FIC-POV-001", "warning", "视角", "叙事视角疑似混用",
      "同一章里第一人称'我'与第三人称'他/她'都高频出现（各>10次），"
      "视角大概率写串了，通读确认。")
def r_pov_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-POV-001"]
    for ch in ctx["chapters"]:
        first = ch["text"].count("我")
        third = ch["text"].count("他") + ch["text"].count("她")
        if first > 10 and third > 10:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"],
                "「我」出现 %d 次，「他/她」出现 %d 次。" % (first, third)))
    return hits


@rule("FIC-POV-002", "warning", "视角", "出现元叙事词",
      "正文出现'读者/本章/主角/作者'等元叙事词，会瞬间打破代入感，改成故事内视角表达。")
def r_pov_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-POV-002"]
    for ch in ctx["chapters"]:
        lines = ch["text"].split("\n")
        for i, ln in enumerate(lines):
            found = [w for w in META_WORDS if w in ln]
            if found:
                hits.append(Finding(
                    rule["id"], rule["severity"], rule["category"],
                    rule["title"], ch["rel"], i + 1,
                    ln.strip()[:80],
                    "元叙事词：%s。" % "、".join(found)))
                break
    return hits


# ---------------- 规则：爽点节奏 ----------------

@rule("FIC-PACE-001", "warning", "爽点节奏", "章末无钩子",
      "章节末尾 300 字既无疑问/省略号，也无悬念词，属于'平收'——"
      "追读就靠章末那一下，平收等于把读者往外推。")
def r_pace_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-PACE-001"]
    for ch in ctx["chapters"]:
        tail = ch["text"][-300:]
        if not re.search(r"[？?……]", tail) and not any(
                w in tail for w in SUSPENSE_WORDS):
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"],
                "章末 300 字无钩子（疑问/省略/悬念词）。"))
    return hits


@rule("FIC-PACE-002", "warning", "爽点节奏", "章节无爽点词",
      "整章没出现任何爽点信号词（打脸/突破/反杀等），可能是水章，"
      "对照细纲确认本章的爽点到底兑现了没有。")
def r_pace_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-PACE-002"]
    for ch in ctx["chapters"]:
        if char_count(ch["text"]) < 800:
            continue  # 太短的章节不判（已有 LEN 规则管）
        if not any(w in ch["text"] for w in SHUANGDIAN_WORDS):
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"], "全章无爽点信号词。"))
    return hits


@rule("FIC-PACE-003", "warning", "爽点节奏", "章节无对应细纲",
      "chapters/ 里有这一章，但 03-细纲.md 里没有它的章纲——"
      "没有章纲就写正文，剧情跑偏的概率极高，先补细纲。")
def r_pace_003(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-PACE-003"]
    for ch in ctx["chapters"]:
        if ch["no"] is not None and ch["no"] not in ctx["outline"]:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"],
                "第 %d 章在细纲中没有对应章纲。" % ch["no"]))
    return hits


# ---------------- 规则：AI 味 ----------------

@rule("FIC-AI-001", "warning", "去AI味", "AI 味模板词密度超标",
      "模板词（不由得/仿佛/缓缓/嘴角勾起一抹等）密度超过每千字 8 个，"
      "读者一眼能嗅出 AI 味，逐个改写。")
def r_ai_001(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-AI-001"]
    for ch in ctx["chapters"]:
        n = char_count(ch["text"])
        if n < 300:
            continue
        c = sum(ch["text"].count(w) for w in AI_WORDS)
        density = c / (n / 1000)
        if density > 8:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"],
                "模板词 %d 个，密度 %.1f/千字。" % (c, density)))
    return hits


@rule("FIC-AI-002", "nit", "去AI味", "排比句式堆砌",
      "'不是…而是…'类排比一章出现 2 次以上，就是 AI 味重灾区，留一次，改写其余。")
def r_ai_002(ctx):
    hits = []
    rule = _RULE_BY_ID["FIC-AI-002"]
    for ch in ctx["chapters"]:
        n = (len(re.findall(r"不是[^，。！？]*，而是", ch["text"]))
             + len(re.findall(r"没有[^，。！？]*，只有", ch["text"])))
        if n >= 2:
            hits.append(Finding(
                rule["id"], rule["severity"], rule["category"], rule["title"],
                ch["rel"], 1, ch["name"], "排比句式出现 %d 次。" % n))
    return hits


# ---------------- 规则：项目格式 ----------------

@rule("FIC-FMT-001", "warning", "项目格式", "缺少故事梗概文件",
      "项目根目录没有 00-故事梗概.md——它是小说项目的存在标志，"
      "没有它插件会认为这不是小说项目。")
def r_fmt_001(ctx):
    rule = _RULE_BY_ID["FIC-FMT-001"]
    if not os.path.isfile(os.path.join(ctx["target"], "00-故事梗概.md")):
        return [Finding(rule["id"], rule["severity"], rule["category"],
                        rule["title"], ".", 0, "",
                        "00-故事梗概.md 缺失。")]
    return []


@rule("FIC-FMT-002", "warning", "项目格式", "缺少伏笔台账文件",
      "没有 02-伏笔台账.md，长篇连载的伏笔只能靠脑子记——脑子记不住 50 章以后的事。")
def r_fmt_002(ctx):
    rule = _RULE_BY_ID["FIC-FMT-002"]
    if not os.path.isfile(os.path.join(ctx["target"], "02-伏笔台账.md")):
        return [Finding(rule["id"], rule["severity"], rule["category"],
                        rule["title"], ".", 0, "",
                        "02-伏笔台账.md 缺失。")]
    return []


@rule("FIC-FMT-003", "nit", "项目格式", "缺少写作日志",
      "没有 writing-log.md，断点续写时只能靠翻聊天记录，建议每章写完追加一行。")
def r_fmt_003(ctx):
    rule = _RULE_BY_ID["FIC-FMT-003"]
    if not os.path.isfile(os.path.join(ctx["target"], "writing-log.md")):
        return [Finding(rule["id"], rule["severity"], rule["category"],
                        rule["title"], ".", 0, "",
                        "writing-log.md 缺失。")]
    return []


# ---------------- 主流程 ----------------

def run(target):
    findings = []
    chapters = collect_chapters(target)
    for ch in chapters:
        ch["rel"] = os.path.relpath(ch["path"], target).replace(os.sep, "/")
    ledger, ledger_bad = parse_ledger(os.path.join(target, "02-伏笔台账.md"))
    nums = [c["no"] for c in chapters if c["no"] is not None]
    ctx = {
        "target": target,
        "chapters": chapters,
        "personas": parse_personas(os.path.join(target, "01-人设卡.md")),
        "ledger": ledger,
        "ledger_bad": ledger_bad,
        "outline": parse_outline(os.path.join(target, "03-细纲.md")),
        "max_chapter": max(nums) if nums else None,
    }
    for r in RULES:
        try:
            findings.extend(r["check"](ctx))
        except Exception:
            continue  # 单条规则异常不影响整体
    return chapters, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-fiction 确定性小说一致性审计")
    ap.add_argument("--target", default=".", help="小说项目目录")
    ap.add_argument("--format", choices=["json", "text"], default="text")
    ap.add_argument("--fail-on", choices=["blocker", "warning", "nit"],
                    default="blocker")
    args = ap.parse_args(argv)

    target = os.path.abspath(args.target)
    if not os.path.isdir(target):
        print("target 不是目录：%s" % args.target, file=sys.stderr)
        return 1

    chapters, findings = run(target)
    sev_rank = {"blocker": 3, "warning": 2, "nit": 1}
    counts = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    result = {
        "tool": TOOL,
        "version": VERSION,
        "target": args.target,
        "summary": {
            "chapters_scanned": len(chapters),
            "rules_run": len(RULES),
            "blocker": counts["blocker"],
            "warning": counts["warning"],
            "nit": counts["nit"],
        },
        "findings": [f.to_dict() for f in sorted(
            findings, key=lambda x: (-sev_rank.get(x.severity, 0),
                                     x.file, x.line))],
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        print("小说审计：扫描 %d 章，运行 %d 条规则" % (
            s["chapters_scanned"], s["rules_run"]))
        print("blocker=%d warning=%d nit=%d" % (
            s["blocker"], s["warning"], s["nit"]))
        for f in result["findings"]:
            print("[%s][%s] %s:%d %s" % (
                f["severity"].upper(), f["rule_id"], f["file"],
                f["line"], f["title"]))
            print("    %s" % f["detail"])
            if f["snippet"]:
                print("    → %s" % f["snippet"])

    level = sev_rank[args.fail_on]
    bad = any(sev_rank.get(f.severity, 0) >= level for f in findings)
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
