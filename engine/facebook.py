import os
import sys
import re
import json
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BLOG_CONTENT_DIR = os.path.join(PROJECT_DIR, 'site/src/content/blog')
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
    link = f"{site_url.rstrip('/')}/blog/{article['slug']}"
    message = (
        f"Nouvel article : {article['title']}\n\n"
        f"{article['description']}\n\n"
        f"Lire l'article : {link}"
    )
    data = urllib.parse.urlencode({
        'message': message,
        'link': link,
        'access_token': token,
    }).encode('utf-8')
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/feed"

    req = urllib.request.Request(url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        print(f"[facebook] Published '{article['title']}' -> {payload.get('id') or payload.get('post_id')}")
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
