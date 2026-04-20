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

- 自動で Obsidian に追記しない
- 保存すべきと判断したら **保存候補として提案する**（タイトル案・配置先案・要約の3点）
- ユーザーの明示指示があったときだけ Obsidian に追記する
