import os
import re
from playwright.sync_api import sync_playwright

URL = "https://www.lansa.se/lediga-lagenheter/"
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "lansa_today.txt")

def scrape_lansa():
    print("Kollar Lansa Fastigheter Umeå...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        
        try:
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            
            try:
                page.wait_for_selector("select.homeq", timeout=5000)
                page.select_option("select.homeq", value="Umeå")
                print("Valde Umeå i rullistan!")
                page.wait_for_timeout(4000)
            except Exception as select_error:
                print(f"Rullistan strulade, men vi försöker skrapa ändå: {select_error}")

            todays_apartments = set()
            
            links = page.locator("a[href*='homeq.se/lagenhet/']").all()
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                        
                    id_match = re.search(r'/lagenhet/(\d+)', href)
                    apt_id = id_match.group(1) if id_match else "OkäntID"

                    # Normalisera länk (kan vara protokoll-relativ eller relativ)
                    full_href = href
                    if full_href.startswith("//"):
                        full_href = "https:" + full_href
                    elif full_href.startswith("/"):
                        full_href = "https://www.homeq.se" + full_href

                    # Kapa tracking-parametrar (ht_position m.fl. ändras och ger falska diffar)
                    full_href = full_href.split("?")[0]
                    
                    card_text = link.inner_text().replace("\n", " ").strip()
                    clean_text = re.sub(r'\s+', ' ', card_text).strip()
                    
                    if "umeå" in clean_text.lower():
                        # Hyra (skrivs inte alltid ut av Lansa)
                        price = ""
                        price_match = re.search(r'(\d[\d\s]*kr/mån)', clean_text)
                        if price_match:
                            price = re.sub(r'\s+', ' ', price_match.group(1)).strip()

                        # Rum/storlek, t.ex. "2 rum • 40m²"
                        details = ""
                        details_match = re.search(r'(\d+\s*rum\s*•\s*\d+m²|\d+\s*R\.o\.K\.)', clean_text)
                        if details_match:
                            details = details_match.group(1)

                        # Inflyttningsdatum
                        inflytt = ""
                        inflytt_match = re.search(r'Inflytt:\s*([\d-]+)', clean_text)
                        if inflytt_match:
                            inflytt = f"Inflytt: {inflytt_match.group(1)}"

                        tags = "👨 Senior" if "senior" in clean_text.lower() else ""

                        # Isolera adressen: ta bort detaljer, hyra och inflytt ur texten
                        adress = clean_text
                        for chunk in (details, price, "kr/mån"):
                            if chunk:
                                adress = adress.replace(chunk, " ")
                        adress = re.sub(r'Inflytt:\s*[\d-]+', ' ', adress)
                        adress = re.sub(r'[•·]', ' ', adress)
                        adress = re.sub(r'\s+', ' ', adress).strip()

                        # Bygg raden av endast ifyllda fält
                        parts = [f"Lansa | {adress}" if adress else "Lansa | Lägenhet"]
                        if details:
                            parts.append(details)
                        if price:
                            parts.append(price)
                        if inflytt:
                            parts.append(inflytt)
                        if tags:
                            parts.append(tags)
                        parts.append(f"Länk: {full_href}")

                        todays_apartments.add(" | ".join(parts))
                        
                except Exception as card_error:
                    continue

            # --- ÄNDRAD SKRIVLOGIK UTAN LÄNKAR MEN MED TOMT-VAKT ---
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(todays_apartments) == 0:
                    f.write("Lansa | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter hos Lansa just nu. Tomt-vakt skriven till filen.")
                else:
                    for apt in sorted(todays_apartments):
                        f.write(apt + "\n")
                    print(f"Hittade {len(todays_apartments)} lägenheter live hos Lansa i Umeå.")
            
        except Exception as e:
            print(f"Fel hos Lansa: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_lansa()