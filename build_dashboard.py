"""
Orkestrator för UmeaDashboard.

1. Roterar data/*_today.txt -> data/*_yesterday.txt (så "NY"-flaggan
   i HTML:en speglar diff sedan förra körningen)
2. Kör alla scrapers/*.py som subprocess
3. Kör generate_html.py för att producera ny index.html

Avbryts inte om enskild scraper failar - vi vill ha så fräsch
data som möjligt i resten av appen.
"""
import glob
import os
import shutil
import subprocess
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRAPERS_DIR = os.path.join(ROOT, "scrapers")
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def rotate_yesterday():
    """Spara förra körningens output som _yesterday innan vi skriver nytt."""
    for today_path in glob.glob(os.path.join(DATA_DIR, "*_today.txt")):
        name = os.path.basename(today_path).replace("_today.txt", "")
        yesterday_path = os.path.join(DATA_DIR, f"{name}_yesterday.txt")
        shutil.copy2(today_path, yesterday_path)
        print(f"  rotate: {name}_today.txt -> {name}_yesterday.txt")


def run_scraper(script_path):
    name = os.path.basename(script_path)
    print(f"\n-> {name}")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        if result.returncode != 0:
            print(f"   FEL ({name}):")
            for line in (result.stderr or "").splitlines()[-10:]:
                print(f"     {line}")
            return False
        print("   OK")
        return True
    except subprocess.TimeoutExpired:
        print(f"   TIMEOUT efter 5 minuter")
        return False


def main():
    print("=== Roterar yesterday-filer ===")
    rotate_yesterday()

    print("\n=== Kör scrapers ===")
    scrapers = sorted(glob.glob(os.path.join(SCRAPERS_DIR, "*.py")))
    ok = 0
    fail = 0
    for s in scrapers:
        if os.path.basename(s) == "__init__.py":
            continue
        if run_scraper(s):
            ok += 1
        else:
            fail += 1
    print(f"\nScrapers klara: {ok} OK, {fail} fel")

    print("\n=== Genererar HTML ===")
    gen = subprocess.run(
        [sys.executable, os.path.join(ROOT, "generate_html.py")],
        encoding="utf-8",
    )
    if gen.returncode != 0:
        print("HTML-generering misslyckades")
        sys.exit(1)

    print("\n=== Klar ===")


if __name__ == "__main__":
    main()
