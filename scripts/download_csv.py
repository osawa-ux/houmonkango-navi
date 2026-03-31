"""
厚生労働省 介護サービス情報公表システム オープンデータCSVのダウンロードと基本分析

データソース: https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html
ライセンス: CC BY（出典明記で商用利用可）
対象: jigyosho_130.csv（訪問看護ステーション）
"""

import requests
import pandas as pd
import os
import sys
import json
from datetime import datetime

# === 設定 ===
CSV_URL = "https://www.mhlw.go.jp/content/12300000/jigyosho_130.csv"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "raw")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "jigyosho_130.csv")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "reports")


def download_csv():
    """CSVをダウンロードして保存"""
    print(f"ダウンロード中: {CSV_URL}")
    r = requests.get(CSV_URL, timeout=120)
    r.raise_for_status()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        f.write(r.content)

    size_mb = len(r.content) / 1024 / 1024
    print(f"保存完了: {OUTPUT_PATH} ({size_mb:.1f} MB)")
    return OUTPUT_PATH


def analyze_csv(filepath):
    """CSVの基本分析を実行"""
    df = pd.read_csv(filepath, encoding="utf-8-sig", low_memory=False)
    cols = list(df.columns)

    print("\n" + "=" * 60)
    print("  訪問看護ステーション オープンデータCSV 分析レポート")
    print("=" * 60)
    print(f"ファイル: {os.path.basename(filepath)}")
    print(f"文字コード: UTF-8 (BOM付き)")
    print(f"総件数: {len(df):,}件")
    print(f"カラム数: {len(cols)}")
    print(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # カラム別充填率
    print("\n--- カラム別充填率 ---")
    fill_rates = {}
    for i, col in enumerate(cols):
        non_null = df[col].notna().sum()
        rate = non_null / len(df) * 100
        fill_rates[col] = rate
        mark = "OK" if rate >= 95 else "LOW" if rate >= 50 else "WARN"
        print(f"  [{mark:4s}] {col}: {rate:.1f}% ({non_null:,}/{len(df):,})")

    # 都道府県別件数
    print("\n--- 都道府県別件数 ---")
    pref_col = cols[2]  # 都道府県名
    pref_counts = df[pref_col].value_counts()
    pref_data = {}
    for name in sorted(pref_counts.index):
        count = int(pref_counts[name])
        pref_data[name] = count
        print(f"  {name}: {count:,}件")
    print(f"\n  合計: {pref_counts.sum():,}件")

    # 重要統計
    print("\n--- 重要統計 ---")
    # 事業所番号の重複チェック
    jigyosho_col = cols[15]  # 事業所番号
    dup_count = df[jigyosho_col].duplicated().sum()
    print(f"  事業所番号の重複: {dup_count}件")

    # 緯度経度の有無
    lat_col, lon_col = cols[9], cols[10]
    geo_count = df[[lat_col, lon_col]].notna().all(axis=1).sum()
    print(f"  緯度経度あり: {geo_count:,}件 ({geo_count/len(df)*100:.1f}%)")

    # URL保有率
    url_col = cols[19]
    url_count = df[url_col].notna().sum()
    print(f"  URL保有: {url_count:,}件 ({url_count/len(df)*100:.1f}%)")

    # 法人種別の分布
    corp_col = cols[14]  # 法人の名称
    corps = df[corp_col].dropna()
    corp_types = {
        "医療法人": corps.str.contains("医療法人", na=False).sum(),
        "株式会社": corps.str.contains("株式会社", na=False).sum(),
        "有限会社": corps.str.contains("有限会社", na=False).sum(),
        "社会福祉法人": corps.str.contains("社会福祉法人", na=False).sum(),
        "NPO法人/特定非営利": corps.str.contains("特定非営利|NPO", na=False).sum(),
        "合同会社": corps.str.contains("合同会社", na=False).sum(),
        "一般社団法人": corps.str.contains("一般社団法人", na=False).sum(),
    }
    print("\n--- 法人種別分布 ---")
    for ctype, count in sorted(corp_types.items(), key=lambda x: -x[1]):
        print(f"  {ctype}: {count:,}件 ({count/len(df)*100:.1f}%)")

    # レポートJSON保存
    report = {
        "analyzed_at": datetime.now().isoformat(),
        "file": os.path.basename(filepath),
        "total_records": int(len(df)),
        "columns": int(len(cols)),
        "column_names": cols,
        "fill_rates": {k: round(v, 1) for k, v in fill_rates.items()},
        "prefecture_counts": {k: int(v) for k, v in pref_data.items()},
        "duplicated_jigyosho_numbers": int(dup_count),
        "geo_available": int(geo_count),
        "corporation_types": {k: int(v) for k, v in corp_types.items()},
    }
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, "csv_analysis_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nレポート保存: {report_path}")

    return report


def main():
    # ダウンロード（既にあればスキップ可能）
    if not os.path.exists(OUTPUT_PATH) or "--force" in sys.argv:
        filepath = download_csv()
    else:
        filepath = OUTPUT_PATH
        print(f"既存ファイル使用: {filepath}")

    # 分析
    report = analyze_csv(filepath)

    # 最終サマリ
    print("\n" + "=" * 60)
    print("  CSV確認結果サマリ")
    print("=" * 60)
    total = report["total_records"]
    print(f"  総件数: {total:,}件 {'OK' if total >= 15000 else 'WARN'}")
    print(f"  事業所番号重複: {report['duplicated_jigyosho_numbers']}件 {'OK' if report['duplicated_jigyosho_numbers'] == 0 else 'WARN'}")
    print(f"  緯度経度: {report['geo_available']:,}件 ({report['geo_available']/total*100:.0f}%)")

    essential_ok = all(
        report["fill_rates"].get(col, 0) >= 95
        for col in ["事業所名", "住所", "電話番号", "事業所番号"]
    )
    print(f"  必須項目充填: {'OK (95%以上)' if essential_ok else 'WARN'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
