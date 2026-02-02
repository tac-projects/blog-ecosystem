import os
import datetime
import random
import time
import argparse
import google.generativeai as genai
import json

# Initialize Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
# else case handled in generation
# else case handled in generation

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_CONTENT_DIR = os.path.join(BASE_DIR, '../blog_template/src/content/blog')
    
# CLI Args
parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Do not save files')
args = parser.parse_args()

def get_config():
    """Fetch blog configuration from blog_config.json."""
    config_path = os.path.join(BASE_DIR, '../blog_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error fetching config from {config_path}: {e}")
        return {}

def generate_topic(niche, tone):
    """Generate a viral topic idea."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Give me 1 viral blog post title about {niche}. The tone should be {tone}. Just the title, no quotes."
    response = model.generate_content(prompt)
    return response.text.strip()

def generate_content(title, tone, language):
    """Generate full blog post content in Markdown."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Write a 1200-word blog post about "{title}".
    Tone: {tone}. Language: {language}.
    Format: Markdown.
    Include h2, h3 headings.
    Do NOT include the title at the start (it will be in frontmatter).
    Do NOT wrap in markdown code blocks.
    """
    response = model.generate_content(prompt)
    return response.text

def save_post(title, content, image_url):
    """Save the post to the repo."""
    slug = title.lower().replace(' ', '-').replace(':', '').replace('?', '')[:50]
    filename = f"{slug}.md"
    filepath = os.path.join(BLOG_CONTENT_DIR, filename)
    
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    
    frontmatter = f"""---
title: "{title}"
description: "An in-depth look at {title}."
pubDate: '{date_str}'
heroImage: '{image_url}'
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
    print("Starting AutoBlog Engine...")
    config = get_config()
    
    # Defaults
    niche = config.get('niche', 'Technology')
    tone = config.get('tone', 'Expert')
    language = config.get('language', 'English')
    
    print(f"Configuration: Niche={niche}, Tone={tone}")
    
    # 1. Topic
    try:
        title = generate_topic(niche, tone)
        print(f"Generated Title: {title}")
        
        # 2. Content
        content = generate_content(title, tone, language)
        print("Content generated.")
        
        # 3. Image (Mocked for robustness if no KEY)
        # Real implementation would use Imagen/Vertex AI
        # For this boilerplate, we use a reliable placeholder based on keyword
        keyword = niche.split()[0]
        image_url = f"https://source.unsplash.com/1200x630/?{keyword}" 
        # Note: source.unsplash is deprecated/unreliable sometimes, using a generic one
        image_url = "/blog-placeholder-1.jpg" # Fallback to local asset
        
        # 4. Save
        save_post(title, content, image_url)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # In production, send alert to Dashboard
        
if __name__ == "__main__":
    main()
