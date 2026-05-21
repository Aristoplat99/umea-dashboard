# Umeå Bostadsdashboard

En fristående webb-/PWA-app som visar lediga hyreslägenheter i Umeå från flera hyresvärdar på ett ställe. Kan installeras på mobilen som en app.

## Vad den gör

- Läser lägenhetsdata och genererar en `index.html` med kort per lägenhet
- Filtrera per hyresvärd och visa bara nya sedan igår
- Installerbar som app (PWA) på mobil och desktop

## Köra lokalt

```powershell
# Generera dashboarden
python generate_html.py

# Generera om app-ikonerna (vid behov)
python generate_icons.py

# Starta lokal server (krävs för att testa PWA-installation)
python -m http.server 8000
```

Öppna sedan `http://localhost:8000/index.html`.

## Datakälla

Just nu läser `generate_html.py` datafilerna från det separata scraper-projektet
(`../UmeaSniperUpgrade/data/*_today.txt`). Sökvägen styrs av `DATA_DIR` överst i skriptet.

## Filöversikt

- `generate_html.py` — läser datafiler och bygger `index.html`
- `generate_icons.py` — genererar app-ikoner i `icons/`
- `manifest.json` — PWA-manifest (namn, ikoner, tema)
- `sw.js` — service worker (installerbarhet + offline-cache)
- `index.html` — genererad dashboard (output)
