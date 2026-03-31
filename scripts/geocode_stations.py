"""
ジオコーディング（緯度経度補完）

現状: 厚労省CSVに緯度経度が100%含まれているため、MVPでは不要。
将来: 厚生局のみに存在する事業所の緯度経度補完用として設計。

使用する場合はGOOGLE_GEOCODING_API_KEY等の環境変数が必要。
"""

import os
import sys


def main():
    print("[geocode] ジオコーディングスタブ")
    print("[geocode] 現在、厚労省CSVに緯度経度が100%含まれているため、")
    print("[geocode] このステップはスキップされます。")
    print("[geocode] 厚生局データのみに存在する事業所が発見された場合に使用します。")


if __name__ == "__main__":
    main()
