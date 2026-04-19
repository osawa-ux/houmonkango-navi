"""都道府県メタ情報。bureau パラメータ化された scripts から共通参照される。"""

# pref_jp -> {code, romaji, bureau}
PREF_META = {
    "北海道":   {"code": "01", "romaji": "hokkaido",  "bureau": "hokkaido"},
    "青森県":   {"code": "02", "romaji": "aomori",    "bureau": "tohoku"},
    "岩手県":   {"code": "03", "romaji": "iwate",     "bureau": "tohoku"},
    "宮城県":   {"code": "04", "romaji": "miyagi",    "bureau": "tohoku"},
    "秋田県":   {"code": "05", "romaji": "akita",     "bureau": "tohoku"},
    "山形県":   {"code": "06", "romaji": "yamagata",  "bureau": "tohoku"},
    "福島県":   {"code": "07", "romaji": "fukushima", "bureau": "tohoku"},
    "茨城県":   {"code": "08", "romaji": "ibaraki",   "bureau": "kantoshinetsu"},
    "栃木県":   {"code": "09", "romaji": "tochigi",   "bureau": "kantoshinetsu"},
    "群馬県":   {"code": "10", "romaji": "gunma",     "bureau": "kantoshinetsu"},
    "埼玉県":   {"code": "11", "romaji": "saitama",   "bureau": "kantoshinetsu"},
    "千葉県":   {"code": "12", "romaji": "chiba",     "bureau": "kantoshinetsu"},
    "東京都":   {"code": "13", "romaji": "tokyo",     "bureau": "kantoshinetsu"},
    "神奈川県": {"code": "14", "romaji": "kanagawa",  "bureau": "kantoshinetsu"},
    "新潟県":   {"code": "15", "romaji": "niigata",   "bureau": "kantoshinetsu"},
    "富山県":   {"code": "16", "romaji": "toyama",    "bureau": "tokaihokuriku"},
    "石川県":   {"code": "17", "romaji": "ishikawa",  "bureau": "tokaihokuriku"},
    "福井県":   {"code": "18", "romaji": "fukui",     "bureau": "kinki"},
    "山梨県":   {"code": "19", "romaji": "yamanashi", "bureau": "kantoshinetsu"},
    "長野県":   {"code": "20", "romaji": "nagano",    "bureau": "kantoshinetsu"},
    "岐阜県":   {"code": "21", "romaji": "gifu",      "bureau": "tokaihokuriku"},
    "静岡県":   {"code": "22", "romaji": "shizuoka",  "bureau": "tokaihokuriku"},
    "愛知県":   {"code": "23", "romaji": "aichi",     "bureau": "tokaihokuriku"},
    "三重県":   {"code": "24", "romaji": "mie",       "bureau": "tokaihokuriku"},
    "滋賀県":   {"code": "25", "romaji": "shiga",     "bureau": "kinki"},
    "京都府":   {"code": "26", "romaji": "kyoto",     "bureau": "kinki"},
    "大阪府":   {"code": "27", "romaji": "osaka",     "bureau": "kinki"},
    "兵庫県":   {"code": "28", "romaji": "hyogo",     "bureau": "kinki"},
    "奈良県":   {"code": "29", "romaji": "nara",      "bureau": "kinki"},
    "和歌山県": {"code": "30", "romaji": "wakayama",  "bureau": "kinki"},
    "鳥取県":   {"code": "31", "romaji": "tottori",   "bureau": "chugokushikoku"},
    "島根県":   {"code": "32", "romaji": "shimane",   "bureau": "chugokushikoku"},
    "岡山県":   {"code": "33", "romaji": "okayama",   "bureau": "chugokushikoku"},
    "広島県":   {"code": "34", "romaji": "hiroshima", "bureau": "chugokushikoku"},
    "山口県":   {"code": "35", "romaji": "yamaguchi", "bureau": "chugokushikoku"},
    "徳島県":   {"code": "36", "romaji": "tokushima", "bureau": "shikoku"},
    "香川県":   {"code": "37", "romaji": "kagawa",    "bureau": "shikoku"},
    "愛媛県":   {"code": "38", "romaji": "ehime",     "bureau": "shikoku"},
    "高知県":   {"code": "39", "romaji": "kochi",     "bureau": "shikoku"},
    "福岡県":   {"code": "40", "romaji": "fukuoka",   "bureau": "kyushu"},
    "佐賀県":   {"code": "41", "romaji": "saga",      "bureau": "kyushu"},
    "長崎県":   {"code": "42", "romaji": "nagasaki",  "bureau": "kyushu"},
    "熊本県":   {"code": "43", "romaji": "kumamoto",  "bureau": "kyushu"},
    "大分県":   {"code": "44", "romaji": "oita",      "bureau": "kyushu"},
    "宮崎県":   {"code": "45", "romaji": "miyazaki",  "bureau": "kyushu"},
    "鹿児島県": {"code": "46", "romaji": "kagoshima", "bureau": "kyushu"},
    "沖縄県":   {"code": "47", "romaji": "okinawa",   "bureau": "kyushu"},
}


def get_pref_meta(pref_jp: str) -> dict:
    """都道府県名から meta 情報を取得。"""
    if pref_jp not in PREF_META:
        raise ValueError(f"unknown prefecture: {pref_jp}")
    return PREF_META[pref_jp]


def get_pref_meta_by_romaji(romaji: str) -> tuple:
    """romaji から (jp, meta) を逆引き。"""
    for jp, m in PREF_META.items():
        if m["romaji"] == romaji:
            return jp, m
    raise ValueError(f"unknown pref romaji: {romaji}")
