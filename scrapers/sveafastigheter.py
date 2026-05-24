import os
import re
from playwright.sync_api import sync_playwright

URL = "https://sveafastigheter.se/se-alla-lediga-lagenheter-for-uthyrning?search=ume%C3%A5&type=lagenheter"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "sveafastigheter_today.txt")

def scrape_svea():
    print("Kollar Sveafastigheter Umeå...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            response = page.goto(URL, wait_until="domcontentloaded")
            
            if response and response.status in [403, 999]:
                raise Exception(f"Sveafastigheter blockerar oss! HTTP Status {response.status}")
                
            try:
                page.click("button:has-text('Acceptera'), button:has-text('Godkänn')", timeout=3000)
            except:
                pass

            print("Väntar på att data ska landa i koden...")
            page.wait_for_selector(".homeq_title", state="attached", timeout=15000)
            
            raw_text = page.locator("body").inner_text().lower()
            if "access denied" in raw_text or "cloudflare" in raw_text:
                raise Exception("Sveafastigheter blockerar oss! Sidan visar 'Access Denied'.")

            # Hämta alla annonskort
            listings = page.locator("a:has(.homeq_title)").all()
            print(f"Hittade {len(listings)} element i koden. Filtrerar för Umeå...")

            found_apartments = []

            for l in listings:
                full_text = l.inner_text()
                
                # Kontrollera att lägenheten faktiskt ligger i Umeå
                if "Umeå" in full_text:
                    title_loc = l.locator(".homeq_title")
                    if title_loc.count() == 0: 
                        continue
                        
                    address = title_loc.inner_text().strip()
                    
                    # Flexibel sökning efter storlek och hyra
                    details = ""
                    rent = ""
                    lines = full_text.split("\n")
                    for line in lines:
                        line_str = line.strip()
                        line_lower = line_str.lower()
                        
                        # UPPDATERAD: Letar efter rum, rok, r o k, kvm eller m²
                        if any(x in line_lower for x in ["rum", "rok", "r o k", "kvm", "m²"]):
                            details = line_str
                        
                        if re.search(r'\d.*\bkr\b', line_lower):
                            rent = line_str

                    detail_str = f" | {details}" if details else ""
                    rent_str = f" | {rent}" if rent else ""

                    if address:
                        href = l.get_attribute("href")
                        if href and href.startswith("/"):
                            href = "https://sveafastigheter.se" + href
                        
                        found_apartments.append(f"{address}{detail_str}{rent_str} (Länk: {href})")

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(unique_apts) == 0:
                    f.write("Sveafastigheter | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter i Umeå just nu.")
                else:
                    for apt in unique_apts:
                        f.write(f"Sveafastigheter | {apt}\n")
                    print(f"Hittade {len(unique_apts)} lägenheter live hos Sveafastigheter.")

        except Exception as e:
            print(f"Fel vid Sveafastigheter-scrape: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_svea()