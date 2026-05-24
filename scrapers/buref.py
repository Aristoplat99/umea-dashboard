import os
from playwright.sync_api import sync_playwright

URL = "https://buref.se/lediga-lagenheter/"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "buref_today.txt")

def scrape_buref():
    print("Kollar Buref Umeå...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 1. Kolla HTTP-statusen när vi går till sidan
            response = page.goto(URL, wait_until="domcontentloaded")
            
            if response and response.status in [403, 999]:
                raise Exception(f"Blockerad av brandvagg! HTTP Status {response.status}")
            
            # Tvingande väntetid så att Javascript hinner rita ut texten
            page.wait_for_timeout(6000)
            
            raw_text = page.locator("body").inner_text()
            
            # 2. Kolla efter vanliga blockerings-ord i texten
            lower_text = raw_text.lower()
            if "access denied" in lower_text or "cloudflare" in lower_text or "pardon our interruption" in lower_text:
                raise Exception("Blockerad! Sidan visar 'Access Denied' eller Cloudflare-skydd.")
            
            lines = raw_text.split('\n')
            found_apartments = []
            
            for line in lines:
                line = line.strip()
                if "Lgh" in line:
                    found_apartments.append(line)

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(unique_apts) == 0:
                    f.write("Buref | Inga lediga lagenheter just nu\n")
                    print("Hittade inga lagenheter (sidan verkar tom på riktigt).")
                else:
                    for apt in unique_apts:
                        f.write(f"Buref | {apt}\n")
                    print(f"Hittade {len(unique_apts)} lagenheter live hos Buref.")

        except Exception as e:
            print(f"Fel vid Buref-scrape: {e}")
            raise e  # Kastar felet vidare till run_all.py så ntfy-notisen skickas!
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_buref()