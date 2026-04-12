#!/usr/bin/env python3
"""
GitHub Pages + Cloudflare カスタムドメイン設定 CLI

サブコマンド:
  plan          現在の状態を表示し、何が変更されるかをプレビュー
  apply         Cloudflare DNS + GitHub Pages を実際に設定
  verify        DNS / GitHub Pages health check / 証明書状態を確認
  enable-https  GitHub Pages の HTTPS 強制を有効化

フラグ:
  --dry-run     apply 時に実際の変更を行わない

必須環境変数:
  GITHUB_TOKEN          GitHub Fine-grained PAT (Pages: write, Administration: write)
  CLOUDFLARE_API_TOKEN  Cloudflare API Token (Zone.DNS edit)
  CLOUDFLARE_ZONE_ID    Cloudflare Zone ID

オプション環境変数:
  GITHUB_OWNER   default: osawa-ux
  GITHUB_REPO    default: houmonkango-navi
  CUSTOM_DOMAIN  default: kango.zaitaku-navi.com
  CNAME_TARGET   default: osawa-ux.github.io
  CF_RECORD_NAME default: kango
"""
import json, os, sys, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# --- 設定 ---
OWNER = os.environ.get('GITHUB_OWNER', 'osawa-ux')
REPO = os.environ.get('GITHUB_REPO', 'houmonkango-navi')
DOMAIN = os.environ.get('CUSTOM_DOMAIN', 'kango.zaitaku-navi.com')
CNAME_TARGET = os.environ.get('CNAME_TARGET', 'osawa-ux.github.io')
CF_RECORD = os.environ.get('CF_RECORD_NAME', 'kango')

GH_TOKEN = os.environ.get('GITHUB_TOKEN', '')
CF_TOKEN = os.environ.get('CLOUDFLARE_API_TOKEN', '')
CF_ZONE = os.environ.get('CLOUDFLARE_ZONE_ID', '')

GH_API = f'https://api.github.com/repos/{OWNER}/{REPO}'
CF_API = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE}'

DRY_RUN = '--dry-run' in sys.argv


def _mask(s, show=4):
    if not s:
        return '(empty)'
    return s[:show] + '***' + s[-2:] if len(s) > show + 2 else '***'


def _req(url, method='GET', data=None, headers=None, token=None, token_type='Bearer'):
    """HTTP request helper with error handling."""
    hdrs = {'Accept': 'application/json', 'User-Agent': 'setup-custom-domain/1.0'}
    if token:
        hdrs['Authorization'] = f'{token_type} {token}'
    if data is not None:
        hdrs['Content-Type'] = 'application/json'
    if headers:
        hdrs.update(headers)
    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, headers=hdrs, method=method)
    try:
        with urlopen(req) as resp:
            body = resp.read().decode()
            if not body.strip():
                return resp.status, {}
            return resp.status, json.loads(body)
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ''
        try:
            err = json.loads(body_text)
        except Exception:
            err = {'raw': body_text}
        return e.code, err


def gh(path, method='GET', data=None):
    return _req(f'{GH_API}{path}', method=method, data=data, token=GH_TOKEN, token_type='token')


def cf(path, method='GET', data=None):
    return _req(f'{CF_API}{path}', method=method, data=data, token=CF_TOKEN)


# ========== Cloudflare DNS ==========

def cf_find_record():
    """CNAME / A / AAAA レコードを検索"""
    status, resp = cf(f'/dns_records?name={DOMAIN}&per_page=50')
    if status != 200:
        print(f'  ERROR: Cloudflare DNS list failed ({status})')
        print(f'  {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}')
        return None, []
    records = resp.get('result', [])
    cname = [r for r in records if r['type'] == 'CNAME']
    conflicts = [r for r in records if r['type'] in ('A', 'AAAA')]
    return (cname[0] if cname else None), conflicts


def cf_apply():
    """Cloudflare CNAME を作成 or 更新"""
    print('\n--- Cloudflare DNS ---')
    existing, conflicts = cf_find_record()

    if conflicts:
        print(f'  ⚠ 競合レコード検出 ({len(conflicts)}件):')
        for r in conflicts:
            print(f'    {r["type"]} {r["name"]} → {r["content"]} (id: {r["id"]})')
        print('  これらを手動で削除してから再実行してください。')
        print('  処理を中止します。')
        return False

    payload = {
        'type': 'CNAME',
        'name': CF_RECORD,
        'content': CNAME_TARGET,
        'ttl': 1,
        'proxied': False,
    }

    if existing:
        # 既に正しいか確認
        if (existing['content'] == CNAME_TARGET and
            existing['type'] == 'CNAME' and
            not existing.get('proxied', True)):
            print(f'  ✓ CNAME already correct: {existing["name"]} → {existing["content"]} (DNS only)')
            return True
        print(f'  変更: {existing["name"]} → {existing["content"]} (proxied={existing.get("proxied")})')
        print(f'    → {CF_RECORD} → {CNAME_TARGET} (proxied=false)')
        if DRY_RUN:
            print('  [dry-run] PATCH skipped')
            return True
        status, resp = cf(f'/dns_records/{existing["id"]}', method='PATCH', data=payload)
    else:
        print(f'  作成: {CF_RECORD} CNAME → {CNAME_TARGET} (DNS only)')
        if DRY_RUN:
            print('  [dry-run] POST skipped')
            return True
        status, resp = cf('/dns_records', method='POST', data=payload)

    if status in (200, 201):
        r = resp.get('result', {})
        print(f'  ✓ OK: {r.get("name")} → {r.get("content")} (id: {r.get("id")})')
        return True
    else:
        print(f'  ERROR ({status}): {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}')
        return False


# ========== GitHub Pages ==========

def gh_get_pages():
    """現在の Pages 設定を取得"""
    status, resp = gh('/pages')
    if status == 404:
        return None
    if status == 200:
        return resp
    print(f'  WARNING: Pages GET returned {status}')
    return resp


def gh_apply():
    """GitHub Pages にカスタムドメインを設定"""
    print('\n--- GitHub Pages ---')
    pages = gh_get_pages()

    if pages is None:
        # Pages 未作成 → 作成
        print(f'  Pages 未設定。作成します (source: gh-pages /, cname: {DOMAIN})')
        if DRY_RUN:
            print('  [dry-run] POST skipped')
            return True
        data = {
            'source': {'branch': 'gh-pages', 'path': '/'},
            'cname': DOMAIN,
            'https_enforced': False,
        }
        # gh-pages ブランチが存在するか確認
        br_status, _ = gh('/branches/gh-pages')
        if br_status == 404:
            print('  ⚠ gh-pages ブランチが存在しません。先にデプロイしてください。')
            print('  Pages 設定はデプロイ後に再実行してください。')
            return False
        status, resp = gh('/pages', method='POST', data=data)
        if status in (201, 204):
            print(f'  ✓ Pages 作成完了')
            return True
        elif status == 409:
            print(f'  Pages は既に存在します。更新を試みます。')
        else:
            print(f'  ERROR ({status}): {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}')
            return False

    # Pages 既存 → cname を更新
    current_cname = pages.get('cname', '')
    current_https = pages.get('https_enforced', False)
    source = pages.get('source', {})
    print(f'  現在: cname={current_cname}, https={current_https}, source={source}')

    if current_cname == DOMAIN:
        print(f'  ✓ cname already set to {DOMAIN}')
        return True

    print(f'  変更: cname {current_cname!r} → {DOMAIN!r}')
    if DRY_RUN:
        print('  [dry-run] PUT skipped')
        return True

    data = {'cname': DOMAIN, 'https_enforced': False}
    # source を保持
    if source:
        data['source'] = source
    status, resp = gh('/pages', method='PUT', data=data)
    if status in (200, 204):
        print(f'  ✓ cname 更新完了')
        return True
    else:
        print(f'  ERROR ({status}): {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}')
        return False


def gh_enable_https():
    """HTTPS 強制を有効化"""
    print('\n--- Enable HTTPS ---')
    pages = gh_get_pages()
    if pages is None:
        print('  ERROR: Pages が未設定です。先に apply を実行してください。')
        return False

    if pages.get('https_enforced'):
        print('  ✓ HTTPS already enforced')
        return True

    https_status = pages.get('https_certificate', {}).get('state', 'unknown')
    print(f'  証明書状態: {https_status}')

    if https_status not in ('authorized', 'issued', 'approved'):
        print(f'  ⚠ 証明書がまだ準備できていません (state={https_status})。')
        print('  しばらく待ってから再実行してください。')
        return False

    if DRY_RUN:
        print('  [dry-run] PUT skipped')
        return True

    source = pages.get('source', {})
    data = {'cname': DOMAIN, 'https_enforced': True}
    if source:
        data['source'] = source
    status, resp = gh('/pages', method='PUT', data=data)
    if status in (200, 204):
        print('  ✓ HTTPS 強制を有効化しました')
        return True
    else:
        print(f'  ERROR ({status}): {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}')
        return False


# ========== verify ==========

def verify():
    """DNS + GitHub Pages の状態を確認"""
    print('\n=== Verify ===')

    # Cloudflare DNS
    print('\n--- Cloudflare DNS ---')
    existing, conflicts = cf_find_record()
    if existing:
        print(f'  CNAME: {existing["name"]} → {existing["content"]}')
        print(f'  proxied: {existing.get("proxied")}, ttl: {existing.get("ttl")}')
    else:
        print('  ⚠ CNAME レコードが見つかりません')
    if conflicts:
        print(f'  ⚠ 競合: {[(r["type"], r["content"]) for r in conflicts]}')

    # GitHub Pages
    print('\n--- GitHub Pages ---')
    pages = gh_get_pages()
    if pages is None:
        print('  ⚠ Pages 未設定')
        return

    print(f'  cname: {pages.get("cname")}')
    print(f'  url: {pages.get("html_url")}')
    print(f'  status: {pages.get("status")}')
    print(f'  https_enforced: {pages.get("https_enforced")}')

    cert = pages.get('https_certificate', {})
    if cert:
        print(f'  certificate.state: {cert.get("state")}')
        print(f'  certificate.domains: {cert.get("domains")}')

    # Health check
    print('\n--- Health Check ---')
    status, resp = gh('/pages/health')
    if status == 200:
        print(f'  ✓ Health check passed')
        if resp.get('domain'):
            d = resp['domain']
            print(f'    host: {d.get("host")}')
            print(f'    caa_error: {d.get("caa_error")}')
            print(f'    enforces_https: {d.get("enforces_https")}')
            print(f'    https_error: {d.get("https_error")}')
            print(f'    is_served_by_pages: {d.get("is_served_by_pages")}')
    elif status == 202:
        print('  ⏳ Health check in progress (202). 30秒後に再試行...')
        time.sleep(30)
        status2, resp2 = gh('/pages/health')
        if status2 == 200:
            print(f'  ✓ Health check passed (retry)')
        else:
            print(f'  ⚠ Retry returned {status2}')
    else:
        print(f'  ⚠ Health check returned {status}: {json.dumps(resp, indent=2, ensure_ascii=False)[:300]}')

    print(f'\n🌐 確認URL: https://{DOMAIN}/')


# ========== plan ==========

def plan():
    """現在の状態と変更予定を表示"""
    print('=== Plan ===')
    print(f'  Owner/Repo: {OWNER}/{REPO}')
    print(f'  Domain: {DOMAIN}')
    print(f'  CNAME Target: {CNAME_TARGET}')
    print(f'  GITHUB_TOKEN: {_mask(GH_TOKEN)}')
    print(f'  CF_API_TOKEN: {_mask(CF_TOKEN)}')
    print(f'  CF_ZONE_ID: {_mask(CF_ZONE)}')

    # Cloudflare
    print('\n--- Cloudflare DNS (current) ---')
    if not CF_TOKEN or not CF_ZONE:
        print('  ⚠ CLOUDFLARE_API_TOKEN / CLOUDFLARE_ZONE_ID 未設定')
    else:
        existing, conflicts = cf_find_record()
        if existing:
            print(f'  CNAME: {existing["name"]} → {existing["content"]} (proxied={existing.get("proxied")})')
            if existing['content'] == CNAME_TARGET:
                print('  → 変更不要')
            else:
                print(f'  → UPDATE to {CNAME_TARGET}')
        else:
            print(f'  CNAME なし → CREATE {CF_RECORD} → {CNAME_TARGET}')
        if conflicts:
            for r in conflicts:
                print(f'  ⚠ 競合: {r["type"]} {r["name"]} → {r["content"]}')

    # GitHub Pages
    print('\n--- GitHub Pages (current) ---')
    if not GH_TOKEN:
        print('  ⚠ GITHUB_TOKEN 未設定')
    else:
        pages = gh_get_pages()
        if pages is None:
            print('  Pages 未設定 → CREATE')
        else:
            print(f'  cname: {pages.get("cname")}')
            print(f'  https: {pages.get("https_enforced")}')
            print(f'  source: {pages.get("source")}')
            if pages.get('cname') == DOMAIN:
                print('  → 変更不要')
            else:
                print(f'  → UPDATE cname to {DOMAIN}')


# ========== main ==========

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'plan':
        plan()
    elif cmd == 'apply':
        ok1 = cf_apply()
        ok2 = gh_apply()
        if ok1 and ok2:
            print('\n✓ apply 完了。verify で状態を確認してください。')
        else:
            print('\n⚠ 一部失敗。上のログを確認してください。')
            sys.exit(1)
    elif cmd == 'verify':
        verify()
    elif cmd == 'enable-https':
        gh_enable_https()
    else:
        print(f'Unknown command: {cmd}')
        print('Usage: setup_custom_domain.py [plan|apply|verify|enable-https] [--dry-run]')
        sys.exit(1)


if __name__ == '__main__':
    main()
