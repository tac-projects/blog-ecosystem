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

from images import generate_photo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
BLOG_CONTENT_DIR = os.path.join(PROJECT_DIR, 'site/src/content/blog')
IMAGES_DIR = os.path.join(PROJECT_DIR, 'site/public/images')
ENV_FILE = os.path.join(PROJECT_DIR, '.env')

CATEGORIES = ['Comportement', 'Sante & Soins', 'Nutrition', 'Races', 'Mode de vie', 'Adoption']

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Do not save files')
parser.add_argument('--count', type=int, default=1, help='Number of articles to generate')
parser.add_argument('--days', type=int, default=0, help='Spread pubDate over N past days (0 = today)')
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


def build_prompt(config, path, **kwargs):
    """Récupère un template de prompt depuis blog_config.json et y injecte les valeurs.

    path est une clé dot-notée, ex: 'prompts.topic.audience'.
    """
    node = config
    for part in path.split('.'):
        node = node.get(part, '') if isinstance(node, dict) else ''
    template = node if isinstance(node, str) else ''
    for k, v in kwargs.items():
        template = template.replace('{' + k + '}', str(v))
    return template


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
    """Read (title, category) of already published posts."""
    posts = []
    try:
        for f in os.listdir(BLOG_CONTENT_DIR):
            if not f.endswith('.md'):
                continue
            with open(os.path.join(BLOG_CONTENT_DIR, f), 'r', encoding='utf-8') as fh:
                content = fh.read(600)
            import re
            title = re.search(r'^title:\s*"?(.+?)"?\s*$', content, re.MULTILINE)
            cat = re.search(r'^category:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
            if title:
                posts.append((title.group(1).strip(), cat.group(1).strip() if cat else ''))
    except FileNotFoundError:
        pass
    return posts


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


def is_semantic_duplicate(title, category, existing_titles, model, api_base):
    """Ask the model whether the new title is a duplicate SUBJECT of an existing one
    in the same category. More reliable than word similarity."""
    if not existing_titles:
        return False
    listed = '\n'.join(f'- {t}' for t in existing_titles)
    config = get_config()
    prompt = build_prompt(
        config, 'prompts.semantic_duplicate.template',
        category=category, titles=listed, title=title,
    )
    answer = deepseek_chat(prompt, model, api_base, temperature=0.0, max_tokens=2048).lower()
    return answer.strip().startswith('yes')


def generate_topic(niche, tone, language, model, api_base, category=None, avoid_titles=None):
    config = get_config()
    prompt = build_prompt(
        config, 'prompts.topic.intro', niche=niche, language=language, tone=tone,
    )
    prompt += build_prompt(config, 'prompts.topic.audience')
    if category:
        prompt += build_prompt(
            config, 'prompts.topic.category', category=category,
        )
    if avoid_titles:
        prompt += build_prompt(
            config, 'prompts.topic.avoid', titles='; '.join(avoid_titles),
        )
    prompt += build_prompt(config, 'prompts.topic.ending')
    return deepseek_chat(prompt, model, api_base, temperature=0.9, max_tokens=4096)


def word_count(text):
    return len(text.split())


def validate_structure(content, min_sections=3, max_sections=10):
    """Check the article matches the uniform format:
    intro (no heading) + 3-10 '## ' sections (adapted to the subject) + conclusion.

    Returns True if the structure is respected, False otherwise.
    """
    lines = [l.rstrip() for l in content.splitlines()]

    # '###' is forbidden by the format.
    if any(l.startswith('### ') for l in lines):
        return False

    h2_indexes = [i for i, l in enumerate(lines) if l.startswith('## ')]
    if not (min_sections <= len(h2_indexes) <= max_sections):
        return False

    # Intro must exist BEFORE the first h2 (non-empty, no heading).
    intro = '\n'.join(lines[:h2_indexes[0]]).strip()
    if not intro:
        return False

    # Conclusion must exist AFTER the last h2 (non-empty, no heading).
    conclusion = '\n'.join(lines[h2_indexes[-1] + 1:]).strip()
    if not conclusion:
        return False

    return True


def generate_content(title, tone, language, model, api_base, min_words=800, target_words=1200, existing_links=None):
    config = get_config()
    content_cfg = config.get('content', {})
    min_words = content_cfg.get('minWords', min_words)
    target_words = content_cfg.get('targetWords', target_words)
    existing_links = existing_links or []
    link_block = ''
    if existing_links:
        titles_block = '\n'.join(f'        - "{t}" -> /blog/{s}/' for t, s in existing_links)
        link_block = build_prompt(
            config, 'prompts.content.links_intro', titles=titles_block,
        )
    for attempt in range(3):
        prompt = build_prompt(
            config, 'prompts.content.template',
            target_words=target_words, title=title, tone=tone, language=language,
            link_block=link_block, min_words=min_words,
        )
        content = deepseek_chat(
            prompt, model, api_base, temperature=0.8, max_tokens=8000,
            thinking={'type': 'disabled'},
        )
        words = word_count(content)
        print(f"Content generated ({words} words).")
        if words >= min_words and validate_structure(content):
            return content
        if words < min_words:
            print(f"Too short ({words} words < {min_words}). Regenerating...")
        else:
            print("Structure does not match (intro + 3-10 x h2 + conclusion). Regenerating...")
    raise RuntimeError(f'Content failed validation after retries ({words} words)')


def review_content(title, content, language, model, api_base):
    """Proofread and improve the content before publishing."""
    config = get_config()
    prompt = build_prompt(
        config, 'prompts.review.template',
        title=title, language=language, content=content,
    )
    return deepseek_chat(
        prompt, model, api_base, temperature=0.3, max_tokens=6000, thinking={'type': 'disabled'}
    )


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


def strip_leading_duplicate_title(content, title, model=None, api_base=None):
    """Remove a leading '## ' heading that merely repeats the frontmatter title."""
    stripped = content.lstrip()
    if not stripped.startswith('## '):
        return content
    line_end = stripped.find('\n')
    heading = stripped[3:line_end if line_end != -1 else None].strip()
    if is_duplicate(heading, [title], threshold=0.6):
        rest = stripped[line_end + 1:] if line_end != -1 else ''
        return rest.lstrip('\n')
    if model and api_base:
        config = get_config()
        prompt = build_prompt(
            config, 'prompts.strip_duplicate_heading.template',
            title=title, heading=heading,
        )
        answer = deepseek_chat(prompt, model, api_base, temperature=0.0, max_tokens=2048).lower()
        if answer.strip().startswith('yes'):
            rest = stripped[line_end + 1:] if line_end != -1 else ''
            return rest.lstrip('\n')
    return content


def existing_links():
    """Return list of (title, slug) for existing posts, usable for inline links."""
    links = []
    try:
        for f in os.listdir(BLOG_CONTENT_DIR):
            if not f.endswith('.md'):
                continue
            slug = f[:-3]
            with open(os.path.join(BLOG_CONTENT_DIR, f), 'r', encoding='utf-8') as fh:
                content = fh.read(600)
            import re
            title = re.search(r'^title:\s*"?(.+?)"?\s*$', content, re.MULTILINE)
            if title:
                links.append((title.group(1).strip(), slug))
    except FileNotFoundError:
        pass
    return links


def validate_links(content, valid_slugs):
    """Replace /blog/ links in the content that point to unknown slugs (None) or keep valid ones.
    Returns (content, kept_count)."""
    import re
    kept = [0]

    def repl(m):
        slug = m.group(2)
        if slug in valid_slugs:
            kept[0] += 1
            return m.group(0)
        # link to a non-existent article: drop the markdown link, keep the anchor text
        return m.group(1)

    new_content = re.sub(r'\[([^\]]+)\]\(/blog/([^)]+)/\)', repl, content)
    return new_content, kept[0]


def generate_description(title, language, model, api_base):
    """Generate an engaging meta description (2-3 sentences) for the article."""
    config = get_config()
    prompt = build_prompt(
        config, 'prompts.description.template', title=title, language=language,
    )
    desc = deepseek_chat(prompt, model, api_base, temperature=0.7, max_tokens=500).strip().strip('"')
    return desc


def save_post(title, content, hero_image, category, date_str=None, description=None):
    slug = slugify(title)
    filename = f"{slug}.md"
    filepath = os.path.join(BLOG_CONTENT_DIR, filename)
    if date_str is None:
        date_str = datetime.datetime.now().strftime('%Y-%m-%d')

    content = strip_leading_duplicate_title(
        content, title, model=args.model, api_base=args.api_base
    )

    content = strip_leading_duplicate_title(content, title)

    if not description:
        description = f"Un article pour tous les amoureux des chats : {title}."

    frontmatter = f"""---
title: "{title}"
description: "{description}"
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

    count = args.count
    days = args.days
    print(f"Generating {count} article(s), dates spread over {days} day(s)")

    now = datetime.datetime.now()
    for idx in range(count):
        print(f"\n--- Article {idx + 1}/{count} ---")

        # Rotate over categories to keep the blog balanced
        category = CATEGORIES[idx % len(CATEGORIES)]
        print(f"Forced category: {category}")

        # Titles already published in this category (for subject dedup)
        cat_titles = [t for t, c in existing if c == category]

        # pubDate: spread backwards over N days, oldest first then newest last
        if days > 1 and count > 1:
            offset = round((days - 1) * idx / max(count - 1, 1))
        else:
            offset = 0
        pub_date = (now - datetime.timedelta(days=offset)).strftime('%Y-%m-%d')

        try:
            # 1. Title with deduplication (word similarity + semantic, up to 5 attempts)
            title = None
            for attempt in range(5):
                candidate = generate_topic(
                    niche, tone, language, model, api_base,
                    category=category, avoid_titles=cat_titles,
                )
                if is_duplicate(candidate, [t for t, _ in existing]):
                    print(f"Title too close to an existing article ({candidate!r}). Retrying...")
                    continue
                if is_semantic_duplicate(candidate, category, cat_titles, model, api_base):
                    print(f"Title duplicates an existing subject ({candidate!r}). Retrying...")
                    continue
                title = candidate
                break
            if title is None:
                raise RuntimeError('Could not generate a unique title after retries')
            title = strip_emojis(title).strip()
            print(f"Generated Title: {title}")

            # 2. Content with length check + editorial review + inline links
            content = generate_content(
                title, tone, language, model, api_base,
                existing_links=existing_links(),
            )
            reviewed = review_content(title, content, language, model, api_base)
            print(f"Content reviewed ({word_count(reviewed)} words).")

            # Clean inline links: drop any that point to unknown slugs
            valid_slugs = {slug for _, slug in existing_links()}
            reviewed, kept = validate_links(reviewed, valid_slugs)
            print(f"Inline links: {kept} valid, broken removed.")

            # 2.5. Meta description: short, engaging, not repeating the title
            description = generate_description(title, language, model, api_base)
            print(f"Description: {description}")

            # 3. Hero image: real Pexels photo matching the subject, SVG as fallback
            hero_image = generate_photo(title, category, niche, model, api_base,
                                        dry_run=args.dry_run)
            if hero_image is None and not args.dry_run:
                print("Image: Pexels unavailable, falling back to generated SVG.")
                hero_image = generate_svg(title, niche)
            print(f"Generated image: {hero_image}")

            save_post(title, reviewed, hero_image, category, date_str=pub_date, description=description)
            existing.append((title, category))

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
