import os
import re
from playwright.sync_api import sync_playwright

# SÄKER DOTENV-LADDNING: Fungerar lokalt men kraschar inte på GitHub
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

URL = "https://upm.unit4cloud.com/FN667500P/tenant/login"
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "balticgruppen_today.txt")

USER = os.environ.get("BALTIC_USER")
PASS = os.environ.get("BALTIC_PASS")

def scrape_baltic():
    if not USER or not PASS:
        raise EnvironmentError("BALTIC_USER eller BALTIC_PASS saknas i miljövariablerna.")

    print("Kollar Balticgruppen...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        try:
            page.goto(URL, wait_until="networkidle")
            
            # Logga in
            page.wait_for_selector("#login-userName", state="visible")
            page.fill("#login-userName", USER)
            page.fill("#login-password", PASS)
            page.click('button[type="submit"]')
            
            # Vänta ordentligt på att Mina Sidor laddas in helt
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(6000) 
            
            todays_apartments = set()
            
            # Vi letar efter lägenhetskorten via klassen du hittade (.media-body)
            cards = page.locator(".media-body").all()
            
            for card in cards:
                try:
                    # 1. Hämta adressen från fn-address-display
                    address_el = card.locator("fn-address-display address")
                    if address_el.count() == 0:
                        continue
                    address_text = address_el.inner_text().replace("\n", " ").strip()
                    address_text = re.sub(r'\s+', ' ', address_text).strip(" ,")
                    
                    # 2. Hämta alla etiketter (Hyra, m², Rum)
                    labels = card.locator("span.label").all_inner_texts()
                    
                    rent = "N/A"
                    size = "N/A"
                    rooms = "N/A"
                    
                    for label in labels:
                        clean_label = label.replace("\xa0", " ").strip()
                        if "Hyra/mån" in clean_label:
                            rent = clean_label.replace("Hyra/mån:", "").strip()
                        elif "m²" in clean_label:
                            size = clean_label.strip()
                        elif "rum och kök" in clean_label or "ROK" in clean_label:
                            rooms = clean_label.replace(" och kök", "").replace(" rum", "r").strip()

                    pretty_text = f"Baltic | {address_text} | {rooms} | {size} | {rent}"
                    todays_apartments.add(pretty_text)
                except Exception:
                    continue

            # --- SKRIVLOGIK MED TOMT-VAKT ---
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(todays_apartments) == 0:
                    page_content = page.locator("body").inner_text()
                    if "Inga lediga lägenheter finns tillgängliga" in page_content:
                        f.write("Balticgruppen | Inga lediga lagenheter just nu\n")
                        print("Inga nya lägenheter hos Baltic (Tomt-vakt skriven).")
                    else:
                        f.write("⚠️ Balticgruppen | Sidan har ändrats! Möjlig ledig lägenhet på Mina Sidor.\n")
                        print("⚠️ Sidan ändrad men kunde inte tolka korten. Fallback skriven.")
                else:
                    for apt in sorted(todays_apartments):
                        f.write(apt + "\n")
                    print(f"Hittade {len(todays_apartments)} lägenheter live hos Balticgruppen!")

        except Exception as e:
            print(f"Fel hos Baltic: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_baltic()