import json, re, time, urllib.request
def get(url, t=25):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        r = urllib.request.urlopen(req, timeout=t); return r.status, r.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR', str(e)[:200]
out = {}
for name, url in [
  ('yahoo_XAUUSD=X_15m', 'https://query1.finance.yahoo.com/v8/finance/chart/XAUUSD=X?interval=15m&range=5d'),
  ('yahoo_GC=F_15m', 'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=15m&range=5d'),
  ('yahoo_GC=F_1h', 'https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1h&range=60d'),
  ('stooq_xauusd_d', 'https://stooq.com/q/d/l/?s=xauusd&i=d'),
  ('stooq_xauusd_h', 'https://stooq.com/q/d/l/?s=xauusd&i=h'),
  ('pages_health', 'https://ts-view-7k3q.github.io/ts-f23f294c4a/health.json'),
]:
    s, b = get(url)
    info = {'status': s, 'len': len(b)}
    if name.startswith('yahoo') and s == 200:
        try:
            j = json.loads(b)['chart']['result'][0]; ts = j['timestamp']
            info.update(bars=len(ts), last=j['meta'].get('regularMarketPrice'), lastbar=time.strftime('%F %T', time.gmtime(ts[-1])))
        except Exception as e: info['parse'] = str(e)[:100]
    else:
        info['head'] = b[:160].replace('\n', ' ')
    out[name] = info
print(json.dumps(out, indent=1))
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, url in [('tv_equiti_symbol', 'https://www.tradingview.com/symbols/XAUUSD/?exchange=EQUITI'),
                          ('tv_equiti_chart', 'https://www.tradingview.com/chart/pqG1FsBz/?symbol=EQUITI%3AXAUUSD'),
                          ('tv_oanda_symbol', 'https://www.tradingview.com/symbols/XAUUSD/?exchange=OANDA')]:
            pg = br.new_page(viewport={'width': 1400, 'height': 900})
            try:
                pg.goto(url, wait_until='domcontentloaded', timeout=45000); pg.wait_for_timeout(9000)
                txt = pg.inner_text('body')[:3000]
                print(name, 'title=', pg.title()[:80], 'nums=', re.findall(r'\b\d{4}\.\d{1,3}\b', txt)[:8])
                pg.screenshot(path=name + '.png')
            except Exception as e:
                print(name, 'ERR', str(e)[:200])
            pg.close()
        br.close()
except Exception as e:
    print('playwright ERR', e)
