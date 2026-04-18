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
  ├ scripts/fetch_*, parse_*, normalize_*     ├ build_site.py
  ├ scripts/merge_stations.py                 ├ site_config_houmon_kango.json
  ├ scripts/export_site_data.py               ├ convert_kango_data.py
  └ data_sources/exports/                     └ site_kango/ (ビルド出力)
     └ kanagawa_*.json (神奈川MVP 1,234件)
                                                     │
                                                     ▼ gh-pages push
                                              kango.zaitaku-navi.com
                                              (全国 17,958件, MHLW直変換)
```

**現在の接続状況（2026-04-18）**

- **公開サイト**: MyPython/convert_kango_data.py が厚労省CSVから直接生成（17,958件・全国）。これがメイン経路
- **本 repo の rich pipeline**: 神奈川 1,234件の richer JSON を data_sources/exports/ に出力
- **接続**: convert_kango_data.py に overlay 経路を実装。現状 `supports_24h` のみが公開系に反映されている（神奈川927件の 24時間訪問看護 バッジ）
- **残り feature**（精神科訪問・特別管理・専門研修看護師・機能強化型・医療DX・ベースアップ）: データ自体は exports/ にあるが、overlay・表示未実装

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
# 全パイプライン一括実行
python scripts/run_pipeline.py

# 個別実行
python scripts/fetch_mhlw.py           # 厚労省CSV取得
python scripts/fetch_kouseikyoku.py     # 厚生局データ取得
python scripts/parse_kouseikyoku.py     # 厚生局データパース
python scripts/normalize_stations.py    # 正規化
python scripts/merge_stations.py        # 統合
python scripts/export_site_data.py      # 出力
```

## データソース

| ソース | 説明 | ライセンス | 件数 |
|--------|------|----------|------|
| 厚労省 jigyosho_130.csv | 訪問看護オープンデータ | CC BY 4.0 | 17,959件（全国） |
| 関東信越厚生局 | 届出受理指定訪問看護事業所名簿 | 政府標準利用規約 | 1,283件（管轄10都県） |

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

## 出力ファイル（神奈川MVP）

| ファイル | 内容 | 件数 |
|---------|------|------|
| kanagawa_stations_master.csv | マスターCSV | 1,234件 |
| kanagawa_stations_master.json | マスターJSON | 1,234件 |
| kanagawa_all.json | サイト表示用軽量JSON | 1,234件 |
| city_index.json | 市区町村インデックス | 62市区町村 |
| kanagawa_review_candidates.csv | 要確認レコード | - |
| kanagawa_source_summary.md | サマリレポート | - |

## 神奈川MVP Feature充填率

| 項目 | 充填率 |
|------|--------|
| 24時間対応体制加算 | 75.1% |
| 精神科訪問看護 | 31.5% |
| 特別管理加算 | 84.8% |
| 専門研修看護師 | 48.9% |
| 医療DX加算 | 93.4% |
| ベースアップ評価料 | 45.3% |
| 郵便番号 | 93.6% |
| 緯度経度 | 100% |

## 現時点の制約

- 公開サイトは全国 17,958件掲載済み（厚労省CSV直変換）
- 本 repo の rich pipeline は神奈川 1,234件分のみ完成（feature充填あり）。他46都道府県は厚労省CSV由来の基本項目のみ
- 厚労省CSVは年2回更新（6月末・12月末時点）のため最大6ヶ月のラグ
- 厚生局データはPDF版のみの都県あり（Excel ZIP展開で対応済み）
- 郵便番号は厚生局データからの補完（厚労省CSVに含まれない）
- 廃業・休止ステーションの完全な除外は未実装

## 次フェーズの拡張案

- [ ] 全国展開（47都道府県）
- [ ] 全8地方厚生局のExcel/PDF対応
- [ ] Google Places連携（営業時間・口コミ・写真）
- [ ] 地図ページ生成
- [ ] 市区町村別ページ生成
- [ ] 在宅クリニックナビとの相互リンク
- [ ] 定期更新の自動化（GitHub Actions）

## 運営

MDX株式会社
