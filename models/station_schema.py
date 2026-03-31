"""
訪問看護ステーション データモデル定義

stations_master: 母集団データ（基本情報）
stations_features: 加算・届出情報（厚生局由来）
stations_web: Web補完情報（将来用）
scrape_audit: 取得監査ログ
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StationMaster(BaseModel):
    """訪問看護ステーション 基本情報"""
    station_id: str = Field(description="一意識別子（office_code ベース）")
    name: str = Field(description="事業所名")
    name_kana: Optional[str] = Field(default=None, description="事業所名カナ")
    prefecture: str = Field(description="都道府県")
    city: str = Field(description="市区町村")
    address: str = Field(description="住所（都道府県含む全文）")
    postal_code: Optional[str] = Field(default=None, description="郵便番号 NNN-NNNN")
    tel: Optional[str] = Field(default=None, description="電話番号 ハイフン付き")
    fax: Optional[str] = Field(default=None, description="FAX番号 ハイフン付き")
    corporation_name: Optional[str] = Field(default=None, description="法人名称")
    office_code: str = Field(description="事業所番号（10桁）")
    latitude: Optional[float] = Field(default=None, description="緯度")
    longitude: Optional[float] = Field(default=None, description="経度")
    website_url: Optional[str] = Field(default=None, description="公式サイトURL")
    source_primary: str = Field(description="主データソース名")
    source_url: Optional[str] = Field(default=None, description="データ取得元URL")
    source_updated_at: Optional[str] = Field(default=None, description="ソースデータ更新日")
    is_active: bool = Field(default=True, description="稼働中フラグ")
    # 生データ保持
    raw_address: Optional[str] = Field(default=None, description="正規化前の住所")
    raw_name: Optional[str] = Field(default=None, description="正規化前の事業所名")
    raw_corporation_name: Optional[str] = Field(default=None, description="正規化前の法人名")


class StationFeatures(BaseModel):
    """訪問看護ステーション 加算・届出情報"""
    station_id: str = Field(description="station_master.station_id と対応")
    supports_24h: Optional[bool] = Field(default=None, description="24時間対応体制加算")
    psychiatric_visit_nursing: Optional[bool] = Field(default=None, description="精神科訪問看護基本療養費")
    special_management_addition: Optional[bool] = Field(default=None, description="特別管理加算")
    specialized_training_nurse: Optional[bool] = Field(default=None, description="専門の研修を受けた看護師")
    function_strengthening_type: Optional[str] = Field(default=None, description="機能強化型 (1/2/3/なし)")
    medical_dx_addition: Optional[bool] = Field(default=None, description="訪問看護医療DX情報活用加算")
    base_up_eval: Optional[bool] = Field(default=None, description="ベースアップ評価料")
    remarks_raw: Optional[str] = Field(default=None, description="備考（生テキスト）")
    source: str = Field(default="kouseikyoku", description="データソース名")


class StationWeb(BaseModel):
    """Web補完情報（将来用）"""
    station_id: str
    website_url: Optional[str] = None
    google_place_id: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    photo_url: Optional[str] = None
    business_status: Optional[str] = None


class ScrapeAudit(BaseModel):
    """取得監査ログ"""
    run_id: str = Field(description="実行ID")
    source_name: str = Field(description="ソース名")
    target_url: str = Field(description="取得先URL")
    fetched_at: str = Field(description="取得日時 ISO8601")
    status: str = Field(description="success / error / skipped")
    row_count: Optional[int] = Field(default=None, description="取得行数")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    file_hash: Optional[str] = Field(default=None, description="ファイルSHA256ハッシュ")
    file_path: Optional[str] = Field(default=None, description="保存先パス")
