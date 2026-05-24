import os
from playwright.sync_api import sync_playwright

URL = "https://mofab.se/lediga-fastigheter/"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "mofab_today.txt")

def scrape_mofab():
    print("Kollar Mofab Umeå...")
    os.makedirs(DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            response = page.goto(URL, wait_until="domcontentloaded")

            if response and response.status in [403, 999]:
                raise Exception(f"Mofab blockerar oss! HTTP {response.status}")

            raw_text = page.locator("body").inner_text().lower()
            if "access denied" in raw_text or "cloudflare" in raw_text:
                raise Exception("Mofab blockerar oss! Access Denied eller Cloudflare.")

            # Varje listning är en div.available-object-row
            # Fälten sitter i div.vc_column-inner (h5 = label, resten = värde)
            # Filtrerar bort display:none-rader (dolda/ej tillgängliga objekt)
            listings = page.evaluate("""() => {
                const rows = [...document.querySelectorAll('div.available-object-row')]
                    .filter(row => window.getComputedStyle(row).display !== 'none');
                return rows.map(row => {
                    const fields = {};
                    const columns = row.querySelectorAll('div.vc_column-inner');
                    for (const col of columns) {
                        const h5 = col.querySelector('h5');
                        if (!h5) continue;
                        const label = h5.textContent.trim();
                        const value = col.textContent.replace(label, '').trim();
                        fields[label] = value;
                    }
                    const link = row.querySelector('a');
                    fields['_href'] = link ? link.getAttribute('href') : null;
                    return fields;
                });
            }""")

            found_apartments = []

            for apt in listings:
                andamal = apt.get('Ändamål', '').strip().lower()

                # Filtrera bort lokaler
                if andamal and andamal not in ('bostad', 'lägenhet'):
                    continue

                adress     = apt.get('Adress', '').strip()
                storlek    = apt.get('Storlek', '').strip()
                vaning     = apt.get('Våning', '').strip()
                inflyttning = apt.get('Inflyttning', '').strip()
                href       = apt.get('_href') or URL

                if not adress:
                    continue

                parts = [f"Mofab | {adress}"]
                if storlek:
                    parts.append(storlek)
                if vaning:
                    parts.append(f"vån {vaning}")
                if inflyttning:
                    parts.append(inflyttning)
                parts.append(f"Länk: {href}")

                found_apartments.append(" | ".join(parts))

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if not unique_apts:
                    f.write("Mofab | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter hos Mofab just nu.")
                else:
                    for apt in unique_apts:
                        f.write(f"{apt}\n")
                    print(f"Hittade {len(unique_apts)} lägenheter hos Mofab.")

        except Exception as e:
            print(f"Fel vid Mofab-scrape: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_mofab()
