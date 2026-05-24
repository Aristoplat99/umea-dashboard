import os
from playwright.sync_api import sync_playwright

URL = "https://lerstenen.se/bostad/ledigt-just-nu/"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "lerstenen_today.txt")

def scrape_lerstenen():
    print("Kollar Lerstenen Umeå...")
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            response = page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(3000)
            
            if response and response.status in [403, 999]:
                raise Exception(f"Lerstenen blockerar oss! HTTP Status {response.status}")
            
            raw_text = page.locator("body").inner_text()
            
            if "access denied" in raw_text.lower() or "cloudflare" in raw_text.lower():
                raise Exception("Lerstenen blockerar oss! Sidan visar 'Access Denied'.")

            # 1. Hämta ALLA unika lägenhetslänkar i exakt den ordning de visas på skärmen
            # Vi letar efter klassen du hittade: js-open-popup-rental-object
            link_elements = page.locator("a.js-open-popup-rental-object").all()
            actual_links = []
            for l in link_elements:
                href = l.get_attribute("href")
                if href and href not in actual_links:
                    if href.startswith("/"):
                        href = "https://lerstenen.se" + href
                    actual_links.append(href)
            
            print(f"Hittade {len(actual_links)} unika objektslänkar i källkoden.")

            # 2. Strukturera texten i block precis som förut
            lines = raw_text.split('\n')
            apartments_blocks = []
            current_block = []
            
            for line in lines:
                line = line.strip()
                if "Område –" in line:
                    if current_block:
                        apartments_blocks.append(current_block)
                    current_block = [line]
                elif current_block:
                    if "Lerstenen • Storgatan" in line:
                        break
                    current_block.append(line)
            
            if current_block:
                apartments_blocks.append(current_block)

            found_apartments = []

            # 3. Matchar textblocken med rätt länk baserat på deras index (ordning)
            for index, block in enumerate(apartments_blocks):
                clean_lines = []
                for r in block:
                    if r and not any(x in r for x in ["Område –", "Läs mer", "Rum:", "Storlek:", "Våning:", "Hyra:", "Uppsagd till:", "Tillgänglig från:"]):
                        clean_info = r.replace(":-", " kr")
                        clean_info = clean_info.replace("m2", "m²")
                        clean_lines.append(clean_info)

                if len(clean_lines) < 2:
                    continue

                area = clean_lines[0]
                address = clean_lines[1]
                details = " | ".join(clean_lines[2:])
                
                # Plocka länken som har samma placering i listan som textblocket
                specific_url = URL # Fallback
                if index < len(actual_links):
                    specific_url = actual_links[index]

                full_string = f"{area} | {address} | {details} (Länk: {specific_url})"
                found_apartments.append(full_string)

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(unique_apts) == 0:
                    f.write("Lerstenen | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter matchade filtret.")
                else:
                    for apt in unique_apts:
                        f.write(f"Lerstenen | {apt}\n")
                    print(f"Hittade {len(unique_apts)} lägenheter live hos Lerstenen.")

        except Exception as e:
            print(f"Fel vid Lerstenen-scrape: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_lerstenen()