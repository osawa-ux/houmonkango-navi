"""
厚労省CSVデータの正規化

入力: data_sources/mhlw/raw_jigyosho_130.csv
出力: data_sources/processed/mhlw_normalized_{pref_romaji}.csv

CLI:
  python normalize_stations.py                  # default: 神奈川県
  python normalize_stations.py --pref 福井県
"""

import argparse
import sys
import pandas as pd
import unicodedata
import re
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, "data_sources", "mhlw", "raw_jigyosho_130.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "data_sources", "processed")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pref_meta import get_pref_meta

TARGET_PREFECTURE = "神奈川県"

# 都道府県リスト（住所から分割するため）
PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

# 市区町村パターン（政令指定都市対応）
CITY_PATTERN = re.compile(
    r"^(.+?市.+?区|.+?[市区町村])"
)


def zen_to_han(text: str) -> str:
    """全角英数を半角に変換"""
    if not isinstance(text, str):
        return text
    return unicodedata.normalize("NFKC", text)


def normalize_tel(tel: str) -> str:
    """電話番号を標準形式に統一"""
    if not isinstance(tel, str) or not tel.strip():
        return None
    # 全角→半角
    tel = zen_to_han(tel).strip()
    # 数字とハイフンのみ残す
    tel = re.sub(r"[^\d\-]", "", tel)
    # ハイフンなしの場合、パターンに応じてハイフン挿入
    if "-" not in tel and len(tel) >= 10:
        if tel.startswith("0120"):
            tel = f"{tel[:4]}-{tel[4:7]}-{tel[7:]}"
        elif tel.startswith("03") or tel.startswith("06"):
            tel = f"{tel[:2]}-{tel[2:6]}-{tel[6:]}"
        elif tel.startswith("0"):
            # 一般的な市外局番（3桁-4桁-4桁 or 4桁-2桁-4桁等）
            tel = f"{tel[:3]}-{tel[3:7]}-{tel[7:]}"
    return tel if tel else None


def normalize_postal(postal: str) -> str:
    """郵便番号をNNN-NNNN形式に統一"""
    if not isinstance(postal, str) or not postal.strip():
        return None
    postal = zen_to_han(postal).strip()
    digits = re.sub(r"[^\d]", "", postal)
    if len(digits) == 7:
        return f"{digits[:3]}-{digits[3:]}"
    return None


def split_address(address: str) -> dict:
    """住所を都道府県・市区町村・それ以降に分割"""
    if not isinstance(address, str):
        return {"prefecture": None, "city": None, "street": None}

    address = zen_to_han(address).strip()
    prefecture = None
    city = None
    street = address

    # 都道府県を抽出
    for pref in PREFECTURES:
        if address.startswith(pref):
            prefecture = pref
            rest = address[len(pref):]
            break
    else:
        rest = address

    # 市区町村を抽出
    if rest:
        m = CITY_PATTERN.match(rest)
        if m:
            city = m.group(1)
            street = rest[len(city):]
        else:
            street = rest

    return {"prefecture": prefecture, "city": city, "street": street}


def normalize_name(name: str) -> str:
    """事業所名の正規化（比較用）"""
    if not isinstance(name, str):
        return ""
    name = zen_to_han(name).strip()
    # スペース除去
    name = re.sub(r"\s+", "", name)
    return name


def normalize_corp_name(name: str) -> str:
    """法人名の正規化"""
    if not isinstance(name, str):
        return name
    name = zen_to_han(name).strip()
    # 略称を正式名称に統一
    replacements = {
        "(株)": "株式会社", "㈱": "株式会社", "（株）": "株式会社",
        "(有)": "有限会社", "㈲": "有限会社", "（有）": "有限会社",
        "(医)": "医療法人", "（医）": "医療法人",
        "(社)": "社会福祉法人", "（社）": "社会福祉法人",
        "(一社)": "一般社団法人", "（一社）": "一般社団法人",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    # 余分なスペース除去
    name = re.sub(r"\s+", " ", name).strip()
    return name


def process(target_pref: str = TARGET_PREFECTURE) -> dict:
    """厚労省CSVを読み込み、正規化して出力"""
    print(f"[normalize] 入力: {INPUT_PATH}")
    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig", low_memory=False)
    cols = list(df.columns)
    total = len(df)
    print(f"[normalize] 全国件数: {total:,}件")

    # 神奈川県フィルタ
    pref_col = cols[2]  # 都道府県名
    df_pref = df[df[pref_col] == target_pref].copy()
    print(f"[normalize] {target_pref}件数: {len(df_pref):,}件")

    # カラムマッピング
    records = []
    for _, row in df_pref.iterrows():
        raw_address = str(row[cols[7]]) if pd.notna(row[cols[7]]) else ""
        building = str(row[cols[8]]) if pd.notna(row[cols[8]]) else ""
        full_address = raw_address
        if building:
            full_address = raw_address  # 方書はaddress内に含まれている場合が多い

        addr_parts = split_address(full_address)

        tel = normalize_tel(str(row[cols[11]])) if pd.notna(row[cols[11]]) else None
        fax = normalize_tel(str(row[cols[12]])) if pd.notna(row[cols[12]]) else None
        office_code = str(int(row[cols[15]])) if pd.notna(row[cols[15]]) else str(row[cols[15]])
        # office_codeが浮動小数点の場合の対処
        office_code = office_code.replace(".0", "")

        corp_name = str(row[cols[14]]) if pd.notna(row[cols[14]]) else None
        raw_corp = corp_name

        record = {
            "station_id": office_code,
            "name": zen_to_han(str(row[cols[4]])).strip() if pd.notna(row[cols[4]]) else "",
            "name_kana": zen_to_han(str(row[cols[5]])).strip() if pd.notna(row[cols[5]]) else None,
            "prefecture": addr_parts["prefecture"] or target_pref,
            "city": addr_parts["city"] or (str(row[cols[3]]) if pd.notna(row[cols[3]]) else ""),
            "address": zen_to_han(full_address),
            "postal_code": None,  # CSVに郵便番号なし
            "tel": tel,
            "fax": fax,
            "corporation_name": normalize_corp_name(corp_name) if corp_name else None,
            "office_code": office_code,
            "latitude": float(row[cols[9]]) if pd.notna(row[cols[9]]) else None,
            "longitude": float(row[cols[10]]) if pd.notna(row[cols[10]]) else None,
            "website_url": str(row[cols[19]]).strip() if pd.notna(row[cols[19]]) else None,
            "source_primary": "mhlw_opendata",
            "source_url": "https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html",
            "source_updated_at": None,
            "is_active": True,
            "raw_address": raw_address,
            "raw_name": str(row[cols[4]]) if pd.notna(row[cols[4]]) else "",
            "raw_corporation_name": raw_corp,
            # 正規化後の比較用キー
            "_normalized_name": normalize_name(str(row[cols[4]])) if pd.notna(row[cols[4]]) else "",
            "_normalized_address": normalize_name(full_address),
        }
        records.append(record)

    # DataFrame化
    result_df = pd.DataFrame(records)

    # 品質レポート
    print(f"\n[normalize] --- 品質レポート ({target_pref}) ---")
    for col in ["name", "address", "tel", "office_code", "latitude", "longitude"]:
        non_null = result_df[col].notna().sum()
        rate = non_null / len(result_df) * 100
        status = "OK" if rate >= 95 else "WARN"
        print(f"  [{status}] {col}: {rate:.1f}% ({non_null}/{len(result_df)})")

    # city の分布
    print(f"\n[normalize] 市区町村別件数 (上位10):")
    city_counts = result_df["city"].value_counts().head(10)
    for city, count in city_counts.items():
        print(f"  {city}: {count}件")

    # 保存（pref_romaji でファイル名分離）
    pref_romaji = get_pref_meta(target_pref)["romaji"]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_csv = os.path.join(OUTPUT_DIR, f"mhlw_normalized_{pref_romaji}.csv")
    result_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n[normalize] 出力: {output_csv} ({len(result_df):,}件)")

    return {
        "total_input": total,
        "prefecture_count": len(df_pref),
        "output_count": len(result_df),
        "output_path": output_csv,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pref", default=TARGET_PREFECTURE, help="対象都道府県名 (例: 福井県)")
    args = parser.parse_args()
    result = process(target_pref=args.pref)
    print(f"\n[normalize] 完了: {result['output_count']:,}件出力")


if __name__ == "__main__":
    main()
