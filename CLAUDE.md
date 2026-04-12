# CLAUDE.md — houmonkango-navi

このファイルは、`houmonkango-navi` repo 固有の最小ルールを記述する。
共通ルール・保存判断基準・repo→project 対応表は `~/.claude/CLAUDE.md`（グローバル）を参照する。
ここには **この repo 固有の補足だけ** を書く。

repo: `houmonkango-navi`
project: `kango`
domain: 訪問看護ステーション検索ポータル（神奈川MVP → 全国展開予定）
姉妹サイト: `houmonshinsatsu-navi` (clinic) と相互リンク・共通基盤化を予定

---

## Obsidian 連携の最小ルール

### いつ Obsidian を読むか

- 軽微な修正（文言、typo、フォーマット、単発スクリプトの微調整）では Obsidian ノートの読み込みは **不要**
- 影響範囲が大きいタスクでは、実装前に relevant notes を確認する
- 特に以下では読むことを **優先する**:
  - 共通基盤・横断設計に関わる変更
  - SEO 方針・内部リンク設計
  - データ構造（共通スキーマ）の変更
  - 過去の意思決定を踏まえる必要がある変更
  - 久しぶりに再開するタスク

### 読む候補ノート

- `02_Projects/kango/index.md` — 現在地・重要論点・次アクション
- `02_Projects/clinic/index.md` — 姉妹サイトとの整合確認時
- `03_Strategy/data-platform/共通基盤設計.md` — スキーマ・パイプライン変更時
- `03_Strategy/seo/SEO共通方針.md` — 一覧/詳細ページ・内部リンク変更時
- `03_Strategy/domain/ドメイン戦略.md` — サブドメイン・URL構造変更時
- `04_Decisions/` 配下の関連ノート（特に `2026-04-12-サブドメイン方式採用.md`）
- 必要なら当日の `01_Daily/YYYY-MM-DD.md`

vault path: `C:\Users\volzs\Obsidian`

### 保存優先度（この repo 特有）

houmonkango-navi では以下のテーマを **保存優先度高め** として扱う。
これらは「他の repo（特に clinic）に横展開できる」または「将来の全国展開で必ず再利用する」知見。

1. **共通スキーマの拡張・変更**
   `models/` の Pydantic スキーマ。clinic と共通化する前提で、追加カラム・型変更・命名は必ず判断理由を残す。
2. **名寄せ・dedup ルール**
   厚労省CSV × 厚生局データのマージロジック。同一事業所判定キー（名称+住所+電話 等）の選定根拠は保存対象。clinic でも同じ問題が出る。
3. **廃業・休止ステーションの除外ロジック**（未実装）
   実装方針が決まったら必ず保存。clinic 側にも適用される横断ルールになる。
4. **データソース追加・全国展開時の流儀**
   全8地方厚生局対応・Excel/PDF パターンの違い・年次更新ラグへの対応方針。次の都道府県を増やすたびに必要になる。
5. **Feature 充填率の改善判断**
   24時間対応・精神科訪問・専門研修看護師など、低充填率項目を補完するソース選定や手法。
6. **clinic との相互リンク・横断検索の設計判断**
   サブドメイン横断 UI、相互リンクの粒度、共通フッタ等。横断設計の中核。

### 保存しないもの（この repo の例）

- パイプラインスクリプトの軽微な修正・パス変更
- 中間 CSV/JSON の一時的な集計
- 1回限りの探索的データ確認
- 既に Decision ノートに残してある内容の重複メモ

ただし、小修正でも上記6テーマのいずれかに波及する知見があれば保存候補にしてよい。

### 保存判断の出力

重要作業の最後には、必要に応じて以下を出力する（フォーマットはグローバル `CLAUDE.md` に準拠）。

- `SAVE_DECISION: yes / no`
- `SAVE_REASON:`
- `SAVE_CATEGORY:` project / strategy / decision / consultation / prompt / daily
- `SAVE_TITLE:`
- `SAVE_SUMMARY:`
- `NEXT_ACTIONS:`

`SAVE_CATEGORY` は houmonkango-navi では `decision`（設計判断）と `strategy`（共通基盤・横展開）が中心になる想定。
