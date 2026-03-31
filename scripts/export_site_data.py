"""
サイト生成用データの出力

入力: data_sources/processed/stations_merged.csv
出力:
- data_sources/exports/kanagawa_stations_master.csv
- data_sources/exports/kanagawa_stations_master.json
- data_sources/exports/kanagawa_all.json (サイト用)
- data_sources/exports/city_index.json (市区町村インデックス)
- data_sources/exports/kanagawa_source_summary.md (サマリレポート)
"""

import pandas as pd
import json
import os
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data_sources", "processed")
EXPORTS_DIR = os.path.join(BASE_DIR, "data_sources", "exports")

# 出力に含めるカラム（内部キーは除外）
MASTER_COLUMNS = [
    "station_id", "name", "name_kana", "prefecture", "city", "address",
    "postal_code", "tel", "fax", "corporation_name", "office_code",
    "latitude", "longitude", "website_url", "source_primary",
    "source_url", "source_updated_at", "is_active",
]

FEATURE_COLUMNS = [
    "supports_24h", "psychiatric_visit_nursing", "special_management_addition",
    "specialized_training_nurse", "function_strengthening_type",
    "medical_dx_addition", "base_up_eval",
]

# 軽量サイト用カラム
SITE_COLUMNS = [
    "station_id", "name", "name_kana", "city", "address",
    "tel", "fax", "corporation_name", "latitude", "longitude",
    "website_url", "is_active",
    "supports_24h", "psychiatric_visit_nursing",
    "function_strengthening_type",
]


def load_merged() -> pd.DataFrame:
    path = os.path.join(PROCESSED_DIR, "stations_merged.csv")
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str)


def export_master_csv(df: pd.DataFrame):
    """マスターCSV出力"""
    cols = [c for c in MASTER_COLUMNS + FEATURE_COLUMNS if c in df.columns]
    output = df[cols].copy()
    path = os.path.join(EXPORTS_DIR, "kanagawa_stations_master.csv")
    output.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[export] CSV: {path} ({len(output):,}件)")
    return path


def export_master_json(df: pd.DataFrame):
    """マスターJSON出力"""
    cols = [c for c in MASTER_COLUMNS + FEATURE_COLUMNS if c in df.columns]
    records = df[cols].to_dict(orient="records")
    # NaN → None変換
    for r in records:
        for k, v in r.items():
            if isinstance(v, float) and pd.isna(v):
                r[k] = None
            elif v == "nan" or v == "None":
                r[k] = None
    path = os.path.join(EXPORTS_DIR, "kanagawa_stations_master.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[export] JSON: {path} ({len(records):,}件)")
    return path


def export_site_json(df: pd.DataFrame):
    """サイト表示用の軽量JSON出力"""
    cols = [c for c in SITE_COLUMNS if c in df.columns]
    records = df[cols].to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if isinstance(v, float) and pd.isna(v):
                r[k] = None
            elif v == "nan" or v == "None":
                r[k] = None
        # 緯度経度を数値に変換
        for geo in ["latitude", "longitude"]:
            if geo in r and r[geo] is not None:
                try:
                    r[geo] = float(r[geo])
                except (ValueError, TypeError):
                    r[geo] = None

    path = os.path.join(EXPORTS_DIR, "kanagawa_all.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[export] サイト用JSON: {path} ({len(records):,}件)")
    return path


def export_city_index(df: pd.DataFrame):
    """市区町村インデックス"""
    city_data = defaultdict(lambda: {"count": 0, "stations": []})

    for _, row in df.iterrows():
        city = str(row.get("city", "")) if pd.notna(row.get("city")) else "不明"
        city_data[city]["count"] += 1
        city_data[city]["stations"].append(str(row.get("station_id", "")))

    index = {
        "prefecture": "神奈川県",
        "total_count": len(df),
        "city_count": len(city_data),
        "cities": dict(sorted(city_data.items(), key=lambda x: -x[1]["count"])),
    }

    path = os.path.join(EXPORTS_DIR, "city_index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[export] 市区町村インデックス: {path} ({len(city_data)}市区町村)")
    return path


def export_summary(df: pd.DataFrame, review_count: int):
    """ソースサマリレポート（Markdown）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(df)

    # 充填率計算
    fill_rates = {}
    for col in MASTER_COLUMNS + FEATURE_COLUMNS:
        if col in df.columns:
            non_null = df[col].notna().sum()
            nonnone = df[col].apply(lambda x: x not in [None, "None", "nan", ""]).sum()
            fill_rates[col] = round(nonnone / total * 100, 1) if total > 0 else 0

    # 市区町村別件数
    city_counts = df["city"].value_counts().head(15) if "city" in df.columns else pd.Series()

    content = f"""# 神奈川県 訪問看護ステーション データサマリ

生成日時: {now}

## データソース

| ソース | 説明 | ライセンス |
|--------|------|----------|
| 厚生労働省 オープンデータ | jigyosho_130.csv (訪問看護) | CC BY 4.0 |
| 関東信越厚生局 | 指定一覧・届出受理状況 | 政府標準利用規約 |

## 件数

| 項目 | 件数 |
|------|------|
| 総掲載件数 | {total:,} |
| 要確認レコード | {review_count:,} |

## 主要項目の充填率

| 項目 | 充填率 |
|------|--------|
"""
    for col, rate in sorted(fill_rates.items(), key=lambda x: -x[1]):
        if rate > 0:
            content += f"| {col} | {rate}% |\n"

    content += f"""
## 市区町村別件数（上位15）

| 市区町村 | 件数 |
|----------|------|
"""
    for city, count in city_counts.items():
        content += f"| {city} | {count} |\n"

    content += f"""
## 制約・注意事項

- 厚労省CSVは年2回更新（6月末・12月末時点）
- 厚生局データの取得状況により、feature情報の充填率は変動
- 郵便番号はCSVに含まれないため未充填
- 廃業・休止ステーションの除外は不完全の可能性あり

## 次フェーズ

- 全国展開（47都道府県）
- 厚生局feature情報の全都県展開
- Google Places連携（営業時間・口コミ）
- 地図ページ生成
- 市区町村別ページ生成
"""

    path = os.path.join(EXPORTS_DIR, "kanagawa_source_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[export] サマリ: {path}")
    return path


def process():
    """エクスポート処理"""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    print("[export] === エクスポート開始 ===")

    df = load_merged()
    print(f"[export] 入力: {len(df):,}件")

    # 要確認候補の件数を読み取る
    review_path = os.path.join(EXPORTS_DIR, "kanagawa_review_candidates.csv")
    review_count = 0
    if os.path.exists(review_path):
        try:
            review_df = pd.read_csv(review_path, encoding="utf-8-sig")
            review_count = len(review_df)
        except Exception:
            review_count = 0

    export_master_csv(df)
    export_master_json(df)
    export_site_json(df)
    export_city_index(df)
    export_summary(df, review_count)

    print(f"\n[export] === 完了 ===")
    print(f"[export] 出力先: {EXPORTS_DIR}")


def main():
    process()


if __name__ == "__main__":
    main()
