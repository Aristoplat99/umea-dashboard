import os
import re
from playwright.sync_api import sync_playwright

URL = "https://www.riksbyggen.se/bostad/?query=Ume%C3%A5&choice=rent&pagination-p=1"
current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "riksbyggen_today.txt")

def scrape_riksbyggen():
    print("Kollar Riksbyggen Umeå...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        page.set_default_timeout(10000)
        
        try:
            response = page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            try:
                page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll").first.click(timeout=3000)
            except Exception:
                pass

            page.wait_for_selector("text=Månadshyra", timeout=5000)
            
            headings = page.locator("h2").all()
            todays_apartments = set()
            seen_strings_count = {}
            
            for h2 in headings:
                addr_text = h2.inner_text().strip()
                
                if not addr_text or any(word in addr_text.lower() for word in ["filter", "bostad", "meny"]):
                    continue
                
                try:
                    # Hitta kortets container
                    card_container = h2.evaluate_handle("el => el.closest('div').parentElement.parentElement")
                    card_text = page.evaluate("el => el.innerText", card_container)
                    
                    # --- FÖRBÄTTRAD LÄNKJAKT ---
                    # Vi kollar alla möjliga ställen där href kan gömma sig
                    href = page.evaluate("""el => {
                        // 1. Kolla om h2 själv är en länk eller innehåller en länk
                        const h2Link = el.querySelector('h2 a') || (el.tagName === 'A' ? el : null);
                        if (h2Link && h2Link.getAttribute('href')) return h2Link.getAttribute('href');
                        
                        // 2. Kolla om det finns en länk som omsluter h2
                        const parentLink = el.querySelector('h2') ? el.querySelector('h2').closest('a') : null;
                        if (parentLink && parentLink.getAttribute('href')) return parentLink.getAttribute('href');
                        
                        // 3. Ta vilken tillgänglig länk som helst inuti kortet
                        const anyLink = el.querySelector('a');
                        return anyLink ? anyLink.getAttribute('href') : '';
                    }""", card_container)
                    
                    # Om vi inte hittade något inuti container, kolla h2:s omedelbara närhet
                    if not href:
                        href = h2.evaluate("el => { const a = el.closest('a') || el.querySelector('a'); return a ? a.getAttribute('href') : ''; }")
                    # ---------------------------

                    if href:
                        if href.startswith("/"):
                            href = "https://www.riksbyggen.se" + href
                        link_str = f" (Länk: {href})"
                    else:
                        link_str = ""

                    clean_text = card_text.replace("\n", " ").strip()
                    clean_text = re.sub(r'\s+', ' ', clean_text).replace("open_in_new", "").replace("location_on", "").strip()
                    
                    display_text = clean_text.split("Hyresrätter")[0].strip()
                    
                    if "kr/mån" in display_text:
                        seen_strings_count[display_text] = seen_strings_count.get(display_text, 0) + 1
                        instance_id = seen_strings_count[display_text]
                        suffix = f" [Kopia #{instance_id}]" if instance_id > 1 else ""
                        pretty_text = f"Riksbyggen | {display_text}{suffix}{link_str}"
                        todays_apartments.add(pretty_text)
                        
                except Exception as e:
                    continue
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if len(todays_apartments) == 0:
                    f.write("Riksbyggen | Inga lediga lagenheter just nu\n")
                else:
                    for apt in sorted(todays_apartments):
                        f.write(apt + "\n")
                    
            print(f"Hittade {len(todays_apartments)} lägenheter live hos Riksbyggen.")

        except Exception as e:
            print(f"Riksbyggen timeout eller fel: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_riksbyggen()