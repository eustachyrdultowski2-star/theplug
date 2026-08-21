# The Plug

A search engine for clothes people spot in TikToks and reels. Paste a link and it
reads the comments to work out which brand each piece is; or search a catalogue of
548 underground and mainstream brands.

## What's in here

| | |
|---|---|
| `index.html` | the whole front end (vanilla, no build step) |
| `server.py` | dev server + API (`/api/detect`, `/api/image`, `/api/watch`, …) |
| `brand_detect.py` | reads captions and comment threads, works out the brands |
| `image_search.py` | reverse image search through Google Lens |
| `assets/js/catalog.js` | generated catalogue: 548 brands, 2100+ products |

## Running it

    py -m pip install pillow          # only needed for shrink_photos.py
    copy .env.example .env            # then paste your Apify token
    py server.py                      # http://localhost:4190

## Building the site

    py build_site.py                  # -> dist/, ready to deploy

Set `PLUG_API` first if the API lives on another host:

    set PLUG_API=https://your-api.onrender.com && py build_site.py

## Rebuilding the catalogue

    py import_brands.py               # spreadsheet -> shops -> products
    py scrape_sites.py                # non-Shopify shops
    py guess_sites.py                 # brands with no url in the sheet
    py build_app_data.py              # -> assets/js/catalog.js

## Notes

`.env`, `data/`, scraped contacts and generated emails are deliberately not
committed. See `.gitignore`.
