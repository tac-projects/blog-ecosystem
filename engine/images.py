import os
import json
import hashlib
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
IMAGES_DIR = os.path.join(PROJECT_DIR, 'site/public/images')
STATE_FILE = os.path.join(PROJECT_DIR, '.pexels_state.json')
PEXELS_SEARCH_URL = 'https://api.pexels.com/v1/search'
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'


def pexels_key():
    return os.environ.get('PEXELS_API_KEY', '')


def _load_state():
    """Return dict slug -> pexels photo id already used."""
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')


def _md5(data):
    return hashlib.md5(data).hexdigest()


def _existing_hashes():
    """md5 of every image already on disk, to catch duplicates not in state."""
    hashes = {}
    try:
        for f in os.listdir(IMAGES_DIR):
            if f.endswith(('.jpg', '.jpeg', '.png')):
                p = os.path.join(IMAGES_DIR, f)
                try:
                    with open(p, 'rb') as fh:
                        hashes[_md5(fh.read())] = p
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return hashes


def _image_query(title, category, niche, model, api_base):
    """DeepSeek translates the article subject into an English Pexels search query."""
    prompt = (
        f"Article subject about {niche} (cats, the animals): \"{title}\" "
        f"(category: {category}). "
        "Give one short English image-search query (3-6 words, no quotes) that would find "
        "a great free stock photo for this article. Reply with the query only."
    )
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
        'max_tokens': 1024,
        'thinking': {'type': 'disabled'},
    }).encode('utf-8')
    req = urllib.request.Request(
        api_base.rstrip('/') + '/chat/completions', data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f"Bearer {os.environ.get('DEEPSEEK_API_KEY', '')}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data['choices'][0]['message']['content'].strip()


def _pexels_search(query, per_page=8):
    url = PEXELS_SEARCH_URL + '?' + urllib.parse.urlencode({
        'query': query, 'per_page': per_page, 'orientation': 'landscape', 'size': 'large'})
    req = urllib.request.Request(url, headers={'Authorization': pexels_key(), 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _crop_url(original):
    return original.replace('?auto=compress', '') + '?auto=compress&cs=tinysrgb&w=1200&h=630&fit=crop'


def _download_bytes(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _pick_photo(photos, used_ids, existing_hashes):
    """First photo not already used (by pexels id or md5). Returns (photo, data)."""
    for photo in photos:
        pid = str(photo.get('id'))
        if pid in used_ids:
            continue
        try:
            data = _download_bytes(_crop_url(photo['src']['original']))
        except Exception as e:
            print(f"Image: download failed for photo {pid} ({e}).")
            continue
        if _md5(data) in existing_hashes:
            print(f"Image: photo {pid} already used on disk, skipping.")
            continue
        return photo, data
    return None, None


def generate_photo(title, category, niche, model, api_base, dry_run=False):
    """Fetch a real Pexels photo matching the article, avoiding duplicates.
    Returns /images/{slug}.jpg or None."""
    slug = _slugify(title)
    filename = f"{slug}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)

    state = _load_state()
    used_ids = set(state.values())
    existing_hashes = _existing_hashes()

    queries = []
    try:
        queries.append(_image_query(title, category, niche, model, api_base))
    except Exception as e:
        print(f"Image: query generation failed ({e}); using fallback keywords.")

    queries += [
        f"cat {category.split(' ')[0].lower()}",
        'cute cat',
    ]

    for q in queries:
        try:
            result = _pexels_search(q)
            photos = result.get('photos', [])
            if not photos:
                print(f"Image: no results for '{q}'.")
                continue
            if dry_run:
                print(f"Image (dry-run): would pick a photo for {filename} from '{q}'")
                return None
            photo, data = _pick_photo(photos, used_ids, existing_hashes)
            if photo is None:
                print(f"Image: all photos for '{q}' already used, trying next query.")
                continue
            os.makedirs(IMAGES_DIR, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(data)
            state[slug] = str(photo['id'])
            _save_state(state)
            print(f"Image: saved {filepath} ({len(data)} bytes, photo {photo['id']}) from query '{q}'")
            return f"/images/{filename}"
        except Exception as e:
            print(f"Image: Pexels failed for '{q}' ({e}).")
    return None


def _slugify(title):
    import unicodedata
    norm = unicodedata.normalize('NFKD', title)
    ascii_only = ''.join(c for c in norm if not unicodedata.combining(c))
    slug = ascii_only.lower().replace(' ', '-').replace(':', '').replace('?', '')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    slug = '-'.join([s for s in slug.split('-') if s])
    return slug[:50] or 'post'
