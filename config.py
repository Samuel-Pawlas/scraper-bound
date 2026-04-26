import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://yqawmzggcgpeyaaynrjk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlxYXdtemdnY2dwZXlhYXlucmprIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTAxMDkyNiwiZXhwIjoyMDcwNTg2OTI2fQ.XtLpxausFriraFJeX27ZzsdQsFv3uQKXBBggoz6P4D4")

BASE_URL = "https://wearebound.com"
COLLECTIONS_URL = "https://wearebound.com/collections/all"

SOURCE = "scraper-bound"
BRAND = "Bound"

EMBEDDING_MODEL = "google/siglip-base-patch16-384"
EMBEDDING_DIM = 768

PAGINATION_START = 1
PAGINATION_END = None  # Will auto-detect

REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 1.0

CSV_OUTPUT = "products.csv"
JSON_OUTPUT = "products.json"