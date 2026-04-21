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

## 上位原則
本repoは Obsidian の `30_Areas/開発運用原則.md` を上位原則として参照する。
repo固有ルールはこの CLAUDE.md に限定し、原則全文は複製しない。

## 量産原則上の位置付け
本repoは clinic（houmonshinsatsu-navi）の同型量産の2番目にあたる。

- MyPython/build_site.py を共通基盤として利用する
- kango専用のscriptsはあくまで差分（神奈川rich pipeline等）
- 実装方針に迷ったら、まず「clinicで既にやっているか」を先に確認する
- kango独自ロジックを足すときは、shika/care/welfareへ横展開可能な形を優先する
- 差分はできるだけ設定ファイル・テンプレート・データで吸収する

## API優先
- データソースは厚労省CSV直変換（構造化データ）を基本とする
- スクレイピングやPlaywrightは、API/CSVで完結しないときの第二選択
- 採用理由はscript内コメントに残す

## ビルド後チェック
build後、デプロイ前にPlaywright等で以下を機械チェックする。
- 代表ページ（トップ / 都道府県 / 市区町村 / 個別）が開く・console error無し
- 検索JSON件数と個別HTML数の整合
- 主要内部リンクが生きているか

---

## Obsidian 連携の最小ルール

共通方針: `~/.claude/CLAUDE.md`（グローバル）と Obsidian Vault の `_Vault運用方針.md` を参照。
ここには **この repo 固有の参照先だけ** を置く。

vault path: 動的解決 — `python ~/.claude/skills/_shared/resolve_vault.py` で取得（別PC・vault移動にも追従）

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
