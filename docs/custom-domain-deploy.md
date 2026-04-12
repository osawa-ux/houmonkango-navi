# カスタムドメイン公開手順

`kango.zaitaku-navi.com` を GitHub Pages + Cloudflare で公開するための手順。

## 必要なトークン

| トークン | 取得場所 | 必要な権限 |
|---------|---------|-----------|
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → Fine-grained PAT | Pages: write + Administration: write |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens | Zone.DNS Edit |
| `CLOUDFLARE_ZONE_ID` | Cloudflare → **zaitaku-navi.com** → Overview → API セクション | — |

> **重要**: `zaitakuclinic-navi.com`（訪問診療本体）と `zaitaku-navi.com`（新親ドメイン）は**別ゾーン**です。
> 訪問看護ナビでは必ず `zaitaku-navi.com` の Zone ID を使ってください。

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
- GitHub Pages の cname が `kango.zaitaku-navi.com` に設定される

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

## 前提: gh-pages ブランチへのデプロイ（worktree 方式・推奨）

`apply` の前に、`site_kango/` の中身を `gh-pages` ブランチに push しておく必要がある。

**worktree 方式を推奨**。master の作業ツリーに一切触れず、別ディレクトリで gh-pages を操作できるため安全。`git checkout --orphan` 方式は master のファイルを一旦削除する必要があり、中断時のリスクが高いので避ける。

### 初回デプロイ

```bash
cd ~/projects/houmonkango-navi
git fetch origin

# gh-pages を orphan ブランチとして worktree で作成
git worktree add --orphan -B gh-pages /tmp/houmonkango-gh-pages

# site_kango の中身を worktree にコピー（.nojekyll / CNAME 含む）
cd ~/projects/MyPython/site_kango
cp -a . /tmp/houmonkango-gh-pages/

# コミット＆push
cd /tmp/houmonkango-gh-pages
git add -A
git commit -m "Initial deploy: kango.zaitaku-navi.com (17,958 stations)"
git push -u origin gh-pages
```

### 2回目以降の再デプロイ

worktree を残しておけば、差分反映だけで済む。

```bash
# MyPython 側で再ビルド
cd ~/projects/MyPython
python build_site.py --config site_config_houmon_kango.json

# worktree に差分コピー（古いファイル削除のため --delete 相当が欲しい）
cd /tmp/houmonkango-gh-pages
# 一度全削除してから再コピー（.git はそのまま）
find . -mindepth 1 -not -path './.git*' -delete
cp -a ~/projects/MyPython/site_kango/. .

git add -A
git commit -m "Update site (YYYY-MM-DD)"
git push origin gh-pages
```

### 注意点

- worktree 先は `/tmp` など repo 外。repo 内には置かない
- `.git` ディレクトリはコピーしない（`cp -a .` で site_kango 配下のみ）
- `.nojekyll` と `CNAME` は build_site.py が自動生成するため、site_kango に既に含まれている
- master ブランチには一切影響しない（確認: `git status` on master）

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
