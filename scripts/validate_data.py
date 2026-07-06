#!/usr/bin/env python3
"""validate_data.py — houmonkango-navi（kango）データ整合性チェック（lightweight, 標準ライブラリのみ・git のみ依存）

CLAUDE.md「ビルド後チェック」節を機械化したもの。他 3 repo（kyotaku / houmonshika /
shogaifukushi）と同型構造（load → count → required-field → link-spot →
baseline → summary の順）だが、この repo だけデータソースの置かれ方が根本的に
異なるため、実装内容は git 経由の read-only 検査になる。

## この repo 固有の前提（他 3 repo との違い）

- この repo（master）にはデータ実体・ビルド生成物が存在しない
  （pipeline scripts のみ・`data_sources/exports/` はこの PC に不在）。
- 公開サイトは `~/projects/MyPython/build_site.py --config
  site_config_houmon_kango.json` が生成し、**このrepoの `origin/gh-pages`
  ブランチへ push**（README.md 記載）。
- よって本 script は作業ツリーを checkout で切り替えず、
  `git ls-tree` / `git cat-file` で `origin/gh-pages` を **read-only** に
  検査する（`git fetch origin gh-pages` 済みであることが前提）。
- データ JSON がこの PC に存在しないため、「データ件数」起点の関係式・
  必須フィールドチェックは実施不能。gh-pages tree 内の生成物同士の関係式のみ
  チェックする（下記）。

## 件数の関係式（実測で裏取り済み・FAIL 対象）

  - station_html_count（gh-pages tree の station/*.html）
    == search_json_total（gh-pages tree の data/search/{01..47}.json 合計）
    2026-07-06 実測: 17,958 == 17,958 で一致確認済み（README記載の全国 17,958件
    とも一致）。

データ JSON 不在のため「データ件数 → detail 件数」の式は組めないが、
生成物間（HTML 実ファイル数 と 検索 JSON 件数）の一致は data 経由なしで
検証可能であり、実務上最も壊れやすい箇所（検索 JSON の生成漏れ・HTML
生成漏れ）を検出できる。

## WARN 止まりの項目（関係式が未確定）

  - sitemap.xml の <loc> 数、tree 内 HTML 総数: pref ページ・static ページ等
    station 以外の URL も含むため、厳密な関係式が未確定。

## 必須フィールドチェックについて

データ JSON がこの PC に存在しないため **実施不能・skip**（推測で埋めない）。
実施したい場合は MyPython 側の生成元データ or このrepoの rich pipeline 出力
（`stations_master_*.json`）をこの PC に用意してから拡張すること。

## internal link spot check の制約

gh-pages tree のファイル名は生 UTF-8（percent-encode されない）。Windows の
subprocess 経由で非 ASCII 引数を git に渡すと argv エンコーディングにより
文字化けするリスクがあるため、**ASCII のみの href**（`/about.html` 等の
ローマ字パス）に限定して `git cat-file -e` で存在確認する。都道府県直下の
市区町村ページ（日本語ファイル名）はこの軽量チェックの対象外とする
（全ページ走査はしない、という brief の方針にも合致）。

## baseline ファイル

scripts/validation_baseline.json（このrepo内・PHI なし・件数と実行時刻のみ）。
git 管理は人間判断。初回実行時は記録のみ、2 回目以降は前回との差分が 5% 超の
減少で FAIL、5% 以下の減少で WARN。

Usage:
    git fetch origin gh-pages   # 事前に実行しておく
    python scripts/validate_data.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Windows のデフォルト stdout エンコーディング（cp932）だと日本語ログが文字化けする
# 環境があるため、UTF-8 に固定する（CI の Ubuntu ランナー等では no-op）。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
GH_PAGES_REF = "origin/gh-pages"
BASELINE_FILE = REPO_ROOT / "scripts" / "validation_baseline.json"
BASELINE_DROP_FAIL_RATIO = 0.05  # 5% 超の減少で FAIL

results: list[tuple[str, str]] = []


def log(level: str, message: str) -> None:
    results.append((level, message))
    print(f"[{level}] {message}")


def git_ls_tree_files(path: str) -> list[str]:
    """origin/gh-pages:<path> 配下のファイル名一覧（サブディレクトリなし直下）を返す。"""
    proc = subprocess.run(
        ["git", "ls-tree", "--name-only", f"{GH_PAGES_REF}:{path}"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line]


def git_ls_tree_recursive_html_count() -> int:
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", GH_PAGES_REF],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        return 0
    return sum(1 for line in proc.stdout.splitlines() if line.endswith(".html"))


def git_show(path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{GH_PAGES_REF}:{path}"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_path_exists(path: str) -> bool:
    """path が ASCII のみである前提（呼び出し側でフィルタ済み）。"""
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{GH_PAGES_REF}:{path}"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return proc.returncode == 0


def sum_search_json_from_tree() -> int:
    files = git_ls_tree_files("data/search")
    total = 0
    for f in files:
        if not f.endswith(".json"):
            continue
        content = git_show(f"data/search/{f}")
        if content is None:
            continue
        total += len(json.loads(content))
    return total


def count_sitemap_locs_from_tree() -> int:
    content = git_show("sitemap.xml")
    if content is None:
        return 0
    return len(re.findall(r"<loc>", content))


def check_internal_link_spot() -> None:
    candidates = ["index.html", "about.html"]
    checked = 0
    broken: list[str] = []
    any_page_found = False
    for page in candidates:
        html = git_show(page)
        if html is None:
            continue
        any_page_found = True
        hrefs = re.findall(r'href="(/[^"#]*)"', html)
        for href in hrefs:
            if href.startswith("//"):
                continue
            path_part = href.split("?")[0].lstrip("/")
            if path_part == "":
                path_part = "index.html"
            elif path_part.endswith("/"):
                path_part += "index.html"
            if not path_part.isascii():
                continue  # 日本語ファイル名は Windows subprocess argv 文字化けリスクのため対象外
            checked += 1
            if checked > 10:
                break
            if not git_path_exists(path_part):
                broken.append(f"{page} -> {href}")
        if checked > 10:
            break

    if not any_page_found:
        log("WARN", "internal link spot check: index.html / about.html が取得できずスキップ")
        return

    if broken:
        log("WARN", f"internal link spot check（ASCII href のみ対象）: {checked} 件中 {len(broken)} 件のリンク切れ疑い: {broken[:5]}")
    else:
        log("OK", f"internal link spot check（ASCII href のみ対象・日本語ファイル名は対象外）: {checked} href を確認、リンク切れなし")


def check_baseline(metrics: dict[str, int]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if BASELINE_FILE.exists():
        try:
            previous = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = None

    if previous is None:
        log("OK", f"baseline: 初回記録（{BASELINE_FILE.name} に保存）")
    else:
        prev_metrics = previous.get("metrics", {})
        for key, current_value in metrics.items():
            prev_value = prev_metrics.get(key)
            if prev_value is None or prev_value == 0:
                continue
            if current_value >= prev_value:
                continue
            drop_ratio = (prev_value - current_value) / prev_value
            if drop_ratio > BASELINE_DROP_FAIL_RATIO:
                log("FAIL", f"baseline 差分: {key} が {prev_value} → {current_value}（{drop_ratio:.1%} 減少・5%超）")
            else:
                log("WARN", f"baseline 差分: {key} が {prev_value} → {current_value}（{drop_ratio:.1%} 減少）")

    # ラチェットガード（reviewer 指摘 2026-07-06）: FAIL 検出時は baseline を上書きしない。
    # 上書きすると件数減少 FAIL が naive リトライで緑化し「件数減少=停止」の警報が消えるため、
    # FAIL ゼロのときのみ現在値を新 baseline として記録する。
    if any(level == "FAIL" for level, _ in results):
        log("WARN", "baseline: FAIL 検出のため更新せず（解消後の実行で更新される）")
        return
    import datetime
    BASELINE_FILE.write_text(
        json.dumps({"last_run": datetime.datetime.now().isoformat(), "metrics": metrics}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    # gh-pages ブランチの存在確認（fetch 済み前提。無ければ明示して停止）
    verify = subprocess.run(
        ["git", "rev-parse", "--verify", GH_PAGES_REF],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if verify.returncode != 0:
        print(f"ERROR: {GH_PAGES_REF} が見つかりません。先に `git fetch origin gh-pages` を実行してください。")
        return 1

    log("OK", "データソース: このrepo（master）にはデータ実体なし。gh-pages tree を read-only 検査。")
    log("OK", "必須フィールドチェック: データ JSON がこの PC に不在のため skip（推測で埋めない）。")

    station_files = git_ls_tree_files("station")
    station_html_count = sum(1 for f in station_files if f.endswith(".html"))
    search_total = sum_search_json_from_tree()
    sitemap_locs = count_sitemap_locs_from_tree()
    total_html = git_ls_tree_recursive_html_count()

    log("OK", f"station HTML 件数（gh-pages tree 実測）: {station_html_count}件")
    log("OK", f"search JSON 合計件数: {search_total}件")
    log("OK", f"sitemap <loc> 数: {sitemap_locs}件 / tree 全 HTML: {total_html}件（関係式未確定・参考値）")

    if station_html_count == search_total:
        log("OK", f"件数整合: station_html({station_html_count}) == search_json_total({search_total})")
    else:
        log("FAIL", f"件数整合 NG: station_html({station_html_count}) != search_json_total({search_total})")

    check_internal_link_spot()

    metrics = {
        "station_html_count": station_html_count,
        "search_json_total": search_total,
        "sitemap_loc_count": sitemap_locs,
        "total_html_count": total_html,
    }
    check_baseline(metrics)

    fail_count = sum(1 for level, _ in results if level == "FAIL")
    warn_count = sum(1 for level, _ in results if level == "WARN")
    print(f"\n=== summary: FAIL={fail_count} WARN={warn_count} OK={len(results) - fail_count - warn_count} ===")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
