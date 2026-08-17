import os
import sys
import re
import json
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BLOG_CONTENT_DIR = os.path.join(PROJECT_DIR, 'site/src/content/blog')
FB_CARDS_DIR = os.path.join(PROJECT_DIR, 'site/public/fb-cards')
STATE_FILE = os.path.join(PROJECT_DIR, '.fb_state.json')
ENV_FILE = os.path.join(PROJECT_DIR, '.env')
GRAPH_VERSION = 'v26.0'


def load_env():
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())


def get_config():
    config_path = os.path.join(PROJECT_DIR, 'blog_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[facebook] Error reading config: {e}")
        return {}


def read_articles():
    """Return {slug, title, description} for every post in the blog content dir."""
    articles = []
    for f in sorted(os.listdir(BLOG_CONTENT_DIR)):
        if not f.endswith('.md'):
            continue
        slug = f[:-3]
        with open(os.path.join(BLOG_CONTENT_DIR, f), 'r', encoding='utf-8') as fh:
            head = fh.read(1200)
        title = re.search(r'^title:\s*"?(.+?)"?\s*$', head, re.MULTILINE)
        desc = re.search(r'^description:\s*"?(.+?)"?\s*$', head, re.MULTILINE)
        if title:
            articles.append({
                'slug': slug,
                'title': title.group(1).strip().strip('"'),
                'description': desc.group(1).strip().strip('"') if desc else '',
            })
    return articles


def load_state():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return set(data.get('posted', []))
    except Exception:
        return set()


def save_state(posted):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'posted': sorted(posted)}, f, ensure_ascii=False, indent=2)
        f.write('\n')


def publish_post(article, token, page_id, site_url):
    """Publie une photo native (carte FB) avec le lien de l'article dans le texte.

    Retourne True si le post est publié (ou si la carte n'existe pas et que le
    post-lien de secours fonctionne).
    """
    link = f"{site_url.rstrip('/')}/blog/{article['slug']}"
    message = (
        f"🐾 L'article du jour 🐾\n\n"
        f"« {article['title']} »\n\n"
        f"{article['description']}\n\n"
        f"Vous avez un chat ? Vous ne voudrez pas manquer ça !\n"
        f"👉 Lire l'article : {link}"
    )
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/photos"

    card_path = os.path.join(FB_CARDS_DIR, f"{article['slug']}.png")
    if os.path.exists(card_path):
        # Publication native de la photo + lien dans le texte (multipart/form-data)
        boundary = '----fbCardBoundary7MA4YWxkTrZu0gW'
        with open(card_path, 'rb') as f:
            image_bytes = f.read()

        parts = []
        parts.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="message"\r\n\r\n'
            f"{message}\r\n"
        )
        parts.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="url"\r\n\r\n'
            f"{link}\r\n"
        )
        parts.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="access_token"\r\n\r\n'
            f"{token}\r\n"
        )
        parts.append(
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="source"; filename="card.png"\r\n'
            'Content-Type: image/png\r\n\r\n'
        )
        body = ''.join(parts).encode('utf-8') + image_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            print(f"[facebook] Published card '{article['title']}' -> {payload.get('id') or payload.get('post_id')}")
            return True
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode('utf-8'))
                err = err_body.get('error', {}).get('message', e.reason)
            except Exception:
                err = e.reason
            print(f"[facebook] ERROR card post '{article['title']}': {err}")
            # Fallback : post-lien classique
        except Exception as e:
            print(f"[facebook] ERROR card post '{article['title']}': {e}")

    # Fallback : post-lien classique (comportement historique)
    data = urllib.parse.urlencode({
        'message': message,
        'link': link,
        'access_token': token,
    }).encode('utf-8')
    feed_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed"
    req = urllib.request.Request(feed_url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        print(f"[facebook] Published link '{article['title']}' -> {payload.get('id') or payload.get('post_id')}")
        return True
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode('utf-8'))
            err = body.get('error', {}).get('message', e.reason)
        except Exception:
            err = e.reason
        print(f"[facebook] ERROR posting '{article['title']}': {err}")
    except Exception as e:
        print(f"[facebook] ERROR posting '{article['title']}': {e}")
    return False


def main():
    load_env()
    config = get_config()

    if not config.get('facebookEnabled', False):
        print("[facebook] Disabled (facebookEnabled=false). Skipping.")
        return

    page_id = config.get('facebookPageId')
    site_url = config.get('siteUrl')
    token = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN', '')

    if not page_id or not token:
        print("[facebook] WARNING: facebookEnabled=true but facebookPageId or "
              "FACEBOOK_PAGE_ACCESS_TOKEN is missing. Skipping.")
        return
    if not site_url:
        print("[facebook] WARNING: siteUrl missing in blog_config.json. Skipping.")
        return

    posted = load_state()
    new_articles = [a for a in read_articles() if a['slug'] not in posted]
    if not new_articles:
        print("[facebook] No new article to publish.")
        return

    for article in new_articles:
        if publish_post(article, token, page_id, site_url):
            posted.add(article['slug'])
    save_state(posted)


if __name__ == "__main__":
    main()
