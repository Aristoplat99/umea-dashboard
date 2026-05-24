import os
from playwright.sync_api import sync_playwright

URL = "https://heimstaden.com/se/sok-lagenhet/?text=Ume%C3%A5%2C+Sweden&number_of_rooms_min=1&number_of_rooms_max=10&rent_min=0&rent_max=26000&size_min=0&size_max=300&search_version=1.5&came_from_lsc_link=0&order=&map_center=63.818835,20.3234065&map_zoom=13.593227379835227&object_type=apartments&tracking_object_type=Apartment&google_place_id=ChIJ-detaBtOfEYRYIWM3gZFAwQ&google_place_type=locality&google_place_name=Ume%C3%A5"

def scrape_heimstaden():
    print("Kollar Heimstaden Umeå...", flush=True)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    today_file = os.path.join(data_dir, "heimstaden_today.txt")
    
    found_apartments = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(4000)
            
            try:
                page.click("button:has-text('Neka alla')", timeout=3000)
            except:
                pass

            page.wait_for_selector("body")
            cards = page.query_selector_all(".object-card__info")
            
            for card in cards:
                try:
                    # Gå upp till föräldern som är a-taggen
                    parent = card.evaluate_handle("node => node.parentElement")
                    
                    # Hämta href-attributet direkt från den element-referensen
                    link = parent.as_element().get_attribute("href")
                    
                    addr_el = card.query_selector(".object-card__address")
                    loc_el = card.query_selector(".object-card__location")
                    prize_el = card.query_selector(".object-card__data-prize")
                    size_el = card.query_selector(".object-card__data-size")
                    
                    if addr_el and loc_el and prize_el and size_el:
                        address = addr_el.inner_text().strip()
                        location = loc_el.inner_text().strip()
                        prize = prize_el.inner_text().strip()
                        size = size_el.inner_text().strip()
                        
                        if "Umeå" in location:
                            # Säkra att länken är absolut
                            full_link = link if link.startswith("http") else "https://heimstaden.com" + link
                            entry = f"Heimstaden | {address} | {size} | {prize} | Länk: {full_link}"
                            found_apartments.append(entry)
                except Exception:
                    continue 

        except Exception as e:
            print(f"Fel vid skrapning: {e}")
            raise e
        finally:
            browser.close()
            
    with open(today_file, "w", encoding="utf-8") as f:
        for apt in sorted(found_apartments):
            f.write(f"{apt}\n")
            
    print(f"Heimstaden klart. Sparade {len(found_apartments)} lägenheter i Umeå.", flush=True)

if __name__ == "__main__":
    scrape_heimstaden()