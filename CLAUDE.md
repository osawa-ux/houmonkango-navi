# CLAUDE.md — houmonkango-navi

このファイルは、`houmonkango-navi` repo 固有の最小ルールを記述する。
共通ルール・保存判断基準・repo→project 対応表は `~/.claude/CLAUDE.md`（グローバル）を参照する。
ここには **この repo 固有の補足だけ** を書く。

repo: `houmonkango-navi`
project: `kango`
domain: 訪問看護ステーション検索ポータル
- 公開サイト: kango.zaitaku-navi.com で全国 17,958件掲載済み（厚労省CSV直変換、MyPython/build_site.py で生成）
- rich pipeline: 本 repo の scripts/ が神奈川 1,234件の feature 付き JSON を出力
- 接続: MyPython/convert_kango_data.py に overlay 経路あり。現状 supports_24h のみが公開系に反映
姉妹サイト: `houmonshinsatsu-navi` (clinic) と相互リンク・共通基盤化を予定

---

## Obsidian 連携の最小ルール

共通方針: `~/.claude/CLAUDE.md`（グローバル）と Obsidian Vault の `_Vault運用方針.md` を参照。
ここには **この repo 固有の参照先だけ** を置く。

vault path: `C:\Users\Motoi\R8.4 Obsidian`

### この repo で優先参照する Obsidian ノート

- `20_Projects/houmonshinsatsu-navi/index.md` — 姉妹サイト（共通基盤・横展開の参考）
- 現時点で kango 専用の SOP / project index は未整備。必要になったら `70_SOP/` または `20_Projects/kango/` に新設する

### 保存の扱い

- **一次保存の主役は Daily**: `10_Daily/YYYY-MM-DD.md`（通常はここ）
- **Inbox は未分類メモの一時置き場のみ**: `00_Inbox/`（常用しない、最小限）
- **Project ログは未整備**: kango 専用 Project index は未作成。必要になったら `20_Projects/kango/` に新設
- **恒久保存は明示指示 or レビュー採択時のみ**: `70_SOP/` / `30_Areas/` / `50_Research/` / Project index の恒久要約欄
- 自動保存は 3〜6行の短い要約（何をした / 何が決まった / 次の宿題）
- **push-pc は作業の締め処理**: 直前に日次レビュー（30秒〜3分）。必要なら Daily に一次保存、Project ログ昇格 / SOP化候補を軽く判断してから push-pc
- 月次レビューは補助（日々の取りこぼし棚卸し・昇格・Archive 判断）
- 作業完了時は「追記先 + 要約 + 日次レビュー判断」または「保存判断 + 理由」を簡潔に報告
- 詳細は Vault の `_Vault運用方針.md` 末尾「Claude Code による自動記録ルール」参照
