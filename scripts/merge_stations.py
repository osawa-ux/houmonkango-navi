"""
データ統合: MHLW母集団 + 厚生局feature情報

入力:
- data_sources/processed/mhlw_normalized.csv (母集団)
- data_sources/processed/kouseikyoku_features.csv (feature)

出力:
- data_sources/processed/stations_merged.csv (統合済み)
- data_sources/exports/kanagawa_review_candidates.csv (要確認レコード)

突合ルール:
1. office_code / station_id 完全一致
2. normalized_name + normalized_address 一致
3. name + tel 一致
4. fuzzy候補 → review_candidates（自動統合しない）
"""

import pandas as pd
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "data_sources", "processed")
EXPORTS_DIR = os.path.join(BASE_DIR, "data_sources", "exports")


def load_master() -> pd.DataFrame:
    """正規化済みMHLWデータを読み込み"""
    path = os.path.join(PROCESSED_DIR, "mhlw_normalized.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"母集団データなし: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    # 数値カラムの型変換
    for col in ["latitude", "longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_active"] = df["is_active"].map({"True": True, "False": False, "true": True, "false": False}).fillna(True)
    return df


def load_features() -> pd.DataFrame:
    """厚生局featureデータを読み込み"""
    path = os.path.join(PROCESSED_DIR, "kouseikyoku_features.csv")
    if not os.path.exists(path):
        print("[merge] 厚生局featureデータなし。母集団のみで出力します。")
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    return df


def merge_by_office_code(master: pd.DataFrame, features: pd.DataFrame) -> tuple:
    """office_codeで突合（末尾6桁マッチ + 名称フォールバック）"""
    if features.empty:
        return master, 0

    feature_cols = [
        "supports_24h", "psychiatric_visit_nursing",
        "special_management_addition", "specialized_training_nurse",
        "function_strengthening_type", "medical_dx_addition",
        "base_up_eval", "remarks_raw",
    ]
    available_feat_cols = [c for c in feature_cols if c in features.columns]

    # Step 1: 末尾6桁マッチ（MHLW=10桁、厚生局=7桁）
    master["_last6"] = master["station_id"].astype(str).str[-6:]
    features["_last6"] = features["station_id"].astype(str).str[-6:]

    feat_slim = features[["_last6"] + available_feat_cols].copy()
    # 厚生局の郵便番号・名称も取り込む（補完用）
    for extra in ["postal_code", "name"]:
        if extra in features.columns:
            feat_slim[f"kousei_{extra}"] = features[extra]

    merged = master.merge(feat_slim, on="_last6", how="left", suffixes=("", "_feat"))

    # マッチ数カウント
    matched_code = merged[available_feat_cols].notna().any(axis=1).sum() if available_feat_cols else 0
    print(f"[merge] Step1 末尾6桁マッチ: {matched_code}件")

    # Step 2: 未マッチ分を名称で突合
    unmatched = merged[merged[available_feat_cols[0]].isna()] if available_feat_cols else pd.DataFrame()
    if len(unmatched) > 0 and "name" in features.columns:
        feat_dedup = features.drop_duplicates(subset=["name"], keep="first")
        feat_by_name = feat_dedup.set_index("name")[available_feat_cols].to_dict("index")
        name_matched = 0
        for idx, row in unmatched.iterrows():
            name = str(row.get("name", "")).strip()
            if name in feat_by_name:
                for col in available_feat_cols:
                    merged.at[idx, col] = feat_by_name[name].get(col)
                name_matched += 1
        print(f"[merge] Step2 名称マッチ: {name_matched}件")
        matched_code += name_matched

    # 郵便番号の補完（MHLWに無く厚生局にある場合）
    if "kousei_postal_code" in merged.columns:
        mask = merged["postal_code"].isna() & merged["kousei_postal_code"].notna()
        merged.loc[mask, "postal_code"] = merged.loc[mask, "kousei_postal_code"]
        postal_filled = mask.sum()
        if postal_filled > 0:
            print(f"[merge] 郵便番号補完: {postal_filled}件")

    # 一時カラム削除
    drop_cols = [c for c in merged.columns if c.startswith("_") or c.startswith("kousei_")]
    merged = merged.drop(columns=drop_cols, errors="ignore")

    return merged, int(matched_code)


def find_review_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """要確認レコードを抽出"""
    candidates = []

    for _, row in df.iterrows():
        reasons = []

        # 必須項目の欠損
        if not row.get("name") or str(row.get("name")).strip() == "":
            reasons.append("名称なし")
        if not row.get("address") or str(row.get("address")).strip() == "":
            reasons.append("住所なし")
        if not row.get("tel") or str(row.get("tel")).strip() == "" or row.get("tel") == "None":
            reasons.append("電話番号なし")
        if not row.get("city") or str(row.get("city")).strip() == "":
            reasons.append("市区町村不明")

        if reasons:
            candidates.append({
                "station_id": row.get("station_id"),
                "name": row.get("name"),
                "address": row.get("address"),
                "tel": row.get("tel"),
                "reasons": "; ".join(reasons),
                "review_type": "missing_data",
            })

    return pd.DataFrame(candidates)


def find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """重複候補を検出"""
    candidates = []

    # office_code重複
    dup_codes = df[df["office_code"].duplicated(keep=False)]
    if len(dup_codes) > 0:
        for code, group in dup_codes.groupby("office_code"):
            for _, row in group.iterrows():
                candidates.append({
                    "station_id": row["station_id"],
                    "name": row.get("name"),
                    "address": row.get("address"),
                    "tel": row.get("tel"),
                    "reasons": f"office_code重複: {code}",
                    "review_type": "duplicate",
                })

    # 名前+電話番号の重複（office_codeが異なる場合）
    if "tel" in df.columns and "_normalized_name" in df.columns:
        df_check = df[df["tel"].notna() & (df["tel"] != "None")].copy()
        df_check["_name_tel"] = df_check["_normalized_name"] + "_" + df_check["tel"].astype(str)
        dup_nt = df_check[df_check["_name_tel"].duplicated(keep=False)]
        for _, row in dup_nt.iterrows():
            if row["station_id"] not in [c["station_id"] for c in candidates]:
                candidates.append({
                    "station_id": row["station_id"],
                    "name": row.get("name"),
                    "address": row.get("address"),
                    "tel": row.get("tel"),
                    "reasons": "名称+電話番号重複",
                    "review_type": "duplicate",
                })

    return pd.DataFrame(candidates)


def process() -> dict:
    """統合処理のメインフロー"""
    print("[merge] === データ統合開始 ===")

    # 読み込み
    master = load_master()
    features = load_features()
    print(f"[merge] 母集団: {len(master):,}件")
    print(f"[merge] feature: {len(features):,}件")

    # 突合
    merged, match_count = merge_by_office_code(master, features)
    print(f"[merge] office_code突合: {match_count}件マッチ")

    match_rate = match_count / len(merged) * 100 if len(merged) > 0 else 0
    print(f"[merge] マッチ率: {match_rate:.1f}%")

    # 要確認レコード
    review_missing = find_review_candidates(merged)
    review_dup = find_duplicates(merged)
    review_all = pd.concat([review_missing, review_dup], ignore_index=True)

    # 出力
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    # 統合データ
    merged_path = os.path.join(PROCESSED_DIR, "stations_merged.csv")
    merged.to_csv(merged_path, index=False, encoding="utf-8-sig")
    print(f"[merge] 統合データ出力: {merged_path} ({len(merged):,}件)")

    # 要確認候補
    review_path = os.path.join(EXPORTS_DIR, "kanagawa_review_candidates.csv")
    review_all.to_csv(review_path, index=False, encoding="utf-8-sig")
    print(f"[merge] 要確認候補: {review_path} ({len(review_all):,}件)")

    # サマリ
    summary = {
        "merged_at": datetime.now().isoformat(),
        "master_count": len(master),
        "feature_count": len(features),
        "merged_count": len(merged),
        "match_count": match_count,
        "match_rate_pct": round(match_rate, 1),
        "review_missing": len(review_missing),
        "review_duplicate": len(review_dup),
    }
    print(f"\n[merge] --- サマリ ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    return summary


def main():
    result = process()
    print(f"\n[merge] 完了: {result['merged_count']:,}件統合")


if __name__ == "__main__":
    main()
