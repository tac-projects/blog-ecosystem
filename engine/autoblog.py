import os
import datetime
import random
import time
import argparse
import urllib.parse
import google.generativeai as genai
import json
import sys

# Initialize Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Available Gemini Models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
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

def generate_with_retry(model, prompt, tries=3, delay=5):
    """Helper to generate content with retry on 429 errors."""
    for i in range(tries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            if "429" in str(e) or "Resource exhausted" in str(e):
                if i < tries - 1:
                    wait_time = delay * (2 ** i)
                    print(f"Rate limit hit (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            raise e


def generate_topic(niche, tone, language):
    """Generate a viral topic idea."""
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"Give me 1 viral blog post title about {niche} in the language '{language}'. The tone should be {tone}. Just the title, no quotes."
    response = generate_with_retry(model, prompt)
    return response.text.strip()

def generate_content(title, tone, language):
    """Generate full blog post content in Markdown."""
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"""
    Write a 1200-word blog post about "{title}".
    Tone: {tone}. Language: {language} (Must be written in {language}).
    Format: Markdown.
    Include h2, h3 headings.
    Do NOT include the title at the start (it will be in frontmatter).
    Do NOT wrap in markdown code blocks.
    """
    response = generate_with_retry(model, prompt)
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
    
    if not config.get('automationActive', True):
        print("Automation is disabled. Skipping generation.")
        return
    
    # 1. Topic
    try:
        title = generate_topic(niche, tone, language)
        print(f"Generated Title: {title}")
        
        # 2. Content
        content = generate_content(title, tone, language)
        print("Content generated.")
        
        # 3. Image Generation (AI)
        print("Generating AI Image...")
        
        # Ask Gemini for a "Cute" visual description based on the title
        image_prompt_request = f"Give me a short, highly descriptive image prompt for an adorable, cute, fluffy cat image related to this blog title: '{title}'. Style: Disney Pixar 3D or Hyperrealistic cute. No text in image. Just the prompt in English."
        model = genai.GenerativeModel('gemini-2.0-flash')
        image_prompt_response = generate_with_retry(model, image_prompt_request)
        image_prompt = image_prompt_response.text.strip()
        print(f"Image Prompt: {image_prompt}")

        # Use Pollinations.ai (Free, Unlimited, URL-based)
        # We add a random seed to ensure uniqueness even if prompt is similar
        seed = random.randint(1, 10000000)
        encoded_prompt = urllib.parse.quote(image_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=1200&height=630&nologo=true"
        
        # 4. Save
        save_post(title, content, image_url)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        # In production, send alert to Dashboard
        sys.exit(1)
        
if __name__ == "__main__":
    main()
