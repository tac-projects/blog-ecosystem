import os
import datetime
import random
import time
import argparse
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore

# Configure arguments
parser = argparse.ArgumentParser(description='AutoBlog Engine')
parser.add_argument('--dry-run', action='store_true', help='Do not save files')
args = parser.parse_args()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_CONTENT_DIR = os.path.join(BASE_DIR, '../blog_template/src/content/blog')

# Initialize Firebase
# Expects GOOGLE_APPLICATION_CREDENTIALS env var or FIREBASE_CREDENTIALS_JSON content
cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if not cred_path and os.environ.get('FIREBASE_CREDENTIALS'):
    # Create temp file from env string if needed, or initialized via dict
    # For simplicity, we assume we can initialize from a dict if provided as JSON string
    # But firebase_admin usually takes a file path or dict.
    import json
    cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
    cred = credentials.Certificate(cred_dict)
else:
    # Fallback/Local dev
    cred = credentials.ApplicationDefault() # Or usage of local file

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Initialize Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not set.")

def get_config():
    """Fetch blog configuration from Firestore."""
    try:
        doc_ref = db.collection('settings').document('blogConfig')
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            print("No config found, using defaults.")
            return {}
    except Exception as e:
        print(f"Error fetching config: {e}")
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
