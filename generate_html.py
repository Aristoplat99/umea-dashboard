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


# ---------- Parsning av lägenhetsrader ----------

def _strip_emoji(text):
    return re.sub(r'[\U00010000-\U0010ffff☀-➿︀-️]+\s*', '', text).strip()

def _strip_link(text):
    text = re.sub(r'\s*\(Länk:\s*https?://[^\)]+\)', '', text)
    text = re.sub(r'\s*Länk:\s*https?://\S+', '', text)
    return text

def extract_link(line):
    m = re.search(r'\(Länk:\s*(https?://[^\)]+)\)', line)
    if m: return m.group(1).strip()
    m = re.search(r'Länk:\s*(https?://\S+)', line)
    if m: return m.group(1).strip()
    return None

def extract_landlord(line):
    return _strip_emoji(line).split(' | ')[0].strip()

def extract_rent(text):
    """Hyra i kr/mån som int, eller None."""
    m = re.search(r'(\d[\d\s.]*?)\s*kr\b', text)
    if not m: return None
    digits = re.sub(r'\D', '', m.group(1))
    if not digits: return None
    try:
        v = int(digits)
        # Sanity: hyror brukar ligga mellan 1000-50000
        return v if 500 <= v <= 100000 else None
    except ValueError:
        return None

def extract_size(text):
    """Storlek i m² som float, eller None."""
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kvm|m²|m2)\b', text, re.IGNORECASE)
    if not m: return None
    try:
        return float(m.group(1).replace(',', '.'))
    except ValueError:
        return None

def extract_rooms(text):
    """Antal rum som int, eller None."""
    m = re.search(r'\b(\d+)\s*(?:rok|rkv|roka|rum|r o k)\b', text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def extract_move_in(text):
    """Inflyttningsdatum som ISO-string, eller None."""
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    return m.group(1) if m else None

def extract_address(line, landlord):
    """Heuristisk adress-extraktion per hyresvärd. Fallback: första |-fältet."""
    text = _strip_emoji(_strip_link(line))
    parts = [p.strip() for p in text.split(' | ') if p.strip()]
    if len(parts) < 2:
        return text
    candidates = parts[1:]  # hoppa över hyresvärds-prefix

    # Buref: "Lgh 02:17, Sofiehemsvägen 76B: 1 Rkv, ..."
    if landlord == 'Buref':
        m = re.match(r'^Lgh\s+[\w:]+,\s*([^:]+):', candidates[0])
        if m: return m.group(1).strip()
    # Riksbyggen: "Kålhagsvägen 16A   Kålhagsvägen 16A, Umeå Månadshyra ..."
    if landlord == 'Riksbyggen':
        m = re.match(r'^(.+?)(?:\s{2,}|\s*,\s*Umeå)', candidates[0])
        if m: return m.group(1).strip()
    # Lerstenen: "Stadsdel | Adress | ..." → adressen är parts[2]
    if landlord == 'Lerstenen' and len(parts) >= 3:
        return parts[2].strip()
    # Default: första kandidat som har en siffra och inte är ett rent metadata-fält.
    # Tillåter att fältet innehåller "X rok" (HSB packar in det i adress-strängen)
    # och städar bort metadata efteråt.
    def _is_pure_metadata(p):
        if re.match(r'^\s*(Hyra|Månadshyra|Inflytt|Inflyttning|Från|Ledig|Tillgänglig|Vån\b)', p, re.IGNORECASE):
            return True
        if re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*(?:kvm|m²|m2)\s*', p, re.IGNORECASE):
            return True
        if re.search(r'\d\s*kr\b', p, re.IGNORECASE):
            return True
        if re.fullmatch(r'\s*\d{4}-\d{2}-\d{2}\s*', p):
            return True
        return False

    def _clean(p):
        # Plocka bort "X rok"-suffix om det hänger med (HSB)
        p = re.sub(r',?\s*\d+\s*(?:rok|rum|rkv|roka|r o k)\b.*$', '', p, flags=re.IGNORECASE)
        # Ta bort standalone "Umeå"
        p = re.sub(r'\bUme[åa]\b', '', p, flags=re.IGNORECASE)
        # Ta bort UMEÅ-suffix (Lansa)
        p = re.sub(r'\s+UMEÅ\s*$', '', p, flags=re.IGNORECASE)
        # Städa whitespace och kommatecken
        p = re.sub(r'\s+', ' ', p).strip()
        p = re.sub(r'\s+,', ',', p)         # "X , Y" -> "X, Y"
        p = re.sub(r',\s*,', ',', p)        # ", ," -> ","
        p = re.sub(r'^[,\s]+|[,\s]+$', '', p)
        return p.strip()

    for p in candidates:
        if _is_pure_metadata(p):
            continue
        if re.search(r'\d', p):
            cleaned = _clean(p)
            if cleaned:
                return cleaned
    return _clean(candidates[0])


def parse_listing(line, landlord):
    """Returnera strukturerat lägenhetsobjekt."""
    return {
        'address': extract_address(line, landlord),
        'rent': extract_rent(line),
        'size': extract_size(line),
        'rooms': extract_rooms(line),
        'move_in': extract_move_in(line),
    }


# ---------- Inläsning ----------

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
            # Hoppa över "tomt-vakt"-rader (scraper-körde-ok-men-noll-resultat)
            if '| Inga lediga' in line:
                continue
            landlord = extract_landlord(line)
            link = extract_link(line) or LANDLORD_FALLBACK_URLS.get(landlord, '#')
            is_new = line not in yesterday
            parsed = parse_listing(line, landlord)
            listings.append({
                'landlord': landlord,
                'link': link,
                'is_new': is_new,
                'raw': line,
                **parsed,
            })
    return listings


# ---------- HTML-rendering ----------

def _esc(s):
    return (str(s) if s is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')

def _format_rent(rent):
    if rent is None:
        return '— kr/mån'
    # 7710 -> "7 710 kr/mån"
    return f"{rent:,}".replace(',', ' ') + " kr/mån"

def _format_meta(rooms, size, move_in):
    bits = []
    if rooms is not None:
        bits.append(f"{rooms} rok")
    if size is not None:
        bits.append(f"{size:g} m²")
    if move_in:
        bits.append(f"Inflytt {move_in}")
    return ' · '.join(bits)


def build_html(listings):
    updated = datetime.now().strftime('%Y-%m-%d %H:%M')
    total = len(listings)
    new_count = sum(1 for l in listings if l['is_new'])
    landlords = sorted(set(l['landlord'] for l in listings))

    # Hyresvärds-filter (visar bara hyresvärdar som faktiskt har lägenheter)
    filter_buttons = '<button class="filter-btn active" onclick="filterLandlord(\'all\', this)">Alla</button>\n'
    for ll in landlords:
        count = sum(1 for x in listings if x['landlord'] == ll)
        filter_buttons += f'<button class="filter-btn" onclick="filterLandlord({_esc(repr(ll))}, this)">{_esc(ll)} ({count})</button>\n'

    # Kort
    cards_html = ''
    for l in listings:
        new_badge = '<span class="badge-new">NY</span>' if l['is_new'] else ''
        new_class = ' is-new' if l['is_new'] else ''
        rent_attr = l['rent'] if l['rent'] is not None else 99999999
        size_attr = l['size'] if l['size'] is not None else 0
        address = _esc(l['address']) or '(okänd adress)'
        meta = _esc(_format_meta(l['rooms'], l['size'], l['move_in']))
        meta_html = f'<div class="meta">{meta}</div>' if meta else ''
        cards_html += f'''
<div class="card{new_class}" data-landlord="{_esc(l['landlord'])}" data-new="{'1' if l['is_new'] else '0'}" data-rent="{rent_attr}" data-size="{size_attr}">
  <div class="card-top">
    <h3 class="address">{address}</h3>
    {new_badge}
  </div>
  {meta_html}
  <div class="rent">{_format_rent(l['rent'])}</div>
  <div class="card-foot">
    <span class="landlord-tag">{_esc(l['landlord'])}</span>
    <a href="{_esc(l['link'])}" target="_blank" rel="noopener" class="link-btn">Visa annons →</a>
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
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    background: #f5f5f7;
    color: #1c1c1e;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }}

  header {{
    background: #1a1a2e;
    color: #fff;
    padding: 1.2rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.5rem;
  }}
  header h1 {{ font-size: 1.25rem; font-weight: 700; letter-spacing: -0.3px; }}
  .stats {{
    display: flex;
    gap: 1.2rem;
    font-size: 0.85rem;
    color: #a8a8b3;
  }}
  .stats strong {{ color: #fff; font-weight: 700; }}
  .stats .new-pill {{ color: #ff6b6b; }}
  .updated {{ font-size: 0.75rem; color: #6e6e80; }}

  .controls {{
    background: #fff;
    border-bottom: 1px solid #e5e5ea;
    padding: 0.9rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }}
  .filter-group {{
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
  }}
  .filter-label {{
    font-size: 0.78rem;
    color: #6e6e73;
    font-weight: 600;
    min-width: 78px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}
  .status-btn, .filter-btn {{
    border: 1px solid #e5e5ea;
    background: #fff;
    color: #1c1c1e;
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.84rem;
    cursor: pointer;
    transition: all 0.12s;
    font-weight: 500;
    font-family: inherit;
  }}
  .status-btn:hover, .filter-btn:hover {{ background: #f0f0f4; }}
  .status-btn.active, .filter-btn.active {{
    background: #1a1a2e;
    color: #fff;
    border-color: #1a1a2e;
  }}
  .status-btn.status-new.active {{
    background: #ff3b30;
    border-color: #ff3b30;
  }}
  .filter-input {{
    border: 1px solid #e5e5ea;
    background: #fff;
    color: #1c1c1e;
    padding: 0.35rem 0.7rem;
    border-radius: 8px;
    font-size: 0.84rem;
    font-family: inherit;
    width: 100px;
  }}
  .filter-input:focus {{ outline: none; border-color: #1a1a2e; }}
  select.filter-input {{ width: auto; cursor: pointer; }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.8rem;
    padding: 1.2rem 1.5rem;
    max-width: 1400px;
    margin: 0 auto;
  }}

  .card {{
    background: #fff;
    border: 1px solid #e5e5ea;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    transition: border-color 0.12s, box-shadow 0.12s, transform 0.12s;
  }}
  .card:hover {{
    border-color: #d0d0d8;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    transform: translateY(-1px);
  }}
  .card[hidden] {{ display: none; }}
  .card.is-new {{ border-color: #ffcec9; }}

  .card-top {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.6rem;
  }}
  .address {{
    font-size: 1rem;
    font-weight: 600;
    color: #1c1c1e;
    line-height: 1.3;
    letter-spacing: -0.1px;
  }}
  .badge-new {{
    background: #ff3b30;
    color: #fff;
    font-size: 0.65rem;
    font-weight: 800;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    letter-spacing: 0.5px;
    flex-shrink: 0;
    line-height: 1.3;
  }}
  .meta {{
    font-size: 0.82rem;
    color: #6e6e73;
    line-height: 1.4;
  }}
  .rent {{
    font-size: 1.15rem;
    font-weight: 700;
    color: #1c1c1e;
    letter-spacing: -0.3px;
    margin-top: 0.1rem;
  }}
  .card-foot {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.4rem;
    padding-top: 0.7rem;
    border-top: 1px solid #f0f0f4;
  }}
  .landlord-tag {{
    font-size: 0.72rem;
    color: #6e6e73;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }}
  .link-btn {{
    padding: 0.3rem 0.8rem;
    background: #1a1a2e;
    color: #fff;
    border-radius: 7px;
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.12s;
  }}
  .link-btn:hover {{ background: #2a2a4e; }}

  .empty-state {{
    grid-column: 1 / -1;
    text-align: center;
    padding: 3rem 1rem;
    color: #8e8e93;
    font-size: 0.95rem;
  }}

  @media (max-width: 600px) {{
    header {{ padding: 1rem; }}
    .stats {{ gap: 0.8rem; font-size: 0.78rem; }}
    .controls {{ padding: 0.8rem 1rem; }}
    .filter-label {{ min-width: auto; }}
    .grid {{ padding: 1rem; gap: 0.7rem; }}
  }}
</style>
</head>
<body>

<header>
  <h1>Umeå Bostadsdashboard</h1>
  <div class="stats">
    <span><strong>{total}</strong> lägenheter</span>
    <span><strong id="visible-count">{total}</strong> visas</span>
    <span class="new-pill"><strong>{new_count}</strong> nya sedan igår</span>
  </div>
  <span class="updated">Uppdaterad {updated}</span>
</header>

<div class="controls">
  <div class="filter-group">
    <span class="filter-label">Visa</span>
    <button class="status-btn active" onclick="filterStatus('all', this)">Alla ({total})</button>
    <button class="status-btn status-new" onclick="filterStatus('new', this)">Bara nya ({new_count})</button>
  </div>
  <div class="filter-group">
    <span class="filter-label">Hyresvärd</span>
    {filter_buttons}
  </div>
  <div class="filter-group">
    <span class="filter-label">Hyra & yta</span>
    <span>Max</span>
    <input id="max-rent" class="filter-input" type="number" min="0" step="500" placeholder="ingen gräns" oninput="applyFilters()">
    <span>kr</span>
    <span style="margin-left:0.4rem">Min</span>
    <input id="min-size" class="filter-input" type="number" min="0" step="5" placeholder="ingen gräns" oninput="applyFilters()">
    <span>m²</span>
  </div>
  <div class="filter-group">
    <span class="filter-label">Sortering</span>
    <select id="sort" class="filter-input" onchange="applyFilters()">
      <option value="default">Standard</option>
      <option value="rent-asc">Hyra (lägst först)</option>
      <option value="rent-desc">Hyra (högst först)</option>
      <option value="size-desc">Yta (störst först)</option>
      <option value="size-asc">Yta (minst först)</option>
    </select>
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
    const maxRent = parseInt(document.getElementById('max-rent').value, 10);
    const minSize = parseFloat(document.getElementById('min-size').value);
    const sort = document.getElementById('sort').value;
    const grid = document.getElementById('grid');
    const cards = Array.from(grid.querySelectorAll('.card'));

    let visible = 0;
    cards.forEach(card => {{
      const matchLandlord = currentLandlord === 'all' || card.dataset.landlord === currentLandlord;
      const matchNew = currentStatus === 'all' || card.dataset.new === '1';
      const rent = parseInt(card.dataset.rent, 10);
      const size = parseFloat(card.dataset.size);
      const matchRent = isNaN(maxRent) || rent <= maxRent;
      const matchSize = isNaN(minSize) || size >= minSize;
      const show = matchLandlord && matchNew && matchRent && matchSize;
      card.hidden = !show;
      if (show) visible++;
    }});

    // Sortering: flytta om DOM-noderna
    if (sort !== 'default') {{
      const sorted = cards.slice().sort((a, b) => {{
        const key = sort.startsWith('rent') ? 'rent' : 'size';
        const va = parseFloat(a.dataset[key]);
        const vb = parseFloat(b.dataset[key]);
        return sort.endsWith('-asc') ? va - vb : vb - va;
      }});
      const empty = document.getElementById('empty');
      sorted.forEach(c => grid.appendChild(c));
      grid.appendChild(empty);
    }}

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
