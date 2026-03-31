"""
データ収集パイプライン 一括実行

実行順序:
1. fetch_mhlw.py       - 厚労省CSVダウンロード
2. fetch_kouseikyoku.py - 厚生局データダウンロード
3. parse_kouseikyoku.py - 厚生局データパース
4. normalize_stations.py - 正規化
5. merge_stations.py    - 統合
6. export_site_data.py  - 出力

使い方:
  python scripts/run_pipeline.py          # 通常実行
  python scripts/run_pipeline.py --force  # 強制再取得
"""

import sys
import os
import time
import traceback
from datetime import datetime

# scriptsディレクトリをパスに追加
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

STEPS = [
    ("1. 厚労省CSV取得", "fetch_mhlw"),
    ("2. 厚生局データ取得", "fetch_kouseikyoku"),
    ("3. 厚生局データパース", "parse_kouseikyoku"),
    ("4. データ正規化", "normalize_stations"),
    ("5. データ統合", "merge_stations"),
    ("6. データエクスポート", "export_site_data"),
]


def run_step(step_name: str, module_name: str) -> dict:
    """個別ステップを実行"""
    print(f"\n{'='*60}")
    print(f"  {step_name}")
    print(f"{'='*60}")

    start = time.time()
    try:
        module = __import__(module_name)
        module.main()
        elapsed = time.time() - start
        print(f"\n  → {step_name} 完了 ({elapsed:.1f}秒)")
        return {"step": step_name, "status": "success", "elapsed": elapsed, "error": None}
    except Exception as e:
        elapsed = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        print(f"\n  → {step_name} エラー: {error_msg}")
        traceback.print_exc()
        return {"step": step_name, "status": "error", "elapsed": elapsed, "error": error_msg}


def main():
    start_time = datetime.now()
    print(f"{'#'*60}")
    print(f"  訪問看護ステーションナビ データ収集パイプライン")
    print(f"  開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    results = []
    for step_name, module_name in STEPS:
        result = run_step(step_name, module_name)
        results.append(result)

        # エラーが出ても継続（fetch系以外）
        if result["status"] == "error" and "fetch" in module_name:
            print(f"\n[pipeline] 警告: {step_name} でエラーが発生しましたが、パイプラインを継続します")

    # 最終レポート
    end_time = datetime.now()
    total_elapsed = (end_time - start_time).total_seconds()

    print(f"\n{'#'*60}")
    print(f"  パイプライン完了レポート")
    print(f"{'#'*60}")
    print(f"  開始: {start_time.strftime('%H:%M:%S')}")
    print(f"  終了: {end_time.strftime('%H:%M:%S')}")
    print(f"  所要: {total_elapsed:.1f}秒")
    print()

    success = 0
    errors = 0
    for r in results:
        status = "OK" if r["status"] == "success" else "NG"
        if r["status"] == "success":
            success += 1
        else:
            errors += 1
        print(f"  [{status}] {r['step']} ({r['elapsed']:.1f}s)")
        if r["error"]:
            print(f"       → {r['error']}")

    print(f"\n  結果: {success}/{len(results)} 成功, {errors} エラー")

    if errors > 0:
        print("\n  [警告] エラーのあるステップを確認してください")
        sys.exit(1)
    else:
        print("\n  全ステップ正常完了")


if __name__ == "__main__":
    main()
