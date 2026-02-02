# Automatic Blog Ecosystem - Setup Guide

## 1. Dashboard (Local Control)
This component creates the configuration for your blog.
1. Go to `dashboard/`
2. Run `npm install`
3. Run `npm run dev`
4. Open http://localhost:5173
5. Configure your Firebase details in `src/lib/firebase.js` (Required for saving).

## 2. Blog Template (The Website)
This is the public static site.
1. Go to `blog_template/`
2. Run `npm install`
3. Run `npm run dev` to preview.
4. Content is in `src/content/blog/`.

## 3. Automation Engine (Python)
This script generates content.
1. Go to `engine/`
2. Install deps: `pip install -r requirements.txt`
3. Set Env Vars: `GEMINI_API_KEY` and `GOOGLE_APPLICATION_CREDENTIALS` (or `FIREBASE_CREDENTIALS` json string).
4. Run: `python autoblog.py`
5. Check `blog_template/src/content/blog/` for new `.md` files.

## 4. GitHub Actions (Deployment)
1. Push this entire repo to GitHub.
2. Go to Settings > Secrets and Variables > Actions.
3. Add secrets:
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
   - `FIREBASE_CREDENTIALS`: The content of your Firebase Service Account JSON.
4. The workflow runs daily at 8:00 UTC.
