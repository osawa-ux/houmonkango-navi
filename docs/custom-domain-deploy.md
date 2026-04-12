# カスタムドメイン公開手順

`kango.zaitakuclinic-navi.com` を GitHub Pages + Cloudflare で公開するための手順。

## 必要なトークン

| トークン | 取得場所 | 必要な権限 |
|---------|---------|-----------|
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → PAT (classic) | `repo` scope |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens | Zone.DNS Edit |
| `CLOUDFLARE_ZONE_ID` | Cloudflare → zaitakuclinic-navi.com → Overview → API セクション | — |

## セットアップ

```bash
cd ~/projects/houmonkango-navi
cp .env.example .env
# .env を編集してトークンを設定
```

## 実行手順

### 1. 現状確認

```bash
python scripts/setup_custom_domain.py plan
```

### 2. dry-run で変更内容をプレビュー

```bash
python scripts/setup_custom_domain.py apply --dry-run
```

### 3. 適用

```bash
python scripts/setup_custom_domain.py apply
```

これにより:
- Cloudflare に `kango` CNAME → `osawa-ux.github.io` (DNS only) が作成/更新される
- GitHub Pages の cname が `kango.zaitakuclinic-navi.com` に設定される

### 4. 確認

```bash
python scripts/setup_custom_domain.py verify
```

DNS 反映・GitHub Pages health check・証明書状態を確認する。

### 5. HTTPS 有効化

証明書が `authorized` または `issued` になったら:

```bash
python scripts/setup_custom_domain.py enable-https
```

**注意**: 証明書の発行には DNS 反映後 5〜30分かかることがある。
`verify` で `certificate.state` が `authorized` になるまで待つ。

## 前提: gh-pages ブランチへのデプロイ

`apply` の前に、`site_kango/` の中身を `gh-pages` ブランチに push しておく必要がある。

```bash
# MyPython リポジトリで site_kango/ をビルド済みの状態で:
cd ~/projects/houmonkango-navi
git checkout --orphan gh-pages
git rm -rf .
cp -r ~/projects/MyPython/site_kango/* .
git add -A
git commit -m "Deploy site"
git push origin gh-pages
git checkout master
```

または ghpages 用のデプロイスクリプトを別途作成してもよい。

## トラブルシュート

| 問題 | 対処 |
|------|------|
| `apply` で "gh-pages ブランチが存在しません" | 先に gh-pages ブランチにデプロイする |
| `verify` で health check 202 | DNS 反映待ち。5分後に再実行 |
| `enable-https` で "証明書が準備できていません" | DNS 反映 + 証明書発行待ち。30分後に再実行 |
| Cloudflare で競合 A/AAAA レコード | 手動で削除してから `apply` を再実行 |
| GitHub Pages 409 エラー | Pages が既に別の設定で存在。`verify` で確認後、手動で修正 |

## 冪等性

- `apply` は何度実行しても安全。既に正しい設定なら何も変更しない
- `enable-https` も同様。既に有効なら何もしない
- `plan` / `verify` は読み取りのみ

## 既存設定を壊さないための注意

- `apply` は既存の Pages source (branch/path) を保持する
- Cloudflare で同名の A/AAAA レコードがある場合は自動で停止する（手動確認を要求）
- 在宅クリニックナビ（zaitakuclinic-navi.com 本体）には一切影響しない
