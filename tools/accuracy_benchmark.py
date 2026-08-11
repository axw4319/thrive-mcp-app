#!/usr/bin/env python3
"""Monthly accuracy benchmark: scanner vs Peec.

For each client domain that has a Peec project, runs a fresh 10-prompt scanner
scan and compares the own-brand leaderboard rank against Peec's brand report.
Writes a monthly report and iMessages Aaron if any domain drifts more than
DRIFT_ALERT ranks — the guard against a Windsor-Drake-style miss reaching a
prospect on a strategy call.

Runs via launchd: com.thrive.aivis-accuracy-benchmark (monthly, day 1, 9am).
Peec key comes from the login keychain (service: peec-thrive) — launchd login
session required, never cron.
"""
import json, subprocess, sys, time, urllib.request, urllib.parse, os, datetime

SCANNER = 'https://thrive-ai-visibility.onrender.com'
PEEC = 'https://api.peec.ai/customer/v1'
DRIFT_ALERT = 2
AARON_CELL = '+18179153751'
OUT_DIR = os.path.expanduser('~/Claude/thrive-mcp-app/benchmarks')

# domain -> (peec_project_id, own-brand name substring in Peec, context for the scan)
TARGETS = {
    'thriveagency.com': ('or_09789e0d-64a9-4409-b0ab-08ddb6af9478', 'thrive',
                         'Full-service digital marketing agency (SEO, PPC, AI search). National — customers across the US.'),
    'windsordrake.com': ('or_071ea8b6-a1fa-43c2-af01-b99da056a99b', 'windsor',
                         'Boutique sell-side M&A advisory for founder-led software/tech companies, mid-market deals. National.'),
    'l40.com':          ('or_b19759f6-92f6-426c-b38f-d77c71db479a', 'l40',
                         'Sell-side M&A advisory for mid-market tech companies. National.'),
    'redroanconstruction.com': ('or_1604ec50-355e-405e-b8b3-5046084d374e', 'red roan',
                         'Residential roofing and construction serving San Antonio, TX homeowners. Local.'),
}


def keychain(service):
    return subprocess.run(['security', 'find-generic-password', '-s', service, '-w'],
                          capture_output=True, text=True).stdout.strip()


def http_json(url, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def peec_own_rank(key, project_id, own_sub):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=14)
    rows = http_json(f'{PEEC}/reports/brands', {
        'project_id': project_id, 'start_date': str(start), 'end_date': str(end), 'limit': 200,
    }, {'x-api-key': key})
    rows = rows.get('data', rows) if isinstance(rows, dict) else rows
    rows = [r for r in rows if r.get('visibility') is not None]
    rows.sort(key=lambda r: -r['visibility'])
    for i, r in enumerate(rows, 1):
        if own_sub in r['brand']['name'].lower():
            return i, round(r['visibility'] * 100)
    return None, None


def scanner_scan(domain, context):
    d = http_json(f'{SCANNER}/api/public/scan/start', {
        'website_url': domain, 'prompt_count': 10, 'user_context': context,
        'utm_source': 'internal_test', 'utm_medium': 'accuracy_benchmark'})
    scan_id = d['scan_id']
    for _ in range(40):
        time.sleep(15)
        s = http_json(f'{SCANNER}/api/scan/{scan_id}/status')
        if s['status'] in ('complete', 'error'):
            break
    rep = http_json(f'{SCANNER}/api/scan/{scan_id}/public-report')
    you = next((c for c in rep.get('competitors', []) if c.get('you')), None)
    return scan_id, (you or {}).get('rank'), (you or {}).get('visibility'), round(rep.get('score', 0))


def imessage(text):
    script = f'tell application "Messages" to send {json.dumps(text)} to buddy "{AARON_CELL}" of (service 1 whose service type is iMessage)'
    subprocess.run(['osascript', '-e', script], capture_output=True)


def main():
    key = keychain('peec-thrive')
    if not key:
        print('no peec key in keychain'); sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)
    month = datetime.date.today().strftime('%Y-%m')
    lines = [f'# Scanner vs Peec accuracy benchmark — {month}', '',
             '| Domain | Scanner rank | Peec rank | Drift | Scanner score | Peec vis% | Scan |',
             '|---|---|---|---|---|---|---|']
    alerts = []
    for domain, (proj, own_sub, context) in TARGETS.items():
        try:
            p_rank, p_vis = peec_own_rank(key, proj, own_sub)
            scan_id, s_rank, s_vis, score = scanner_scan(domain, context)
            drift = (s_rank - p_rank) if (s_rank and p_rank) else None
            lines.append(f'| {domain} | {s_rank or "—"} | {p_rank or "—"} | {drift if drift is not None else "—"} | {score} | {p_vis or "—"} | {SCANNER}/report/{scan_id} |')
            if drift is not None and abs(drift) > DRIFT_ALERT:
                alerts.append(f'{domain}: scanner #{s_rank} vs Peec #{p_rank} (drift {drift:+d})')
            print(f'{domain}: scanner #{s_rank} vs peec #{p_rank}')
        except Exception as e:
            lines.append(f'| {domain} | ERROR | | | | | {e} |')
            print(f'{domain}: ERROR {e}')
    out = os.path.join(OUT_DIR, f'benchmark-{month}.md')
    open(out, 'w').write('\n'.join(lines) + '\n')
    print('wrote', out)
    if alerts:
        imessage('AI scanner accuracy drift vs Peec: ' + '; '.join(alerts) + f'. Report: {out}')


if __name__ == '__main__':
    main()
