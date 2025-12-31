import os, time, zipfile, random
from urllib.parse import quote
from playwright.sync_api import sync_playwright

PAGES = range(42, 121)  # 0..80
LIST_URL = "https://www.justice.gov/epstein/doj-disclosures/data-set-8-files?page={}"
FILE_BASE = "https://www.justice.gov/epstein/files/DataSet%208/"

OUTDIR = "dataset8_pdfs"
ZIPNAME = "dataset8_pages_42-121.zip"
FAILED_TXT = "failed.txt"

os.makedirs(OUTDIR, exist_ok=True)

def make_file_url(filename: str) -> str:
    return FILE_BASE + quote(filename)

def new_context_and_page(browser):
    ctx = browser.new_context()
    pg = ctx.new_page()
    # Touch site once to establish cookies/session
    pg.goto(LIST_URL.format(0), wait_until="domcontentloaded", timeout=60000)
    return ctx, pg

# tuning
BASE_SLEEP = 0.35
JITTER = 0.50
MAX_RETRIES = 6
RESET_ON_401_STREAK = 3
CONTEXT_ROTATE_EVERY = 200

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context, page = new_context_and_page(browser)

    # ----------------------------
    # 1) Collect filenames
    # ----------------------------
    filenames = []
    seen = set()

    for i in PAGES:
        url = LIST_URL.format(i)
        print(f"\n[+] Loading list page {i}: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_selector("a:has-text('.pdf')", timeout=20000)
        except Exception:
            pass

        texts = page.eval_on_selector_all(
            "a",
            """els => els
                .map(a => (a.innerText||'').trim())
                .filter(t => t.toLowerCase().endsWith('.pdf'))
            """
        )

        new_count = 0
        for t in texts:
            if t and t not in seen:
                seen.add(t)
                filenames.append(t)
                new_count += 1

        print(f"    Found {new_count} new filenames (total so far: {len(filenames)})")

    # ----------------------------
    # 2) Download with Playwright request (same session)
    # ----------------------------
    downloaded = []
    failed = []
    success_count = 0
    streak_401 = 0

    for fn in filenames:
        pdf_url = make_file_url(fn)
        outpath = os.path.join(OUTDIR, fn)

        if os.path.exists(outpath) and os.path.getsize(outpath) > 0:
            downloaded.append(outpath)
            continue

        for attempt in range(1, MAX_RETRIES + 1):
            # refresh session if 401s start stacking up
            if streak_401 >= RESET_ON_401_STREAK:
                print(f"[!] {streak_401}x 401 in a row — refreshing context...")
                try:
                    context.close()
                except Exception:
                    pass
                context, page = new_context_and_page(browser)
                streak_401 = 0

            try:
                print(f"[>] Downloading {fn} (attempt {attempt}/{MAX_RETRIES})")
                resp = context.request.get(
                    pdf_url,
                    timeout=60000,
                    headers={"Referer": "https://www.justice.gov/epstein/doj-disclosures/data-set-8-files"}
                )

                if resp.ok:
                    with open(outpath, "wb") as f:
                        f.write(resp.body())

                    downloaded.append(outpath)
                    success_count += 1
                    streak_401 = 0

                    if success_count % CONTEXT_ROTATE_EVERY == 0:
                        print(f"[i] Rotating context after {success_count} successes...")
                        try:
                            context.close()
                        except Exception:
                            pass
                        context, page = new_context_and_page(browser)

                    time.sleep(BASE_SLEEP + random.random() * JITTER)
                    break

                if resp.status == 401:
                    streak_401 += 1
                    backoff = min(120, (2 ** attempt) + random.random() * 5)
                    print(f"[!] 401 for {fn}. Backing off {backoff:.1f}s (streak={streak_401})")
                    time.sleep(backoff)
                    continue

                backoff = min(45, attempt * 3 + random.random() * 3)
                print(f"[!] HTTP {resp.status} for {fn}. Backing off {backoff:.1f}s")
                time.sleep(backoff)

            except Exception as e:
                backoff = min(45, attempt * 3 + random.random() * 3)
                print(f"[!] Exception for {fn}: {e} — sleeping {backoff:.1f}s")
                time.sleep(backoff)

        else:
            print(f"[X] Giving up on {fn}")
            failed.append(fn)

    if failed:
        with open(FAILED_TXT, "w", encoding="utf-8") as f:
            f.write("\n".join(failed))
        print(f"[!] Wrote {len(failed)} failures to {FAILED_TXT}")

    # ----------------------------
    # 3) Zip them (still inside with-block is fine)
    # ----------------------------
    print(f"\n[+] Zipping {len(downloaded)} PDFs into {ZIPNAME}")
    with zipfile.ZipFile(ZIPNAME, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for pth in downloaded:
            if os.path.exists(pth) and os.path.getsize(pth) > 0:
                z.write(pth, arcname=os.path.basename(pth))

    browser.close()

print("[✓] Done.")
