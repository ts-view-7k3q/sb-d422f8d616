#!/usr/bin/env python3
"""V1 cloud standby (GitHub Actions). Takes over ONLY when the Mac/ThinkPad program has stopped publishing.
check  -> writes run=true|false to GITHUB_OUTPUT (is the primary stale? is gold open?)
run    -> reads Equiti gold price (TradingView page), adjusts Yahoo gold-futures candle highs/lows to it, flags touched entry/TP/SL of the setups the Mac exported, ntfy alert (chart-read)."""
import os, sys, re, json, time, urllib.request, datetime
PAGES = 'https://ts-view-7k3q.github.io/ts-f23f294c4a/'
STATE = 'state.json'; UA = {'User-Agent': 'Mozilla/5.0'}
STALE_MIN = 20
def get(url, t=25):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=t).read().decode('utf-8', 'ignore')
def load():
    try: return json.load(open(STATE))
    except Exception: return {'sent': {}, 'last_ts': 0}
def market_open(now):
    wd = now.weekday(); h = now.hour
    if wd == 5: return False
    if wd == 4 and h >= 21: return False
    if wd == 6 and h < 22: return False
    return True
def primary_age():
    try:
        b = json.loads(get(PAGES + 'health.json?x=%d' % time.time()))['built']
        t = datetime.datetime.strptime(b, '%Y-%m-%d %H:%M UTC').replace(tzinfo=datetime.timezone.utc)
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 60
    except Exception as e:
        return 9999
def out(k, v):
    print(k, v)
    if os.environ.get('GITHUB_OUTPUT'): open(os.environ['GITHUB_OUTPUT'], 'a').write('%s=%s\n' % (k, v))
def check():
    now = datetime.datetime.now(datetime.timezone.utc); age = primary_age(); st = load()
    st['primary_age_min'] = round(age, 1); st['checked'] = now.strftime('%F %T'); json.dump(st, open(STATE, 'w'))
    go = (age > STALE_MIN or os.path.exists('force.txt')) and market_open(now)
    out('run', 'true' if go else 'false')
def equiti_price():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        for url, rx, name in [('https://www.tradingview.com/symbols/XAUUSD/?exchange=EQUITI', r'Equiti\s*\|\s*([\d,]+\.\d+)', 'Equiti'),
                              ('https://www.tradingview.com/symbols/XAUUSD/?exchange=OANDA', r'OANDA\s*\|\s*([\d,]+\.\d+)', 'OANDA'),
                              ('https://www.tradingview.com/symbols/XAUUSD/?exchange=FXCM', r'FXCM\s*\|\s*([\d,]+\.\d+)', 'FXCM')]:
            try:
                pg = br.new_page(); pg.goto(url, wait_until='domcontentloaded', timeout=45000); pg.wait_for_timeout(8000)
                m = re.search(rx, pg.inner_text('body'))
                pg.close()
                if m: br.close(); return float(m.group(1).replace(',', '')), name
            except Exception: continue
        br.close()
    return None, None
def yahoo_bars():
    j = json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=15m&range=2d'))['chart']['result'][0]
    q = j['indicators']['quote'][0]; ts = j['timestamp']
    return [(t, h, l, c) for t, h, l, c in zip(ts, q['high'], q['low'], q['close']) if h and l and c]
def alert(text, click=''):
    tp = os.environ.get('NTFY_TOPIC')
    if not tp: print('NO TOPIC:', text); return
    h = {'Title': 'Gold (cloud standby, chart-read)'}
    if click: h['Click'] = click
    urllib.request.urlopen(urllib.request.Request('https://ntfy.sh/' + tp, data=text.encode(), headers=h), timeout=20)
def run():
    st = load(); now = time.time()
    px, src = equiti_price()
    if px is None: print('no price source'); return
    try:
        bars = yahoo_bars(); basis = px - bars[-1][3]
        since = max(st.get('last_ts', 0), now - 3 * 3600)
        rec = [b for b in bars if b[0] >= since - 900]
        hi = max([b[1] + basis for b in rec] + [px]); lo = min([b[2] + basis for b in rec] + [px])
    except Exception as e:
        print('yahoo fail', e); hi = lo = px
    try: setups = json.loads(get(PAGES + 'standby_setups.json?x=%d' % now))['setups']
    except Exception as e: print('no setups file', e); setups = []
    ev = []
    nowS = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    for s in setups:
        buy = str(s['side']).upper() == 'BUY'
        if not s.get('entered'):
            if str(s.get('expiry', '9999')) < nowS: continue
            if lo <= s['entry'] <= hi: ev.append(('entry', s, s['entry']))
        else:
            if (hi >= s['tp1'] if buy else lo <= s['tp1']): ev.append(('tp1', s, s['tp1']))
            if (lo <= s['sl'] if buy else hi >= s['sl']): ev.append(('sl', s, s['sl']))
    for t, s, lvl in ev:
        key = '%s|%s' % (s['id'], t)
        if key in st['sent']: continue
        word = {'entry': 'ENTRY touched', 'tp1': 'TP1 touched', 'sl': 'SL touched'}[t]
        alert('%s %s %s: %s at %.2f. Price %.2f (%s). Mac is off, so this is a chart read.' % (s['system'], s['side'], s['id'], word, lvl, px, src))
        st['sent'][key] = int(now)
    st.update(last_ts=int(now), price=px, source=src, hi=round(hi, 2), lo=round(lo, 2), events=len(ev), ran=time.strftime('%F %T', time.gmtime()))
    json.dump(st, open(STATE, 'w'), indent=1); print('price', px, src, 'hi', hi, 'lo', lo, 'events', len(ev))
if __name__ == '__main__':
    check() if (sys.argv[1:] or ['run'])[0] == 'check' else run()
