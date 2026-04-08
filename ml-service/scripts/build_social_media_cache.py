from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import _load_cached_or_build


if __name__ == '__main__':
    payload = _load_cached_or_build()
    out = ROOT / 'artifacts' / 'social_media_analytics_cache.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Wrote social media analytics cache: {out}')
