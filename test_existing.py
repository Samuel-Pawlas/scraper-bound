from importer import SupabaseImporter

imp = SupabaseImporter()
urls = ['https://wearebound.com/products/gift-card', 'https://wearebound.com/products/alpaca-brushed-stripe-sweat']
existing = imp._get_existing_products('scraper-bound', urls[:2])
print('Found', len(existing), 'existing products')
for url, p in existing.items():
    title = p.get('title', 'N/A')
    print(' -', title[:30])