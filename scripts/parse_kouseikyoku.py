"""
関東信越厚生局データのパース

入力: data_sources/kouseikyoku/ 内の神奈川県Excelファイル
  - 14コード内容別訪問看護事業所一覧表（神奈川）r0803.xlsx  → 指定一覧
  - 14届出受理指定訪問看護事業所名簿（神奈川）r0803.xlsx    → 届出受理（feature情報）

出力: data_sources/processed/kouseikyoku_features.csv

届出受理名簿の受理番号コード体系:
  訪看10 = 24時間対応体制加算
  訪看24 = 精神科訪問看護基本療養費
  訪看25 = 特別管理加算
  訪看27 = 専門の研修を受けた看護師（緩和ケア等）
  訪看28 = 専門の研修を受けた看護師（褥瘡等）
  訪看30 = 機能強化型訪問看護管理療養費
  訪看40 = 訪問看護医療DX情報活用加算 / ベースアップ評価料
  訪看41 = 医療DX関連
  訪ベⅠ１ = ベースアップ評価料
"""

import argparse
import sys
import yaml
import pandas as pd
import unicodedata
import os
import re
import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data_sources", "kouseikyoku")
OUTPUT_DIR = os.path.join(BASE_DIR, "data_sources", "processed")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.yaml")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pref_meta import get_pref_meta

# 受理番号コード → feature フィールドのマッピング
JURI_CODE_MAP = {
    "訪看10": "supports_24h",
    "訪看24": "psychiatric_visit_nursing",
    "訪看25": "special_management_addition",
    "訪看27": "specialized_training_nurse",
    "訪看28": "specialized_training_nurse",
    "訪看30": "function_strengthening_type",
    "訪看40": "medical_dx_addition",
    "訪看41": "medical_dx_addition",
    "訪ベ": "base_up_eval",
}


def zen_to_han(text: str) -> str:
    """全角英数を半角に変換"""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    return unicodedata.normalize("NFKC", text)


def _load_bureau_patterns(bureau: str) -> dict:
    """config/sources.yaml から bureau の excel_file_patterns を取得"""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["kouseikyoku"]["bureaus"][bureau]["excel_file_patterns"]


def find_pref_excel(pref_jp: str, kind: str) -> str:
    """指定 pref / kind (todokede/shitei) の Excel を探す。
    config/sources.yaml の bureau.excel_file_patterns に従って glob する。"""
    meta = get_pref_meta(pref_jp)
    bureau = meta["bureau"]
    patterns = _load_bureau_patterns(bureau)
    pattern_tpl = patterns.get(kind)
    if not pattern_tpl:
        return None

    pref_jp_short = pref_jp.replace("県", "").replace("府", "").replace("都", "").replace("道", "")
    pattern = pattern_tpl.format(
        pref_code=meta["code"],
        pref_jp=pref_jp_short,
        pref_romaji=meta["romaji"],
    )
    files = glob.glob(os.path.join(INPUT_DIR, pattern))
    if files:
        # 届出受理は feature 情報量が多い = 大きいファイル
        return max(files, key=os.path.getsize) if kind == "todokede" else min(files, key=os.path.getsize)

    # フォールバック: pref_code prefix で全 xlsx を探し、サイズで大小を選ぶ
    fallback = glob.glob(os.path.join(INPUT_DIR, f"raw_{meta['code']}*.xlsx"))
    if fallback:
        return max(fallback, key=os.path.getsize) if kind == "todokede" else min(fallback, key=os.path.getsize)
    return None


def parse_juri_codes(juri_text: str) -> dict:
    """受理番号テキストからfeatureフラグを抽出"""
    features = {}
    if not isinstance(juri_text, str):
        return features

    text = zen_to_han(juri_text)

    for code, field in JURI_CODE_MAP.items():
        code_han = zen_to_han(code)
        if code_han in text or code in text:
            # 訪看30 含む全コード共通: 受理あり = True
            # 旧版は「訪看30 第N号」の N を type 1/2/3 と誤認していたが、
            # 実際には N は受理連番で type 情報ではない（厚生局公開データに 1/2/3 区別は無い）
            features[field] = True

    return features


def parse_station_code(code_text: str) -> str:
    """ステーションコードからoffice_code相当の文字列を生成"""
    if not isinstance(code_text, str):
        code_text = str(code_text) if code_text is not None else ""
    # 全角→半角
    code = zen_to_han(code_text).strip()
    # カンマ・ドット・スペースを除去して数字のみ
    digits = re.sub(r"[^\d]", "", code)
    return digits


def parse_todokede_excel(filepath: str) -> list:
    """届出受理名簿Excelをパース"""
    print(f"[parse_kousei] 届出受理パース: {os.path.basename(filepath)}")

    df = pd.read_excel(filepath, header=None)
    print(f"[parse_kousei]   総行数: {len(df)}")

    # データ構造:
    # col[2] = 項番
    # col[4] = ステーションコード
    # col[7] = 事業者名/事業所名（改行区切り）
    # col[10] = 事業所所在地（〒含む、改行区切り）
    # col[13] = 電話(FAX)番号
    # col[16] = 受理番号（複数行、加算情報の核心）
    # col[18] = 算定開始年月日

    records = []
    skip_count = 0

    for idx in range(7, len(df)):  # 行7からデータ開始
        row = df.iloc[idx]

        # 項番チェック（数値でなければスキップ）
        item_no = row.iloc[2] if len(row) > 2 else None
        if pd.isna(item_no):
            skip_count += 1
            continue
        try:
            int(float(item_no))
        except (ValueError, TypeError):
            skip_count += 1
            continue

        # ステーションコード
        station_code = parse_station_code(row.iloc[4] if len(row) > 4 else None)

        # 事業者名/事業所名
        name_raw = str(row.iloc[7]) if len(row) > 7 and pd.notna(row.iloc[7]) else ""
        # 改行で分割（1行目=法人名、2行目=事業所名）
        name_parts = name_raw.split("\n")
        corp_name = name_parts[0].strip() if len(name_parts) > 0 else ""
        station_name = name_parts[1].strip() if len(name_parts) > 1 else name_parts[0].strip()

        # 住所
        addr_raw = str(row.iloc[10]) if len(row) > 10 and pd.notna(row.iloc[10]) else ""
        # 〒と住所を分離
        addr_lines = addr_raw.split("\n")
        postal = ""
        address = ""
        for line in addr_lines:
            line = line.strip()
            if line.startswith("〒"):
                postal = zen_to_han(line.replace("〒", "").strip())
                postal = re.sub(r"[^\d\-]", "", postal)
                if len(postal) == 7:
                    postal = f"{postal[:3]}-{postal[3:]}"
            elif line:
                address = zen_to_han(line)

        # 電話/FAX
        tel_raw = str(row.iloc[13]) if len(row) > 13 and pd.notna(row.iloc[13]) else ""
        tel_lines = tel_raw.split("\n")
        tel = zen_to_han(tel_lines[0].strip()) if len(tel_lines) > 0 else ""
        fax = ""
        if len(tel_lines) > 1:
            fax_line = zen_to_han(tel_lines[1].strip())
            fax = re.sub(r"[()]", "", fax_line).strip()

        # 受理番号（feature情報の核心）
        juri_raw = str(row.iloc[16]) if len(row) > 16 and pd.notna(row.iloc[16]) else ""
        features = parse_juri_codes(juri_raw)

        record = {
            "station_id": station_code,
            "station_code_raw": str(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else "",
            "name": station_name,
            "corporation_name": corp_name,
            "postal_code": postal if postal else None,
            "address": address,
            "tel": tel if tel else None,
            "fax": fax if fax else None,
            "juri_raw": juri_raw,
            "supports_24h": features.get("supports_24h"),
            "psychiatric_visit_nursing": features.get("psychiatric_visit_nursing"),
            "special_management_addition": features.get("special_management_addition"),
            "specialized_training_nurse": features.get("specialized_training_nurse"),
            "function_strengthening_type": features.get("function_strengthening_type"),
            "medical_dx_addition": features.get("medical_dx_addition"),
            "base_up_eval": features.get("base_up_eval"),
            "remarks_raw": None,
            "source": "kouseikyoku_kanto",
        }
        records.append(record)

    print(f"[parse_kousei]   データ行: {len(records)}件, スキップ: {skip_count}行")
    return records


def process(target_pref: str = "神奈川県") -> dict:
    """厚生局データパースのメインフロー"""
    print(f"[parse_kousei] === 厚生局データパース開始 (pref={target_pref}) ===")

    # 届出受理名簿を優先（feature情報が豊富）
    todokede_file = find_pref_excel(target_pref, "todokede")
    shitei_file = find_pref_excel(target_pref, "shitei")

    print(f"[parse_kousei] 届出受理: {os.path.basename(todokede_file) if todokede_file else 'なし'}")
    print(f"[parse_kousei] 指定一覧: {os.path.basename(shitei_file) if shitei_file else 'なし'}")

    records = []

    if todokede_file:
        records = parse_todokede_excel(todokede_file)
    elif shitei_file:
        # 指定一覧からもパース可能だが、feature情報は少ない
        print("[parse_kousei] 届出受理なし。指定一覧をフォールバックで使用")
        records = parse_todokede_excel(shitei_file)  # 同じパーサで試行

    if not records:
        print("[parse_kousei] パース結果なし。空ファイルを出力します。")

    result_df = pd.DataFrame(records)

    # 重複除去
    if len(result_df) > 0 and "station_id" in result_df.columns:
        before = len(result_df)
        result_df = result_df.drop_duplicates(subset=["station_id"], keep="first")
        after = len(result_df)
        if before != after:
            print(f"[parse_kousei] 重複除去: {before} → {after}")

    # feature充填率レポート
    if len(result_df) > 0:
        print(f"\n[parse_kousei] --- feature充填率 ---")
        for col in ["supports_24h", "psychiatric_visit_nursing", "special_management_addition",
                     "specialized_training_nurse", "function_strengthening_type",
                     "medical_dx_addition", "base_up_eval"]:
            if col in result_df.columns:
                count = result_df[col].notna().sum()
                true_count = (result_df[col] == True).sum() if result_df[col].dtype == bool else result_df[col].notna().sum()
                print(f"  {col}: {true_count}/{len(result_df)} ({true_count/len(result_df)*100:.1f}%)")

    # 出力（pref_romaji でファイル名分離）
    pref_romaji = get_pref_meta(target_pref)["romaji"]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"kouseikyoku_features_{pref_romaji}.csv")
    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n[parse_kousei] 出力: {output_path} ({len(result_df):,}件)")

    return {
        "status": "success" if len(result_df) > 0 else "no_data",
        "output_count": len(result_df),
        "output_path": output_path,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pref", default="神奈川県", help="対象都道府県名 (例: 福井県)")
    args = parser.parse_args()
    result = process(target_pref=args.pref)
    print(f"[parse_kousei] 完了: {result['status']}, {result['output_count']}件")


if __name__ == "__main__":
    main()
