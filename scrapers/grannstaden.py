import os
import json
from playwright.sync_api import sync_playwright

URL = "https://minasidor.grannstaden.se/ledigt/lagenhet"

current_dir = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(current_dir, "..", "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "grannstaden_today.txt")

def scrape_grannstaden():
    print("Kollar Grannstaden Umeå...")
    os.makedirs(DATA_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            api_data = []

            def handle_response(response):
                if "Listapartment" in response.url:
                    try:
                        api_data.append(response.json())
                    except Exception:
                        pass

            page.on("response", handle_response)

            response = page.goto(URL, wait_until="networkidle")

            if response and response.status in [403, 999]:
                raise Exception(f"Grannstaden blockerar oss! HTTP {response.status}")

            page.wait_for_timeout(3000)

            if not api_data:
                raise Exception("Inget API-svar från Grannstaden — sidan kan ha ändrats.")

            # data['data'] är en inbäddad JSON-sträng
            raw = api_data[0].get("data", "[]")
            items = json.loads(raw) if isinstance(raw, str) else raw

            print(f"Hämtade {len(items)} lägenheter totalt. Filtrerar för Umeå...")

            found_apartments = []

            for item in items:
                city = item.get("Adress3", "").strip()
                if city.lower() != "umeå":
                    continue

                address    = item.get("Adress1", "").strip()
                rent       = item.get("Cost", "")
                size       = item.get("Size", "")
                rooms      = item.get("ObjectTypeName", "").strip()
                available  = (item.get("AvailableDate") or "")[:10]  # YYYY-MM-DD
                detail_url = item.get("DetailsUrl", "")
                if detail_url.startswith("/"):
                    detail_url = "https://minasidor.grannstaden.se" + detail_url

                parts = [f"Grannstaden | {address}, {city}"]
                if rent:
                    parts.append(f"{rent} kr/mån")
                if size:
                    parts.append(f"{size} m²")
                if rooms:
                    parts.append(rooms)
                if available:
                    parts.append(f"Tillgänglig: {available}")
                parts.append(f"Länk: {detail_url or URL}")

                found_apartments.append(" | ".join(parts))

            unique_apts = sorted(set(found_apartments))

            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                if not unique_apts:
                    f.write("Grannstaden | Inga lediga lagenheter just nu\n")
                    print("Inga lediga lägenheter i Umeå hos Grannstaden just nu.")
                else:
                    for apt in unique_apts:
                        f.write(f"{apt}\n")
                    print(f"Hittade {len(unique_apts)} lägenheter i Umeå hos Grannstaden.")

        except Exception as e:
            print(f"Fel vid Grannstaden-scrape: {e}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_grannstaden()
