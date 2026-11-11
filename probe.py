import json, re, time, urllib.request
def req(url, data=None, t=25):
    r = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'Origin': 'https://www.tradingview.com'})
    try:
        x = urllib.request.urlopen(r, timeout=t); return x.status, x.read().decode('utf-8', 'ignore')
    except Exception as e:
        return 'ERR', str(e)[:200]
body = json.dumps({"symbols": {"tickers": ["EQUITI:XAUUSD", "OANDA:XAUUSD", "FXCM:XAUUSD", "FX_IDC:XAUUSD"]}, "columns": ["close", "bid", "ask", "update_mode", "description"]}).encode()
for u in ['https://scanner.tradingview.com/forex/scan', 'https://scanner.tradingview.com/cfd/scan', 'https://scanner.tradingview.com/global/scan']:
    print('SCAN', u, *req(u, body))
for sym in ['EQUITI:XAUUSD', 'OANDA:XAUUSD']:
    print('SYM', sym, *req('https://scanner.tradingview.com/symbol?symbol=%s&fields=close,bid,ask,update_mode&no_404=true' % sym))
s, h = req('https://www.tradingview.com/symbols/XAUUSD/?exchange=EQUITI')
print('PAGE', s, len(h), re.findall(r'"last_price":\s*[\d.]+|"price":\s*[\d.]+|"lp":\s*[\d.]+', h)[:6], re.findall(r'\b\d,\d{3}\.\d{1,3}\b', h)[:6])
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 1400, 'height': 900})
        pg.goto('https://www.tradingview.com/symbols/XAUUSD/?exchange=EQUITI', wait_until='domcontentloaded', timeout=45000); pg.wait_for_timeout(9000)
        txt = pg.inner_text('body')
        print('BROWSER nums', re.findall(r'\b\d{1,2},?\d{3}\.\d{1,3}\b', txt)[:10])
        print('BROWSER text', txt[:500].replace('\n', ' | '))
        br.close()
except Exception as e:
    print('playwright ERR', e)
