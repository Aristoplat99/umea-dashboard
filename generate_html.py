import glob
import os
import re
from datetime import datetime

_LOCAL_DATA = os.path.join(os.path.dirname(__file__), 'data')
_EXTERNAL_DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'UmeaSniperUpgrade', 'data'))
# Föredra lokal data/ om den har innehåll, annars fall tillbaka på systerprojektet (lokal dev).
DATA_DIR = _LOCAL_DATA if glob.glob(os.path.join(_LOCAL_DATA, '*_today.txt')) else _EXTERNAL_DATA
OUT_FILE = os.path.join(os.path.dirname(__file__), 'index.html')

LANDLORD_FALLBACK_URLS = {
    'Buref':           'https://buref.se/lediga-lagenheter/',
    'Bostaden':        'https://www.bostaden.umea.se/ledigt',
    'Sveafastigheter': 'https://sveafastigheter.se/lediga-lagenheter',
    'Lerstenen':       'https://lerstenen.se/lediga-lagenheter',
    'Riksbyggen':      'https://www.homeq.se/',
    'Rikshem':         'https://www.rikshem.se/hyra-lagenhet/sok-lagenhet/',
    'HSB':             'https://www.hsb.se/umea/sok-boende/',
    'Heimstaden':      'https://heimstaden.com/sv/lediga-objekt/',
    'Lansa':           'https://www.lansa.se/',
    'Balticgruppen':   'https://balticgruppen.se/',
    'Grannstaden':     'https://grannstaden.se/',
    'Mofab':           'https://mofab.se/',
}

LANDLORD_COLORS = {
    'Buref':           '#4f86c6',
    'Bostaden':        '#e07b39',
    'Sveafastigheter': '#6ab04c',
    'Lerstenen':       '#9b59b6',
    'Riksbyggen':      '#e74c3c',
    'Rikshem':         '#1abc9c',
    'HSB':             '#f39c12',
    'Heimstaden':      '#2980b9',
    'Lansa':           '#16a085',
    'Balticgruppen':   '#8e44ad',
    'Grannstaden':     '#d35400',
    'Mofab':           '#27ae60',
}

def strip_emoji(text):
    return re.sub(r'[\U00010000-\U0010ffff☀-➿︀-️]+\s*', '', text).strip()

def extract_link(line):
    m = re.search(r'\(Länk: (https?://[^\)]+)\)', line)
    if m:
        return m.group(1).strip()
    m = re.search(r'Länk: (https?://\S+)', line)
    if m:
        return m.group(1).strip()
    return None

def extract_landlord(line):
    return strip_emoji(line).split(' | ')[0].strip()

def get_display_text(line, landlord):
    text = re.sub(r'\s*\(Länk: https?://[^\)]+\)', '', line)
    text = re.sub(r'\s*Länk: https?://\S+', '', text)
    text = strip_emoji(text)
    parts = text.split(' | ', 1)
    return parts[1].strip() if len(parts) > 1 else text

def load_listings():
    today_files = sorted(glob.glob(os.path.join(DATA_DIR, '*_today.txt')))

    yesterday_sets = {}
    for f in glob.glob(os.path.join(DATA_DIR, '*_yesterday.txt')):
        name = os.path.basename(f).replace('_yesterday.txt', '')
        try:
            with open(f, encoding='utf-8') as fh:
                yesterday_sets[name] = set(fh.read().splitlines())
        except Exception:
            yesterday_sets[name] = set()

    listings = []
    for today_file in today_files:
        name = os.path.basename(today_file).replace('_today.txt', '')
        yesterday = yesterday_sets.get(name, set())
        try:
            with open(today_file, encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
        except Exception:
            continue
        for line in lines:
            # Hoppa över "tomt-vakt"-rader som scrapers skriver när
            # hyresvärden inte har några lediga lägenheter just nu.
            if '| Inga lediga' in line:
                continue
            landlord = extract_landlord(line)
            link = extract_link(line) or LANDLORD_FALLBACK_URLS.get(landlord, '#')
            is_new = line not in yesterday
            display = get_display_text(line, landlord)
            listings.append({
                'landlord': landlord,
                'display': display,
                'link': link,
                'is_new': is_new,
            })
    return listings

def build_html(listings):
    updated = datetime.now().strftime('%Y-%m-%d %H:%M')
    total = len(listings)
    new_count = sum(1 for l in listings if l['is_new'])
    landlords = sorted(set(l['landlord'] for l in listings))

    # Build landlord filter buttons (visar bara hyresvärdar som faktiskt har lägenheter)
    filter_buttons = '<button class="filter-btn active" onclick="filterLandlord(\'all\', this)">Alla</button>\n'
    for ll in landlords:
        color = LANDLORD_COLORS.get(ll, '#888')
        count = sum(1 for x in listings if x['landlord'] == ll)
        filter_buttons += f'<button class="filter-btn" style="--accent:{color}" onclick="filterLandlord(\'{ll}\', this)">{ll} ({count})</button>\n'

    # Build cards
    cards_html = ''
    for l in listings:
        color = LANDLORD_COLORS.get(l['landlord'], '#888')
        new_badge = '<span class="badge-new">NY</span>' if l['is_new'] else ''
        escaped_display = l['display'].replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
        escaped_landlord = l['landlord'].replace("'", "\\'")
        cards_html += f'''
<div class="card" data-landlord="{l['landlord']}" data-new="{'1' if l['is_new'] else '0'}">
  <div class="card-header" style="background:{color}">
    <span class="landlord-name">{l['landlord']}</span>
    {new_badge}
  </div>
  <div class="card-body">
    <p class="listing-text">{escaped_display}</p>
    <a href="{l['link']}" target="_blank" class="link-btn" style="--accent:{color}">Visa annons →</a>
  </div>
</div>
'''

    html = f'''<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Umeå Bostadsdashboard</title>
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#1a1a2e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Bostäder">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f0f2f5;
    color: #1a1a2e;
    min-height: 100vh;
  }}
  header {{
    background: #1a1a2e;
    color: #fff;
    padding: 1.5rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}
  header h1 {{ font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px; }}
  .stats {{
    display: flex;
    gap: 1.2rem;
    font-size: 0.9rem;
    color: #aab;
  }}
  .stats strong {{ color: #fff; }}
  .updated {{ font-size: 0.8rem; color: #778; }}

  .controls {{
    background: #fff;
    border-bottom: 1px solid #e0e0e0;
    padding: 1rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
  }}
  .filter-group {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}
  .filter-label {{
    font-size: 0.82rem;
    color: #555;
    font-weight: 600;
    min-width: 80px;
  }}
  .status-btn {{
    border: 2px solid transparent;
    background: #f0f2f5;
    color: #444;
    padding: 0.4rem 1rem;
    border-radius: 999px;
    font-size: 0.88rem;
    cursor: pointer;
    transition: all 0.15s;
    font-weight: 600;
  }}
  .status-btn:hover {{ background: #e2e4e8; }}
  .status-btn.active {{
    background: #1a1a2e;
    color: #fff;
    border-color: #1a1a2e;
  }}
  .status-btn.status-new.active {{
    background: #e74c3c;
    border-color: #e74c3c;
  }}
  .filter-btn {{
    border: 2px solid transparent;
    background: #f0f2f5;
    color: #444;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
    font-weight: 500;
  }}
  .filter-btn:hover {{
    background: #e2e4e8;
  }}
  .filter-btn.active {{
    background: var(--accent, #1a1a2e);
    color: #fff;
    border-color: var(--accent, #1a1a2e);
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
    padding: 1.5rem 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }}
  .card {{
    background: #fff;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  }}
  .card[hidden] {{ display: none; }}
  .card-header {{
    padding: 0.6rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #fff;
  }}
  .landlord-name {{ font-weight: 700; font-size: 0.9rem; letter-spacing: 0.3px; }}
  .badge-new {{
    background: #fff;
    color: #e74c3c;
    font-size: 0.7rem;
    font-weight: 800;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    letter-spacing: 0.5px;
  }}
  .card-body {{
    padding: 0.9rem 1rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
  }}
  .listing-text {{
    font-size: 0.88rem;
    line-height: 1.55;
    color: #333;
    word-break: break-word;
  }}
  .link-btn {{
    display: inline-block;
    align-self: flex-start;
    padding: 0.35rem 0.9rem;
    background: var(--accent, #333);
    color: #fff;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
    transition: opacity 0.15s;
  }}
  .link-btn:hover {{ opacity: 0.85; }}

  .empty-state {{
    grid-column: 1 / -1;
    text-align: center;
    padding: 3rem;
    color: #888;
    font-size: 1rem;
  }}
</style>
</head>
<body>

<header>
  <h1>Umeå Bostadsdashboard</h1>
  <div class="stats">
    <span><strong>{total}</strong> lägenheter</span>
    <span><strong id="visible-count">{total}</strong> visas</span>
    <span><strong style="color:#ff6b6b">{new_count}</strong> nya sedan igår</span>
  </div>
  <span class="updated">Uppdaterad {updated}</span>
</header>

<div class="controls">
  <div class="filter-group">
    <span class="filter-label">Visa:</span>
    <button class="status-btn active" onclick="filterStatus('all', this)">Alla ({total})</button>
    <button class="status-btn status-new" onclick="filterStatus('new', this)">Bara nya ({new_count})</button>
  </div>
  <div class="filter-group">
    <span class="filter-label">Hyresvärd:</span>
    {filter_buttons}
  </div>
</div>

<div class="grid" id="grid">
{cards_html}
  <div class="empty-state" id="empty" hidden>Inga lägenheter matchar filtret.</div>
</div>

<script>
  let currentLandlord = 'all';
  let currentStatus = 'all';

  function filterLandlord(landlord, btn) {{
    currentLandlord = landlord;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
  }}

  function filterStatus(status, btn) {{
    currentStatus = status;
    document.querySelectorAll('.status-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
  }}

  function applyFilters() {{
    const cards = document.querySelectorAll('.card');
    let visible = 0;
    cards.forEach(card => {{
      const matchLandlord = currentLandlord === 'all' || card.dataset.landlord === currentLandlord;
      const matchNew = currentStatus === 'all' || card.dataset.new === '1';
      const show = matchLandlord && matchNew;
      card.hidden = !show;
      if (show) visible++;
    }});
    document.getElementById('visible-count').textContent = visible;
    document.getElementById('empty').hidden = visible > 0;
  }}

  // Registrera service worker (gör appen installerbar + offline)
  if ('serviceWorker' in navigator) {{
    window.addEventListener('load', () => {{
      navigator.serviceWorker.register('sw.js').catch(err =>
        console.warn('Service worker kunde inte registreras:', err)
      );
    }});
  }}
</script>

</body>
</html>'''
    return html

def main():
    print(f"Läser datafiler från: {DATA_DIR}")
    listings = load_listings()
    if not listings:
        print("VARNING: Inga lägenheter hittades. Kontrollera att DATA_DIR är korrekt.")
    else:
        print(f"Hittade {len(listings)} lägenheter ({sum(1 for l in listings if l['is_new'])} nya)")
    html = build_html(listings)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Dashboard genererad: {OUT_FILE}")

if __name__ == '__main__':
    main()
