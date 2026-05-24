import os
from playwright.sync_api import sync_playwright

# Inställningar
URL = "https://www.hsb.se/sok-bostad/sok-hyresratter/vasterbotten/umea/?Places=%5b%7b%22name%22:%22Ume%c3%a5%22,%22type%22:%22Kommun%22,%22city%22:%22%22%7d%5d&MinRoom=1&MaxRoom=-1&MinArea=10&MaxArea=-1&MaxFee=-1&Types=Standard&Types=Senior&Types=Junior&Types=Demolition"

def scrape_hsb():
    print("Kollar HSB Umeå...", flush=True)
    
    # 1. Hitta den absoluta sökvägen till mappen där hsb.py ligger
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Hitta projektets huvudmapp (vi antar att hsb.py ligger i /scrapers)
    # Om script_dir slutar på 'scrapers', så är root mappen ovanför
    project_root = os.path.dirname(script_dir)
    
    # 3. Definiera absolut sökväg till data-mappen
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    today_file = os.path.join(data_dir, "hsb_today.txt")
    
    found_apartments = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            page.goto(URL, wait_until="networkidle")
            try:
                page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=3000)
            except Exception:
                pass

            print("Väntar på lägenhetsblock...", flush=True)
            try:
                page.wait_for_selector(".apartment-block__details", timeout=10000)
                listings = page.locator(".apartment-block__details").all()
            except Exception:
                print("Hittade inga lägenhetsblock.")
                listings = []

            for l in listings:
                address_locator = l.locator("h4")
                if address_locator.count() == 0: continue
                address = address_locator.inner_text().strip()
                
                full_text = l.inner_text().replace("\n", " ").strip()
                clean_text = full_text.replace("Visa bostaden", "").strip()
                
                if address and clean_text:
                    link_locator = l.locator("a").first
                    link = "https://www.hsb.se" + link_locator.get_attribute("href") if link_locator.count() > 0 else URL
                    entry = f"HSB | {clean_text} | Länk: {link}"
                    found_apartments.append(entry)
                    print(f"Hittade live: {address}")
        except Exception as e:
            print(f"Fel vid skrapning av HSB: {e}")
            raise e
        finally:
            browser.close()
            
    with open(today_file, "w", encoding="utf-8") as f:
        for apt in sorted(found_apartments):
            f.write(f"{apt}\n")
            
    print(f"HSB klart. Sparade {len(found_apartments)} lägenheter.", flush=True)

if __name__ == "__main__":
    scrape_hsb()