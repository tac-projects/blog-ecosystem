import os
import sys
import json
import time
import random
import argparse
import hashlib
import datetime
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BLOG_CONTENT_DIR = os.path.join(PROJECT_DIR, 'site/src/content/blog')
IMAGES_DIR = os.path.join(PROJECT_DIR, 'site/public/images')
ENV_FILE = os.path.join(PROJECT_DIR, '.env')

CATEGORIES = ['Comportement', 'Sante & Soins', 'Nutrition', 'Races', 'Mode de vie']

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Do not save files')
args = parser.parse_args()


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
        print(f"Error fetching config from {config_path}: {e}")
        return {}


def deepseek_chat(prompt, model, api_base, temperature=0.8, max_tokens=2000, thinking=None):
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        raise RuntimeError('DEEPSEEK_API_KEY is not set. Add it to the .env file.')

    url = api_base.rstrip('/') + '/chat/completions'

    for i in range(3):
        body = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if thinking is not None:
            body['thinking'] = thinking
        payload = json.dumps(body).encode('utf-8')

        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content'].strip()
            if content:
                return content
            print("Empty content from API (reasoning consumed tokens). Retrying...")
        except Exception as e:
            print(f"API error ({e}). Retrying...")
        if i < 2:
            time.sleep(5 * (2 ** i))
    raise RuntimeError('API returned empty content after retries')


def existing_titles():
    """Read titles of already published posts."""
    titles = []
    try:
        for f in os.listdir(BLOG_CONTENT_DIR):
            if not f.endswith('.md'):
                continue
            with open(os.path.join(BLOG_CONTENT_DIR, f), 'r', encoding='utf-8') as fh:
                content = fh.read(500)
            import re
            m = re.search(r'^title:\s*"?(.+?)"?\s*$', content, re.MULTILINE)
            if m:
                titles.append(m.group(1).strip())
    except FileNotFoundError:
        pass
    return titles


def title_similarity(t1, t2):
    """Jaccard-like similarity on significant words, 0..1."""
    def words(t):
        import re
        return set(re.findall(r'[a-z0-9]{3,}', t.lower()))
    w1, w2 = words(t1), words(t2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def is_duplicate(title, existing, threshold=0.55):
    """True if the title is too close to an existing one."""
    return any(title_similarity(title, t) >= threshold for t in existing)


def generate_topic(niche, tone, language, model, api_base):
    prompt = (
        f"Give me 1 viral blog post title about {niche} in the language '{language}'. "
        f"The tone should be {tone}. Just the title, no quotes."
    )
    return deepseek_chat(prompt, model, api_base, temperature=0.9, max_tokens=1024)


def word_count(text):
    return len(text.split())


def generate_content(title, tone, language, model, api_base, min_words=800, target_words=1200):
    for attempt in range(2):
        prompt = f"""
        Write a {target_words}-word blog post about "{title}".
        Tone: {tone}. Language: {language} (Must be written in {language}).
        Format: Markdown.
        Include h2, h3 headings.
        Do NOT include the title at the start (it will be in frontmatter).
        Do NOT wrap in markdown code blocks.
        IMPORTANT: The article must be at least {min_words} words long.
        """
        content = deepseek_chat(prompt, model, api_base, temperature=0.8, max_tokens=2500)
        words = word_count(content)
        print(f"Content generated ({words} words).")
        if words >= min_words:
            return content
        print(f"Too short ({words} words < {min_words}). Regenerating...")
    raise RuntimeError(f'Content too short after retries ({words} words)')


def review_content(title, content, language, model, api_base):
    """Proofread and improve the content before publishing."""
    prompt = f"""
    You are the editor of a French cat blog. Review the following article
    (title: "{title}") and return ONLY the corrected markdown, no commentary.

    Requirements:
    - Fix spelling and grammar mistakes (language: {language}).
    - Remove repetitive sentences and vague filler.
    - Keep the markdown structure (h2, h3 headings).
    - Keep roughly the same length.
    - Do NOT add a title at the start.
    - Do NOT wrap in markdown code blocks.

    Article:
    {content}
    """
    return deepseek_chat(
        prompt, model, api_base, temperature=0.3, max_tokens=6000, thinking={'type': 'disabled'}
    )


def generate_category(title, model, api_base):
    choices = ', '.join(CATEGORIES)
    prompt = (
        f'Classify the blog post title "{title}" into exactly one category. '
        f'Pick from: {choices}. Reply with only the category name, nothing else.'
    )
    category = deepseek_chat(prompt, model, api_base, temperature=0.2, max_tokens=1024).strip()
    return category if category in CATEGORIES else 'Mode de vie'


def strip_emojis(text):
    """Remove emoji and non-printable characters."""
    return ''.join(c for c in text if c.isprintable() and ord(c) < 0x1F000 or c in 'éèêëàâäîïôöùûüçÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ')


def slugify(title):
    import unicodedata
    title = strip_emojis(title)
    norm = unicodedata.normalize('NFKD', title)
    ascii_only = ''.join(c for c in norm if not unicodedata.combining(c))
    slug = ascii_only.lower().replace(' ', '-').replace(':', '').replace('?', '')
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    slug = '-'.join([s for s in slug.split('-') if s])
    return slug[:50] or 'post'


def palette_for(seed_text):
    palettes = [
        ('#C0673C', '#8A4222', '#2D2320'),
        ('#B5651D', '#C88A5A', '#40352F'),
        ('#A0522D', '#D4A574', '#2D2320'),
        ('#C67B5C', '#E8DFD2', '#6B5D55'),
        ('#B5651D', '#F5EEE4', '#40352F'),
        ('#8A4222', '#C0673C', '#2D2320'),
    ]
    idx = int(hashlib.md5(seed_text.encode('utf-8')).hexdigest(), 16) % len(palettes)
    return palettes[idx]


def generate_svg(title, niche):
    c1, c2, bg = palette_for(title + niche)
    safe_title = title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#g)"/>
  <circle cx="1050" cy="90" r="220" fill="{bg}" opacity="0.35"/>
  <circle cx="140" cy="560" r="260" fill="{bg}" opacity="0.25"/>
  <text x="70" y="220" font-family="Georgia, serif" font-size="40" fill="#ffffff" opacity="0.85">{niche}</text>
  <text x="70" y="340" font-family="Georgia, serif" font-size="58" font-weight="bold" fill="#ffffff">{safe_title}</text>
</svg>"""
    filename = slugify(title) + '.svg'
    filepath = os.path.join(IMAGES_DIR, filename)
    if not args.dry_run:
        os.makedirs(IMAGES_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(svg)
        print(f"Saved image: {filepath}")
    return f"/images/{filename}"


def save_post(title, content, hero_image, category):
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = os.path.join(BLOG_CONTENT_DIR, filename)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    frontmatter = f"""---
title: "{title}"
description: "Un article pour tous les amoureux des chats : {title}."
pubDate: '{date_str}'
category: '{category}'
heroImage: '{hero_image}'
---

{content}
"""

    if args.dry_run:
        print(f"--- DRY RUN: Would save to {filepath} ---")
        print(frontmatter[:200] + "...")
    else:
        os.makedirs(BLOG_CONTENT_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
        print(f"Saved post: {filepath}")


def main():
    load_env()
    print("Starting AutoBlog Engine...")
    config = get_config()

    niche = config.get('niche', 'Technology')
    tone = config.get('tone', 'Expert')
    language = config.get('language', 'English')
    model = config.get('model', 'deepseek-chat')
    api_base = config.get('apiBase', 'https://api.deepseek.com')

    print(f"Configuration: Niche={niche}, Tone={tone}, Model={model}")

    if not config.get('automationActive', True):
        print("Automation is disabled. Skipping generation.")
        return

    existing = existing_titles()
    print(f"Existing articles: {len(existing)}")

    try:
        # 1. Title with deduplication (up to 5 attempts)
        title = None
        for attempt in range(5):
            candidate = generate_topic(niche, tone, language, model, api_base)
            if not is_duplicate(candidate, existing):
                title = candidate
                break
            print(f"Title too close to an existing article ({candidate!r}). Retrying...")
        if title is None:
            raise RuntimeError('Could not generate a unique title after retries')
        title = strip_emojis(title).strip()
        print(f"Generated Title: {title}")

        # 2. Content with length check + editorial review
        content = generate_content(title, tone, language, model, api_base)
        reviewed = review_content(title, content, language, model, api_base)
        print(f"Content reviewed ({word_count(reviewed)} words).")

        category = generate_category(title, model, api_base)
        print(f"Category: {category}")

        hero_image = generate_svg(title, niche)
        print(f"Generated image: {hero_image}")

        save_post(title, reviewed, hero_image, category)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
