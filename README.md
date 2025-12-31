# -Files-Downloader
On December 22, 2025, The United States Department of Justice accidentally released/made live the URL for Data Set 8 of the released Jeffrey Epstein files, leaking over 11,000 files ahead of schedule. 

Data Set 8 wasn't visible from the main ``` https://www.justice.gov/epstein/doj-disclosures ``` page, and was only accessible by modifying the existing Data Set 7 URL to ``` https://www.justice.gov/epstein/doj-disclosures/data-set-8-files ```.

The DOJ attempted to remedy this issue by removing access to the button that allowed you to mass download Data Set 8 to a singular .zip file, making it impossible to access the files locally, hence allowing the DOJ to make any desired modifications or removals uncontested.

This repository contains a small Python script that remedied that: it automates downloading the publicly posted PDF files from the **DOJ Epstein "Data Set 8"** page on justice.gov into a local folder and then bundles them into a single ZIP file.

It is designed for personal research and archival purposes, using
[Playwright](https://playwright.dev/) to emulate a real browser session so that
the site cookies and access patterns are respected.

> Use this script responsibly. It targets publicly available documents on a
> U.S. government site but you are still responsible for complying with all
> applicable laws, terms of use, and rate-limiting expectations.

> As of December 30, 2025: the DOJ has allowed for mass downloading of Data Set 8, and finally added Data Set 8 to the main ``` https://www.justice.gov/epstein/doj-disclosures ``` page. so the impact of this repository is dimished.
>
> However, slight modifications to this script can be made to work for other existing websites if needed be.
> As well as of December 30th, with the current administration calling for the release of more files, the possibility that this script could be used again in the near future is evident.

---

## What the Script Does

- Opens the DOJ **Data Set 8** listings using Playwright.
- Iterates over a configurable range of listing pages (e.g. `?page=40` to `?page=120`).
- Collects unique `.pdf` filenames from the listing pages.
- Downloads each PDF via the same Playwright browser context (so cookies/session are shared).
- Retries downloads with backoff on HTTP errors (including 401s).
- Writes all successfully downloaded PDFs into a local directory.
- Creates a compressed `.zip` archive of the downloaded PDFs.
- Records any permanently failed filenames in `failed.txt`.

The default constants (page range, output directory, zip name, etc.) are set
near the top of `epstein_downloader.py` and can be adjusted as needed.

---

## Requirements

- Python 3.10+ (or any modern 3.x version supported by Playwright)
- [Playwright](https://playwright.dev/python/)

Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```
> ```playwright install``` downloads the browser binaries (e.g. Chromium) that Playwright will use.

## Usage
1. Clone the repo:
```
git clone https://github.com/AnotherAnotherAustin/-Files-Downloader.git
cd -Files-Downloader
```
2. Create a virtual environment *(optional but recommended)*:
```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```
3. Install dependencies and Playwright browsers:
```
pip install -r requirements.txt
playwright install
```
4. Run the script:
```
python epstein.py
```
---

In its current default form, the script will:

- Fetch list pages from ```https://www.justice.gov/epstein/doj-disclosures/data-set-8-files``` for a range of *?page=* values.
- Download PDFs into the **dataset8_pdfs/** directory *(created if needed)*.
- Write a ZIP archive like ***dataset8_pages_40-120.zip*** in the current directory.
- Write any permanent failures to *failed.txt*.


## Configuration

At the top of epstein_downloader.py you can adjust:
```
PAGES      = range(40, 120)  # List pages to scrape
LIST_URL   = "https://www.justice.gov/epstein/doj-disclosures/data-set-8-files?page={}"
FILE_BASE  = "https://www.justice.gov/epstein/files/DataSet%208/"

OUTDIR     = "dataset8_pdfs"
ZIPNAME    = "dataset8_pages_40-120.zip"
FAILED_TXT = "failed.txt"
```

Other tunable constants:
- BASE_SLEEP / JITTER: base delay and jitter between successful downloads.
- MAX_RETRIES: how many attempts per file.
- RESET_ON_401_STREAK: after this many 401s in a row, the script resets the browser context.
- CONTEXT_ROTATE_EVERY: refreshes the context every N successful downloads.

These are used to behave more politely and robustly when dealing with transient errors or access issues.

## Brief Overview of How It Works
1. Session Setup
The script starts a Playwright Chromium browser and opens a page on the DOJ site to establish cookies/session:
```
context = browser.new_context()
page = context.new_page()
page.goto(LIST_URL.format(0), wait_until="domcontentloaded")
```
2. Collect Filenames
For each page in PAGES, it loads the listing and finds link text that ends with .pdf via a small JavaScript snippet:
```
texts = page.eval_on_selector_all(
    "a",
    "els => els.map(a => (a.innerText||'').trim()).filter(t => t.toLowerCase().endsWith('.pdf'))"
)
```
3. Download Files
PDFs are downloaded using context.request.get(...) with a Referer
header so the request looks like it came from the listing page. The script
retries on errors with exponential-ish backoff and occasionally resets the
context when it sees repeated 401s.
4. Zip and Report
After iterating through all filenames:
- It writes any failures to failed.txt.
- It zips all successfully downloaded PDFs into ZIPNAME.

## Notes / Disclaimers
- This script is for working with publicly listed PDFs on an official U.S. government website. You are responsible for any use of the downloaded content.
- The script is intentionally conservative with delays and context resets to reduce the chance of being blocked or causing undue load.

