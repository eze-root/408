"""Compare editable local papers with the cached public corpus; never merge sources."""
from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import unicodedata

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

from scripts.build_papers import IMAGE, PAPERS, ROOT, parse_paper
from scripts.collect_beokayy import html_document, timestamp, write_file, write_json


MD = MarkdownIt("commonmark", {"html": True}).enable("table")


def markdown_text(value):
    value = IMAGE.sub("", value)
    value = re.sub(r"^\s*[（(]\s*\d+\s*分\s*[）)]", "", value)
    return BeautifulSoup(MD.render(value), "html.parser").get_text()


def normalized(value):
    # Preserve numbers, operators and all words. This is text equivalence, not proof.
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\[图片:[^\]]*\]", "", value)
    return re.sub(r"\s+", "", value).translate(str.maketrans({"，": ",", "。": ".", "；": ";", "：": ":"}))


def fingerprints(value):
    value = normalized(value)
    return {value[i:i+3] for i in range(max(1, len(value)-2))}


def similarity(left, right):
    a, b = fingerprints(left), fingerprints(right)
    return 2 * len(a & b) / max(1, len(a) + len(b))


def option_permutation(local, remote):
    if len(local) != 4 or len(remote) != 4:
        return None
    left, right = [normalized(x) for x in local], [normalized(x) for x in remote]
    if len(set(left)) != 4 or set(left) != set(right):
        return None
    return {chr(65+i): chr(65+right.index(value)) for i, value in enumerate(left)}


def changes(left, right):
    a, b = normalized(left), normalized(right)
    result = []
    for op, i, j, k, l in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            result.append({"operation": op, "local": a[i:j], "remote": b[k:l],
                           "before": a[max(0, i-20):i], "after": a[j:j+20]})
    return result


def compare(dataset: Path, output: Path):
    remote = [json.loads(line) for line in (dataset / "questions.jsonl").read_text().splitlines()]
    remote_by_id = {q["id"]: q for q in remote}
    if len(remote_by_id) != len(remote):
        raise ValueError("采集数据中有重复题号")
    manifest = json.loads((PAPERS / "manifest.json").read_text())
    records, local_questions, input_hashes = [], {}, {}
    for year in sorted(manifest):
        path = PAPERS / f"{year}.md"
        input_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        paper = parse_paper(path.read_text(), year=year, metadata=manifest[year])
        for q in paper["questions"]:
            qid = f"{year}-{q['number']:02d}"
            local_questions[qid] = {**q, "id": qid, "year": int(year),
                                   "stem_text": markdown_text(q["body"]),
                                   "options_text": [markdown_text(o) for o in q["options"]],
                                   "known_issue": q["number"] in manifest[year]["incomplete_questions"]}
    for q in remote:
        qid = q["id"]
        local = local_questions.get(qid)
        record = {"id": qid, "year": q["year"], "number": q["number"], "source_url": q["source"]["url"]}
        if local is None:
            record.update(status="new_year", flags=["本地尚无该年份可编辑试卷"])
            records.append(record)
            continue
        local_stem, remote_stem = local["stem_text"], q["stem"]["text"]
        options = [o["text"] for o in q["options"]]
        local_images = IMAGE.findall(local["body"] + "\n" + "\n".join(local["options"]))
        remote_images = sorted({u for b in [q["stem"], *q["options"]] for u in b["image_urls"]})
        local_score_match = re.match(r"[（(]\s*(\d+)\s*分[）)]", local["body"])
        local_score = 2 if q["number"] <= 40 else int(local_score_match[1]) if local_score_match else None
        same_stem = normalized(local_stem) == normalized(remote_stem)
        same_options = [normalized(o) for o in local["options_text"]] == [normalized(o) for o in options]
        same_similarity = similarity(local_stem, remote_stem)
        alternatives = [r for r in remote if r["year"] == q["year"]]
        best = max(alternatives, key=lambda r: similarity(local_stem, r["stem"]["text"]))
        best_score = similarity(local_stem, best["stem"]["text"])
        flags = []
        if best["id"] != qid and best_score >= .55 and best_score > same_similarity + .15:
            flags.append("疑似题号错位，须人工确认")
        if local_score is not None and local_score != q["score"]:
            flags.append("单题分值不同")
        if not same_options:
            flags.append("选项文字不同，不能直接套用答案字母")
        if local["known_issue"]:
            flags.append("本地已记录疑点")
        if local_images or remote_images:
            flags.append("含配图，图片内容需目视核对")
        if len(local_images) != len(remote_images):
            flags.append("配图数量不同")
        if same_similarity < .55:
            flags.append("题干文字差异较大")
        record.update({"status": "text_equivalent" if same_stem and same_options else "text_different",
                       "same_stem_text": same_stem, "same_options_text": same_options,
                       "stem_similarity": round(same_similarity, 4),
                       "best_candidate": best["id"], "best_candidate_similarity": round(best_score, 4),
                       "option_permutation": option_permutation(local["options_text"], options),
                       "local_score": local_score, "remote_score": q["score"],
                       "local_images": local_images, "remote_images": remote_images,
                       "flags": flags, "stem_changes": changes(local_stem, remote_stem),
                       "option_changes": {chr(65+i): changes(a, b) for i, (a, b) in enumerate(zip(local["options_text"], options)) if normalized(a) != normalized(b)}})
        records.append(record)
    shared = [r for r in records if r["status"] != "new_year"]
    summary = {"generated_at": timestamp(), "local_count": len(local_questions), "remote_count": len(remote),
               "shared_ids": len(shared), "local_only_ids": sorted(set(local_questions)-set(remote_by_id)),
               "new_ids": [r["id"] for r in records if r["status"] == "new_year"],
               "status_counts": dict(Counter(r["status"] for r in records)),
               "flag_counts": dict(Counter(flag for r in shared for flag in r["flags"])),
               "input_sha256": input_hashes,
               "remote_jsonl_sha256": hashlib.sha256((dataset / "questions.jsonl").read_bytes()).hexdigest(),
               "method": "按年份和题号对应；NFKC、空白及中文标点归一化后比较题干和选项。字符三元组相似度仅筛查疑似错位；不自动判定哪版正确。图片不由文字相似度判定。"}
    write_json(output / "comparison.json", {"summary": summary, "questions": records})
    summary_rows = "".join(f"<li>{html.escape(k)}：{v}</li>" for k, v in summary["flag_counts"].items())
    score_rows = "".join(f'<tr><td>{r["id"]}</td><td>{r["local_score"]}</td><td>{r["remote_score"]}</td></tr>'
                         for r in shared if "单题分值不同" in r["flags"])
    body = ["<h1>408 本地试卷与题库对比</h1>",
            f"<p>本地 {len(local_questions)} 题；采集 {len(remote)} 题；同年份同题号 {len(shared)} 题；新增 {len(summary['new_ids'])} 题。</p>",
            "<p>按年份和题号对应，展开条目查看题干、选项、图片和分值差异。</p>",
            f"<ul>{summary_rows}</ul>",
            "<h2>项目层面的重合与差别</h2><p>真题浏览、知识点分类和考纲入口与现有资料站存在功能重合。现有项目的四科复习提纲、专项练习方法、套卷复盘模板、人工勘误记录和可编辑 Typst 排版仍可继续使用。此次整理的是公开题库快照，不包含原站账号、个人错题记录或在线做题功能。</p>",
            "<h2>分值差异</h2><p>以下保留本地修订值与采集快照值，修订结论见 typst/papers/corrections-2026-10-29.json。</p>",
            f"<table><tr><th>题号</th><th>本地分值</th><th>采集分值</th></tr>{score_rows}</table>",
            "<p>2024-04 已按扫描题页修正：b、d 的度为 2、4，答案为 B。</p>",
            "<p>2023-43 采用 a[24][64]；2023-44 的两处机器码已通过汇编器验证并修正。2012、2014 年保留本地题头分值。2025 年第 44、45、46 题采用 11、7、8 分。</p>",
            "<p>本地正式下载页提供 2009—2026 年试题、答题纸，以及 2025、2026 年答案与解析。采集快照保留作资料对照。</p>",
            "<h2>逐题对照</h2><p>比较范围为本地 typst/papers 的可编辑题面与采集题库。折叠条目展示两版题干、选项和图片。</p>"]
    for year in sorted({q["year"] for q in remote}, reverse=True):
        body.append(f'<h2 id="y{year}">{year} 年</h2>')
        for record in (r for r in records if r["year"] == year):
            qid = record["id"]
            q = remote_by_id[qid]
            label = {"new_year": "新增年份", "text_equivalent": "文字归一化后一致", "text_different": "文字存在差异"}[record["status"]]
            body.append(f'<details id="{qid}"><summary>{qid} · {label} · {html.escape("；".join(record["flags"]))}</summary>')
            if record["status"] != "new_year":
                local = local_questions[qid]
                raw = local["body"] + "\n\n" + "\n\n".join(f"{chr(65+i)}. {o}" for i,o in enumerate(local["options"]))
                rendered = BeautifulSoup(MD.render(raw), "html.parser")
                for image in rendered.select("img[src]"):
                    src = (ROOT / "typst" / image["src"]).resolve()
                    if not src.is_relative_to(ROOT / "typst/assets") or not src.is_file():
                        raise ValueError(f"Missing local image {src}")
                    target = "assets/local-" + hashlib.sha256(src.read_bytes()).hexdigest()[:20] + src.suffix
                    (output / "assets").mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, output / target)
                    image["src"] = target
                body.append('<h3>本地人工稿</h3>' + str(rendered))
                body.append(f'<p>题干相似度 {record["stem_similarity"]}；本地分值 {record["local_score"]} / 采集分值 {record["remote_score"]}。最相近题号：{record["best_candidate"]}。</p>')
            rendered = BeautifulSoup(q["stem"]["html"] + "".join(f'<p><b>{o["label"]}.</b></p>{o["html"]}' for o in q["options"]), "html.parser")
            assets = {a["url"]: a for a in q["assets"]}
            for image in rendered.select("img[src]"):
                image["src"] = "../" + assets[image["src"]]["path"]
            body.append('<h3>采集题面</h3>' + str(rendered))
            body.append(f'<p><a href="{html.escape(q["source"]["url"], quote=True)}">原站来源</a></p></details>')
    write_file(output / "index.html", html_document("408 真题对比", "\n".join(body)))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "resources/beokayy")
    parser.add_argument("--output", type=Path, default=ROOT / "resources/beokayy/comparison")
    args = parser.parse_args()
    print(json.dumps(compare(args.dataset, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
