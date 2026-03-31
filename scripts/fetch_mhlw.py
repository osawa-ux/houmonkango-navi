"""
厚生労働省 介護サービス情報公表システム オープンデータの取得

データソース: https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html
ライセンス: CC BY 4.0
対象: jigyosho_130.csv（訪問看護ステーション）
"""

import requests
import hashlib
import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data_sources", "mhlw")
AUDIT_DIR = os.path.join(BASE_DIR, "data_sources", "processed")

CSV_URL = "https://www.mhlw.go.jp/content/12300000/jigyosho_130.csv"
SOURCE_NAME = "mhlw_opendata"


def sha256_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch(force: bool = False) -> dict:
    """厚労省CSVを取得して保存。auditレコードを返す。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(AUDIT_DIR, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, "raw_jigyosho_130.csv")

    # 既存ファイルがあり、forceでなければスキップ
    if os.path.exists(output_path) and not force:
        print(f"[fetch_mhlw] 既存ファイル使用: {output_path}")
        with open(output_path, "rb") as f:
            content = f.read()
        file_hash = sha256_hash(content)
        row_count = content.decode("utf-8-sig").count("\n") - 1
        audit = {
            "run_id": run_id,
            "source_name": SOURCE_NAME,
            "target_url": CSV_URL,
            "fetched_at": datetime.now().isoformat(),
            "status": "skipped",
            "row_count": row_count,
            "error_message": None,
            "file_hash": file_hash,
            "file_path": output_path,
        }
        return audit

    print(f"[fetch_mhlw] ダウンロード中: {CSV_URL}")
    try:
        r = requests.get(CSV_URL, timeout=120)
        r.raise_for_status()
    except Exception as e:
        audit = {
            "run_id": run_id,
            "source_name": SOURCE_NAME,
            "target_url": CSV_URL,
            "fetched_at": datetime.now().isoformat(),
            "status": "error",
            "row_count": None,
            "error_message": str(e),
            "file_hash": None,
            "file_path": None,
        }
        print(f"[fetch_mhlw] エラー: {e}")
        return audit

    content = r.content
    file_hash = sha256_hash(content)
    size_mb = len(content) / 1024 / 1024

    with open(output_path, "wb") as f:
        f.write(content)

    row_count = content.decode("utf-8-sig").count("\n") - 1
    print(f"[fetch_mhlw] 保存完了: {output_path} ({size_mb:.1f}MB, {row_count:,}行)")

    audit = {
        "run_id": run_id,
        "source_name": SOURCE_NAME,
        "target_url": CSV_URL,
        "fetched_at": datetime.now().isoformat(),
        "status": "success",
        "row_count": row_count,
        "error_message": None,
        "file_hash": file_hash,
        "file_path": output_path,
    }
    return audit


def save_audit(audit: dict):
    """監査ログをJSONLファイルに追記"""
    audit_path = os.path.join(AUDIT_DIR, "scrape_audit.jsonl")
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")
    print(f"[fetch_mhlw] audit保存: {audit_path}")


def main():
    force = "--force" in sys.argv
    audit = fetch(force=force)
    save_audit(audit)

    if audit["status"] == "error":
        print(f"[fetch_mhlw] 失敗: {audit['error_message']}")
        sys.exit(1)

    print(f"[fetch_mhlw] 完了 (status={audit['status']}, rows={audit['row_count']})")


if __name__ == "__main__":
    main()
