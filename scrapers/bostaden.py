import os
import re
from playwright.sync_api import sync_playwright

# Filtret i URL:en begränsar till studentbostäder (avtalstyp=2)
URL = "https://www.bostaden.umea.se/bostadssokande/lediga-lagenheter/?street=&avtalstyp%5B%5D=2&min_rent=0&max_rent=20000&min_size=0&max_size=200"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "bostaden_today.txt")

# Skydd mot oändlig loop om paginering ändras
MAX_PAGES = 20

# JS som plockar ut unika kortcontainers via detalj-länk på aktuell sida
EXTRACT_JS = """() => {
    const seen = new Set();
    const results = [];

    const cards = document.querySelectorAll("a[href*='/ledigt/detalj/id/']");
    for (const a of cards) {
        const href = a.getAttribute('href');
        if (seen.has(href)) continue;
        seen.add(href);

        // Gå upp tills vi hittar ett element med Hyra-info
        let card = a.parentElement;
        for (let i = 0; i < 8; i++) {
            if (!card) break;
            if (card.textContent.includes('Hyra')) break;
            card = card.parentElement;
        }

        const text = card ? card.textContent.trim().replace(/\\s+/g, ' ') : '';
        results.push({ href, text });
    }
    return results;
}"""

def scrape_bostaden():
    print("Kollar Bostaden Umeå (studentbostäder)...")
    os.makedirs(DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            response = page.goto(URL, wait_until="networkidle")

            if response and response.status in [403, 999]:
                raise Exception(f"Bostaden blockerar oss! HTTP {response.status}")

            page.wait_for_timeout(3000)

            # Cookiebot-dialog: prova flera knappvarianter
            for sel in [
                "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
                "text=Tillåt alla cookies",
                "text=Tillåt alla",
            ]:
                try:
                    page.click(sel, timeout=3000)
                    page.wait_for_timeout(2000)
                    break
                except Exception:
                    continue

            raw_text = page.locator("body").inner_text().lower()
            if "access denied" in raw_text or "cloudflare" in raw_text:
                raise Exception("Bostaden blockerar oss! Access Denied eller Cloudflare.")

            # Hur många sidor finns? Läs av pagineringens sidlänkar (?pag=N)
            page_numbers = page.evaluate("""() => {
                const nums = new Set([1]);
                for (const a of document.querySelectorAll("a[href*='pag=']")) {
                    const m = a.href.match(/[?&]pag=(\\d+)/);
                    if (m) nums.add(parseInt(m[1], 10));
                }
                return [...nums].sort((a, b) => a - b);
            }""")
            max_page = min(max(page_numbers), MAX_PAGES) if page_numbers else 1
            print(f"Hittade {max_page} sida(or) hos Bostaden.")

            # Samla in listings från alla sidor
            listings = page.evaluate(EXTRACT_JS)

            for p_num in range(2, max_page + 1):
                page_url = f"{URL}&pag={p_num}"
                resp = page.goto(page_url, wait_until="networkidle")
                if resp and resp.status in [403, 999]:
                    raise Exception(f"Bostaden blockerar oss! HTTP {resp.status}")
                page.wait_for_timeout(2000)
                listings.extend(page.evaluate(EXTRACT_JS))

            found_apartments = []

            for apt in listings:
                text = apt.get("text", "")
                href = apt.get("href", URL)

                # Extrahera adress (text före "Studentbostad" eller "Omr")
                adress_match = re.match(r"^(.+?)(?:\s+Studentbostad|\s+Omr)", text)
                adress = adress_match.group(1).strip() if adress_match else ""

                # Hyra
                hyra_match = re.search(r"Hyra kr/m[åa]n:\s*(\d+)", text)
                hyra = f"{hyra_match.group(1)} kr/mån" if hyra_match else ""

                # Storlek
                yta_match = re.search(r"Yta:\s*(\d+)\s*kvm", text)
                yta = f"{yta_match.group(1)} kvm" if yta_match else ""

                # Rum (ta allt mellan "Typ: " och ", Stud")
                rum_match = re.search(r"Typ:\s*(.+?)(?:,\s*Stud)", text)
                rum = rum_match.group(1).strip() if rum_match else ""

                # Storlek
                yta_match = re.search(r"Yta[^:]*:\s*(\d+)", text)
                yta = f"{yta_match.group(1)} kvm" if yta_match else ""

                # Inflyttning
                infly_match = re.search(r"Inflyttning:\s*(\d{4}-\d{2}-\d{2})", text)
                inflyttning = f"Inflyttning: {infly_match.group(1)}" if infly_match else ""

                if not adress:
                    continue

                parts = [f"Bostaden | {adress}"]
                if hyra:
                    parts.append(hyra)
                if yta:
                    parts.append(yta)
                if rum:
                    parts.append(rum)
                if inflyttning:
                    parts.append(inflyttning)
                parts.append(f"Länk: {href}")

                found_apartments.append(" | ".join(parts))

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if not unique_apts:
                    f.write("Bostaden | Inga lediga studentlagenheter just nu\n")
                    print("Inga lediga studentbostäder hos Bostaden just nu.")
                else:
                    for apt in unique_apts:
                        f.write(f"{apt}\n")
                    print(f"Hittade {len(unique_apts)} studentbostäder hos Bostaden.")

        except Exception as e:
            print(f"Fel vid Bostaden-scrape: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_bostaden()
