# Bound Scraper

Automated scraper for Bound fashion store (https://wearebound.com/)

## Features

- Scrapes all products from Bound's collection
- Extracts product details: title, price, category, gender, sizes, images
- Generates 768-dim SigLIP embeddings for images (google/siglip-base-patch16-384)
- Generates text embeddings for product info
- Imports to Supabase database

## Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Scrape all products
python main.py

# Scrape with limit
python main.py --limit 50

# Skip cache
python main.py --no-cache

# Incremental update (only new products)
python main.py --incremental
```

## Environment Variables

Create a `.env` file:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

## Automated Schedule

The scraper runs automatically via GitHub Actions:
- Wednesday 3:00 PM
- Friday 3:00 PM

You can also trigger manually from GitHub Actions tab.

## Project Structure

```
scraper-bound/
├── config.py          # Configuration
├── scraper.py        # Product listing extractor
├── product_scraper.py # Product detail extractor
├── embeddings.py     # SigLIP embeddings
├── importer.py       # Supabase import
├── main.py           # Main orchestrator
├── .env              # Environment variables
└── .github/
    └── workflows/
        └── scrape.yml # GitHub Actions
```