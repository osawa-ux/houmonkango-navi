"""
関東信越厚生局 訪問看護ステーション関連データの取得

対象:
- 指定訪問看護ステーションの指定一覧
- 訪問看護ステーションの基準の届出受理状況

取得戦略:
1. 厚生局のページからExcel/ZIP/PDFリンクを探索
2. ダウンロード可能なファイルを保存
3. ファイル形式に応じてparse_kouseikyoku.pyで処理
"""

import requests
import hashlib
import json
import os
import sys
import re
import zipfile
import io
from datetime import datetime
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data_sources", "kouseikyoku")
AUDIT_DIR = os.path.join(BASE_DIR, "data_sources", "processed")

SOURCE_NAME = "kouseikyoku_kanto"
BASE_URL = "https://kouseikyoku.mhlw.go.jp/kantoshinetsu/"

# 探索するページ一覧（優先度順）
SEARCH_PAGES = [
    "https://kouseikyoku.mhlw.go.jp/kantoshinetsu/chousa/houmon.html",
    "https://kouseikyoku.mhlw.go.jp/kantoshinetsu/shinsei/shitei/houmonkango.html",
    "https://kouseikyoku.mhlw.go.jp/kantoshinetsu/gyomu/gyomu/hoken_kikan/index.html",
    "https://kouseikyoku.mhlw.go.jp/kantoshinetsu/gyomu/gyomu/hoken_kikan/shitei_jokyo.html",
]

# 訪問看護関連キーワード
KEYWORDS = ["訪問看護", "houmon", "指定一覧", "届出受理", "ステーション"]
FILE_EXTENSIONS = [".xlsx", ".xls", ".zip", ".pdf", ".csv"]

HEADERS = {
    "User-Agent": "HoumonkangoNavi-DataCollector/1.0 (MDX Inc.; contact: osawa@yokohama-home.jp)"
}


def sha256_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def find_download_links(page_url: str) -> list:
    """ページからダウンロード可能なリンクを抽出"""
    print(f"[fetch_kousei] ページ探索中: {page_url}")
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"[fetch_kousei]   HTTP {r.status_code} → スキップ")
            return []
    except Exception as e:
        print(f"[fetch_kousei]   接続エラー: {e}")
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        full_text = text + " " + href

        # 訪問看護関連のリンクかチェック
        is_relevant = any(kw in full_text for kw in KEYWORDS)
        is_file = any(href.lower().endswith(ext) for ext in FILE_EXTENSIONS)

        if is_relevant or is_file:
            # 相対URLを絶対URLに変換
            if href.startswith("/"):
                abs_url = "https://kouseikyoku.mhlw.go.jp" + href
            elif not href.startswith("http"):
                abs_url = page_url.rsplit("/", 1)[0] + "/" + href
            else:
                abs_url = href

            links.append({
                "url": abs_url,
                "text": text,
                "is_file": is_file,
                "extension": os.path.splitext(href)[1].lower() if is_file else None,
            })

    # 関連リンク（サブページ）も探索
    sub_pages = []
    for link in links:
        if not link["is_file"] and any(kw in link["text"] for kw in KEYWORDS):
            sub_pages.append(link["url"])

    # サブページ内のファイルリンクも取得
    for sub_url in sub_pages[:5]:  # 最大5ページまで
        if sub_url != page_url:
            sub_links = find_download_links_shallow(sub_url)
            links.extend(sub_links)

    # ファイルリンクのみ返す
    file_links = [l for l in links if l["is_file"]]
    print(f"[fetch_kousei]   ファイルリンク {len(file_links)}件発見")
    return file_links


def find_download_links_shallow(page_url: str) -> list:
    """サブページからファイルリンクのみ抽出（再帰しない）"""
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return []
    except Exception:
        return []

    soup = BeautifulSoup(r.content, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        is_file = any(href.lower().endswith(ext) for ext in FILE_EXTENSIONS)
        if is_file:
            if href.startswith("/"):
                abs_url = "https://kouseikyoku.mhlw.go.jp" + href
            elif not href.startswith("http"):
                abs_url = page_url.rsplit("/", 1)[0] + "/" + href
            else:
                abs_url = href
            links.append({
                "url": abs_url, "text": text, "is_file": True,
                "extension": os.path.splitext(href)[1].lower(),
            })
    return links


def download_file(url: str, output_dir: str) -> dict:
    """ファイルをダウンロードして保存"""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        print(f"[fetch_kousei] DL中: {url}")
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
    except Exception as e:
        return {
            "run_id": run_id, "source_name": SOURCE_NAME,
            "target_url": url, "fetched_at": datetime.now().isoformat(),
            "status": "error", "row_count": None,
            "error_message": str(e), "file_hash": None, "file_path": None,
        }

    content = r.content
    file_hash = sha256_hash(content)

    # ファイル名を決定
    filename = url.split("/")[-1].split("?")[0]
    if not filename:
        filename = f"download_{run_id}"
    output_path = os.path.join(output_dir, f"raw_{filename}")

    # ZIPファイルの場合は展開
    if filename.lower().endswith(".zip"):
        zip_path = os.path.join(output_dir, f"raw_{filename}")
        with open(zip_path, "wb") as f:
            f.write(content)
        print(f"[fetch_kousei]   ZIP保存: {zip_path}")

        # ZIP内のファイルも展開
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    extract_path = os.path.join(output_dir, f"raw_{name}")
                    with zf.open(name) as src, open(extract_path, "wb") as dst:
                        dst.write(src.read())
                    print(f"[fetch_kousei]   展開: {extract_path}")
        except Exception as e:
            print(f"[fetch_kousei]   ZIP展開エラー: {e}")
    else:
        with open(output_path, "wb") as f:
            f.write(content)

    size_kb = len(content) / 1024
    print(f"[fetch_kousei]   保存完了: {output_path} ({size_kb:.0f}KB)")

    return {
        "run_id": run_id, "source_name": SOURCE_NAME,
        "target_url": url, "fetched_at": datetime.now().isoformat(),
        "status": "success", "row_count": None,
        "error_message": None, "file_hash": file_hash, "file_path": output_path,
    }


def save_audit(audit: dict):
    """監査ログ追記"""
    audit_path = os.path.join(AUDIT_DIR, "scrape_audit.jsonl")
    os.makedirs(AUDIT_DIR, exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")


def fetch() -> list:
    """厚生局データを探索・取得"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    audits = []

    # 各ページからファイルリンクを収集
    all_links = []
    for page_url in SEARCH_PAGES:
        links = find_download_links(page_url)
        all_links.extend(links)

    # URLの重複除去
    seen_urls = set()
    unique_links = []
    for link in all_links:
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            unique_links.append(link)

    print(f"\n[fetch_kousei] ユニークファイル数: {len(unique_links)}件")
    for link in unique_links:
        print(f"  [{link['extension']}] {link['text'][:50]} → {link['url']}")

    # 訪問看護関連ファイルのみダウンロード
    houmon_links = [
        l for l in unique_links
        if any(kw in l["text"] + l["url"] for kw in ["訪問看護", "houmon", "houmonkango"])
    ]

    if not houmon_links:
        # 関連ファイルが見つからない場合、全ファイルをDL対象にする
        print("[fetch_kousei] 訪問看護キーワードなし。全ファイルを対象にします")
        houmon_links = unique_links

    print(f"\n[fetch_kousei] ダウンロード対象: {len(houmon_links)}件")
    for link in houmon_links:
        audit = download_file(link["url"], OUTPUT_DIR)
        save_audit(audit)
        audits.append(audit)

    return audits


def main():
    audits = fetch()

    success = sum(1 for a in audits if a["status"] == "success")
    errors = sum(1 for a in audits if a["status"] == "error")
    print(f"\n[fetch_kousei] 完了: {success}件成功, {errors}件エラー")

    # ダウンロードしたファイル一覧
    print("\n[fetch_kousei] 取得ファイル一覧:")
    for a in audits:
        status = "OK" if a["status"] == "success" else "NG"
        path = a.get("file_path", "N/A")
        print(f"  [{status}] {os.path.basename(path or 'N/A')}")

    if errors > 0:
        print(f"\n[fetch_kousei] 警告: {errors}件のエラーがあります")


if __name__ == "__main__":
    main()
