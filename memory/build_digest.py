#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""從 lessons.md／rulings.md 自動產生 digest.md（一行一條的摘要表）。

開工只讀 digest.md；全文留在原檔用 grep 查。digest 是本機產生物，不進 git（.gitignore），每次開工重產，不要手改：
    python memory/build_digest.py          # 重新產生
    python memory/build_digest.py --check  # 和現有 digest.md 比對，不同就 exit 1
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "digest.md")

# 每個檔要抽哪一欄當摘要，依序找第一個有的。
SOURCES = [
    {
        "file": "lessons.md",
        "title": "教訓（lessons）",
        "prefix": "L",
        "summary_keys": ["規則", "教訓", "錯誤", "錯"],
        "status_key": None,
        "columns": ("ID", "日期", "規則"),
    },
    {
        "file": "rulings.md",
        "title": "裁決（rulings）",
        "prefix": "R",
        "summary_keys": ["裁決", "套用", "細節", "實作", "原話"],
        "status_key": "狀態",
        "columns": ("ID", "日期", "狀態", "裁決"),
    },
]

FIELD_RE = re.compile(r"^- \*{0,2}(?P<key>[^*：:]+?)\*{0,2}\s*[：:]\s*(?P<val>.*)$")


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def parse_entries(text, prefix):
    """回傳 [(id, {欄位: 值})]，略過範例 X-999。"""
    entries = []
    blocks = re.split(r"^### ", text, flags=re.M)[1:]
    for block in blocks:
        head, _, body = block.partition("\n")
        id_ = head.strip()
        if not re.fullmatch(rf"{prefix}-\d{{3}}", id_) or id_.endswith("999"):
            continue
        fields = {}
        last_key = None
        for line in body.splitlines():
            if line.startswith("### ") or line.strip() == "---":
                break
            m = FIELD_RE.match(line)
            if m:
                last_key = m.group("key").strip()
                fields.setdefault(last_key, m.group("val").strip())
            elif last_key and line.startswith("  ") and line.strip():
                # 續行（縮排子彈）併進同一欄，用空格接
                fields[last_key] += " " + line.strip()
        entries.append((id_, fields))
    return entries


MAX_CHARS = 90  # 摘要只留第一句、超過就截斷，細節查原檔


def first_sentence(s):
    m = re.search(r"。", s)
    return s[: m.start() + 1] if m else s


def cell(s, limit=None):
    s = re.sub(r"\s+", " ", s or "").strip().replace("|", "｜")
    if limit:
        s = first_sentence(s)
        if len(s) > limit:
            s = s[: limit - 1].rstrip() + "…"
    return s


def short_status(s):
    s = cell(s)
    if not s:
        return "—"
    for k in ("已廢止", "暫定", "有效"):
        if s.startswith(k):
            return k
    return s.split("（")[0][:6]


def build():
    out = []
    out.append("# memory 摘要表（digest）\n")
    out.append(
        "**自動產生，不要手改。**來源 `lessons.md`、`rulings.md`；不進 git，每次開工跑 `python memory/build_digest.py` 重產。"
        "每條只留一句規則／裁決；要看發生什麼、理由、來源、相關 ID，"
        "用 `grep -n '^### L-012' memory/lessons.md` 之類的方式查原檔，不要整份讀。\n"
    )
    for src in SOURCES:
        text = read(os.path.join(HERE, src["file"]))
        entries = parse_entries(text, src["prefix"])
        # 狀態不是「有效」的（暫緩、被取代、廢止）只列 ID，不佔表格列
        inactive = [id_ for id_, f in entries
                    if src["status_key"] and short_status(f.get(src["status_key"], "")) != "有效"]
        entries = [e for e in entries if e[0] not in inactive]
        out.append(f"\n## {src['title']}：{len(entries)} 條\n")
        out.append("| " + " | ".join(src["columns"]) + " |")
        out.append("|" + "---|" * len(src["columns"]))
        for id_, f in entries:
            summary = ""
            for k in src["summary_keys"]:
                if f.get(k):
                    summary = f[k]
                    if k != src["summary_keys"][0]:
                        summary = f"（{k}）{summary}"
                    break
            row = [id_, cell(f.get("日期", ""))[:10] or "—"]
            if src["status_key"]:
                row.append(short_status(f.get(src["status_key"], "")))
            row.append(cell(summary, MAX_CHARS) or "（無摘要欄，查原檔）")
            out.append("| " + " | ".join(row) + " |")
        if inactive:
            out.append(f"\n非有效（暫緩／被取代／廢止，查原檔）：{'、'.join(inactive)}")
    return "\n".join(out) + "\n"


def main(argv):
    content = build()
    if "--check" in argv:
        if not os.path.exists(OUT):
            print("digest.md 不存在，請跑 python memory/build_digest.py", file=sys.stderr)
            return 1
        if read(OUT) != content:
            print("memory/digest.md 和 lessons.md／rulings.md 不一致，請跑 python memory/build_digest.py 再 commit", file=sys.stderr)
            return 1
        return 0
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    n = content.count("\n| ") - 2
    print(f"wrote {OUT}: {n} rows, {len(content.encode('utf-8'))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
