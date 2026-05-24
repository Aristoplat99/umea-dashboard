import os
import re
from playwright.sync_api import sync_playwright

URL = "https://minasidor.rikshem.se/ledigt/lagenhet?objectgroup=&selectedarea=AREAUMEA"
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "rikshem_today.txt")

def scrape_rikshem():
    print("Kollar Rikshem Umeå...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(URL, wait_until="networkidle")
            
            # Cookie-slakt
            try:
                page.wait_for_selector("#CybotCookiebotDialogBodyButtonAccept", timeout=5000)
                page.locator("#CybotCookiebotDialogBodyButtonAccept").click()
                page.wait_for_timeout(2000)
            except:
                pass

            page.wait_for_timeout(4000)
            
            todays_apartments = set()

            links = page.locator("a[href*='detalj/id/']").all()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    card_container = link.evaluate_handle("el => el.closest('.item-inner') || el.closest('tr') || el.closest('div[class*=\"object\"]') || el.parentElement.parentElement")
                    full_card_text = page.evaluate("el => el.innerText", card_container)
                    
                    lines = full_card_text.split('\n')
                    
                    for line in lines:
                        clean_line = line.strip()
                        clean_line = re.sub(r'\s+', ' ', clean_line)
                        
                        # FILTRERING: Vi tar bara rader som innehåller Umeå och ett datum (t.ex. 2026-08-01)
                        # Detta rensar bort mobildubbletterna direkt!
                        if "umeå" in clean_line.lower() and re.search(r'\d{4}-\d{2}-\d{2}', clean_line):
                            
                            clean_href = href.replace("../", "")
                            full_url = f"https://minasidor.rikshem.se/ledigt/{clean_href}"
                            
                            # Vi snyggar till råtexten så den blir lättläst i ntfy-notisen
                            display_text = clean_line.replace("Umeå - ", "").replace("Umeå", "").strip(" -")
                            
                            # Vi letar efter mönstret med siffror i slutet (t.ex. "3 87 11 229") för att sätta dit rätt enheter
                            match = re.search(r'(\d+)\s+(\d+)\s+(\d+[\s]?\d+)\s+\d{4}-\d{2}-\d{2}', display_text)
                            if match:
                                rooms = match.group(1)
                                size = match.group(2)
                                rent = match.group(3)
                                
                                # Ta bort de råa siffrorna från slutet av adressen och bygg en vacker rad
                                base_address = display_text.split(f" {rooms} {size}")[0].strip()
                                pretty_text = f"Rikshem | {base_address} | {rooms} rum | {size} m² | {rent} kr/mån (Länk: {full_url})"
                            else:
                                pretty_text = f"Rikshem | {display_text} (Länk: {full_url})"
                                
                            todays_apartments.add(pretty_text)
                except Exception:
                    continue

            # --- SKRIVLOGIK MED TOMT-VAKT ---
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(todays_apartments) == 0:
                    f.write("Rikshem | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter hittades efter rensning. Tomt-vakt skriven.")
                else:
                    for apt in sorted(todays_apartments):
                        f.write(apt + "\n")
                    print(f"Hittade {len(todays_apartments)} städade lägenheter live hos Rikshem.")

        except Exception as e:
            print(f"Fel hos Rikshem: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_rikshem()