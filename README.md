# 訪問看護ステーションナビ

全国の訪問看護ステーション検索ポータル。

- 公開URL: **https://kango.zaitaku-navi.com/**
- 公開リポジトリ: `osawa-ux/houmonkango-navi`（public）
- データ件数: **17,958件 / 47都道府県**
- ホスティング: GitHub Pages + Cloudflare DNS
- ビルド: `~/projects/MyPython/build_site.py --config site_config_houmon_kango.json`

## アーキテクチャ概要

公開系と rich データパイプラインは意図的に別 repo 分離されている。

```
[このrepo] houmonkango-navi                [別repo] MyPython
  データ収集・正規化パイプライン              公開サイト生成
  ├ config/sources.yaml (bureau定義)          ├ build_site.py
  ├ scripts/pref_meta.py (47都道府県meta)     ├ site_config_houmon_kango.json
  ├ scripts/fetch_kouseikyoku.py --bureau     ├ convert_kango_data.py (glob overlay)
  ├ scripts/normalize/parse/merge/export      └ site_kango/ (ビルド出力)
  │   はすべて --pref <県名> 引数対応
  └ data_sources/exports/
     └ stations_master_{pref_romaji}.json
                                                     │
                                                     ▼ gh-pages push
                                              kango.zaitaku-navi.com
                                              (全国 17,958件, MHLW直変換 + feature overlay)
```

**現在の接続状況（2026-04-20）**

- **公開サイト**: MyPython/convert_kango_data.py が厚労省CSVから直接生成（17,958件・全国）をベースに、本 repo の rich pipeline 出力 `stations_master_*.json` を glob で overlay
- **rich pipeline 対応済 23都府県**（被覆率 58.5%、10,500件）:
  - 関東信越（10）: 茨城・栃木・群馬・埼玉・千葉・東京・神奈川・新潟・山梨・長野
  - 近畿（7）: 福井・滋賀・京都・大阪・兵庫・奈良・和歌山
  - 東海北陸（6）: 富山・石川・岐阜・静岡・愛知・三重
- **表示中の feature**（4種、`site_config.feature_badges` で宣言的定義）:
  - 24時間訪問看護 (8,072件)
  - 精神科訪問看護 (4,275件)
  - 特別管理加算 (9,828件)
  - 専門研修看護師 (5,701件)
- **保留中の feature**: `function_strengthening_type` (boolean化済だが type 1/2/3 取得不可のため UI 未追加) / `medical_dx_addition` / `base_up_eval` (UI 非表示継続)
- **未対応 5厚生局 (24県, 5,684件)**: 九州・中国四国・四国支局・東北・北海道

## 公開状況（2026-04-12）

| 項目 | 状態 |
|------|------|
| ドメイン取得 (Namecheap) | ✓ zaitaku-navi.com |
| Cloudflare zone | ✓ active (`d2ee309f0a2fb373a09f0deb6669d7a2`) |
| Cloudflare CNAME | ✓ kango → osawa-ux.github.io |
| GitHub Pages | ✓ gh-pages ブランチ / built / built |
| SSL証明書 | ✓ Let's Encrypt approved |
| HTTPS強制 | ✓ enforced |
| Formspree (contact) | ✓ `xzdknkvw` |
| Formspree (premium) | ✓ `xpqovoja` |
| GA4 測定ID | ⏳ 未設定 |
| Search Console | ✓ sc-domain:zaitaku-navi.com (siteOwner) |

## デプロイ運用

### gh-pages worktree 方式（master を汚さない）

```bash
# 初回のみ
cd ~/projects/houmonkango-navi
git fetch origin
git worktree add --orphan -B gh-pages /tmp/houmonkango-gh-pages

# 再デプロイ
cd ~/projects/MyPython
python build_site.py --config site_config_houmon_kango.json
cd /tmp/houmonkango-gh-pages
find . -mindepth 1 -not -path './.git*' -delete
cp -a ~/projects/MyPython/site_kango/. .
git add -A
git commit -m "Update site (YYYY-MM-DD)"
git push origin gh-pages
```

詳細は [docs/custom-domain-deploy.md](docs/custom-domain-deploy.md) を参照。

### カスタムドメイン設定 CLI

`scripts/setup_custom_domain.py` で Cloudflare DNS と GitHub Pages の設定を半自動化。

```bash
python scripts/setup_custom_domain.py plan
python scripts/setup_custom_domain.py apply
python scripts/setup_custom_domain.py verify
python scripts/setup_custom_domain.py enable-https
```

---

## データ収集パイプライン

## セットアップ

```bash
pip install -r requirements.txt
```

## 実行方法

```bash
# 厚労省 CSV 取得（全国）
python scripts/fetch_mhlw.py

# 厚生局データ取得（bureau 単位）
python scripts/fetch_kouseikyoku.py --bureau kantoshinetsu
python scripts/fetch_kouseikyoku.py --bureau kinki
python scripts/fetch_kouseikyoku.py --bureau tokaihokuriku

# 県単位のパイプライン
python scripts/normalize_stations.py --pref 神奈川県
python scripts/parse_kouseikyoku.py   --pref 神奈川県
python scripts/merge_stations.py      --pref 神奈川県
python scripts/export_site_data.py    --pref 神奈川県

# 公開サイト生成（MyPython 側）
cd ~/projects/MyPython
python convert_kango_data.py --csv                              # stations_master_*.json を glob で overlay
python build_site.py --config site_config_houmon_kango.json     # site_kango/ を生成
```

※ `scripts/run_pipeline.py` は --pref 未対応のため神奈川固定動作。全国展開時は個別スクリプト経由推奨。

## データソース

| ソース | 説明 | ライセンス | 件数 |
|--------|------|----------|------|
| 厚労省 jigyosho_130.csv | 訪問看護オープンデータ | CC BY 4.0 | 17,959件（全国） |
| 関東信越厚生局 | 届出受理指定訪問看護事業所名簿 | 政府標準利用規約 | 10都県 |
| 近畿厚生局 | 訪問看護事業所名簿 ZIP | 政府標準利用規約 | 7府県 |
| 東海北陸厚生局 | 訪問看護事業所名簿 ZIP | 政府標準利用規約 | 6県 |

## ディレクトリ構成

```
data_sources/
  mhlw/            # 厚労省CSV原本
  kouseikyoku/     # 厚生局Excel/PDF原本
  processed/       # 正規化・統合中間データ
  exports/         # 最終出力（CSV/JSON/MD）
scripts/           # パイプラインスクリプト群
models/            # Pydanticスキーマ定義
config/            # ソースURL・スキーマ定義
```

## 出力ファイル（県単位、すべて `{pref_romaji}` 接尾辞付き）

| ファイル | 内容 |
|---------|------|
| `mhlw_normalized_{romaji}.csv` | 正規化済み MHLW 母集団 (processed/) |
| `kouseikyoku_features_{romaji}.csv` | 厚生局 feature (processed/) |
| `stations_merged_{romaji}.csv` | 統合データ (processed/) |
| `stations_master_{romaji}.{csv,json}` | マスター出力（MyPython 側が glob で拾う） |
| `stations_all_{romaji}.json` | サイト表示用軽量 JSON |
| `city_index_{romaji}.json` | 市区町村インデックス |
| `review_candidates_{romaji}.csv` | 要確認レコード |
| `source_summary_{romaji}.md` | サマリレポート |

## 対応 23都府県の件数 / match 率サマリ

| 厚生局 | 対応県 | 公開件数 |
|---|---|---|
| 関東信越 | 茨城・栃木・群馬・埼玉・千葉・東京・神奈川・新潟・山梨・長野 | 5,661 |
| 近畿 | 福井・滋賀・京都・大阪・兵庫・奈良・和歌山 | 3,819 |
| 東海北陸 | 富山・石川・岐阜・静岡・愛知・三重 | 2,610 |
| **小計** | **23都府県** | **12,090** |

充填率の典型（関東信越・近畿・東海北陸で類似分布）:

| 項目 | 典型充填率 |
|------|--------|
| 24時間対応体制加算 | 65-80% |
| 精神科訪問看護 | 30-50% |
| 特別管理加算 | 85-95% |
| 専門研修看護師 | 35-55% |
| 医療DX加算 | 93-98% |
| ベースアップ評価料 | 35-65% |

## 現時点の制約

- 公開サイトは全国 17,958件掲載済み（厚労省CSV直変換）
- rich pipeline 対応済は 23都府県 = 全体の約 58.5%（10,500件に feature badge 反映）
- 残り 24道県は厚労省CSV由来の基本項目のみ
- 厚労省CSVは年2回更新（6月末・12月末時点）のため最大6ヶ月のラグ
- 厚生局データの ZIP はネストしたディレクトリ構造があり、fetch 時に flatten 展開する
- 郵便番号は厚生局データからの補完（厚労省CSVに含まれない）
- 廃業・休止ステーションの完全な除外は未実装
- `function_strengthening_type`（機能強化型）は厚生局公開データから type 1/2/3 を抽出不可、boolean 保持のみ
- 東京の 末尾6桁マッチ率 65.3%（他県 > 90%）は station_id 衝突起因、将来の精度改善余地

## 次フェーズの拡張案

- [x] 関東信越（10都県）対応
- [x] 近畿（7府県）対応
- [x] 東海北陸（6県）対応
- [ ] 九州厚生局（8県含沖縄）PoC + 全件化
- [ ] 中国四国・四国支局（8県）PoC + 全件化
- [ ] 東北厚生局（6県）PoC + 全件化
- [ ] 北海道厚生局（1道）PoC（形式未確定）
- [ ] `medical_dx_addition` / `base_up_eval` の UI 露出判断
- [ ] `function_strengthening_type` の type 1/2/3 別ソース調査
- [ ] GA4 測定ID 反映（受領待ち）
- [ ] Google Places連携（営業時間・口コミ・写真）
- [ ] 地図ページ生成
- [ ] 在宅クリニックナビとの相互リンク
- [ ] 定期更新の自動化（GitHub Actions）

## 運営

MDX株式会社
