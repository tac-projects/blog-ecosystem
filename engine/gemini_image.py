import os
import json
import time
import datetime
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
IMAGES_DIR = os.path.join(PROJECT_DIR, '.gemini_images')
STATE_FILE = os.path.join(PROJECT_DIR, '.gemini_image_state.json')
ENV_FILE = os.path.join(PROJECT_DIR, '.env')
GEMINI_CARD_SCRIPT = os.path.join(PROJECT_DIR, 'scripts/gemini-card.mjs')
API_BASE = 'https://generativelanguage.googleapis.com/v1beta'
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
        print(f"[gemini_image] Error reading config: {e}")
        return {}


def get_prompt(config, path, **kwargs):
    node = config
    for part in path.split('.'):
        node = node.get(part, '') if isinstance(node, dict) else ''
    template = node if isinstance(node, str) else ''
    for k, v in kwargs.items():
        template = template.replace('{' + k + '}', str(v))
    return template


def deepseek_chat(prompt, model, api_base, temperature=1.0, max_tokens=200):
    """Appelle DeepSeek pour le texte (hook). Retry auto sur contenu vide."""
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
            'thinking': {'type': 'disabled'},
        }
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


def parse_hook_scene(raw):
    """Extrait le hook (français) et la scène (anglais) de la réponse DeepSeek.

    Tolère un JSON enveloppé dans des fences markdown (```json ... ```).
    """
    import re as _re
    text = raw.strip()
    fence = _re.search(r'```(?:json)?\s*(.*?)```', text, _re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    hook = str(data.get('hook', '')).strip().strip('"')
    scene = str(data.get('scene', '')).strip().strip('"')
    if not hook:
        raise RuntimeError('DeepSeek returned no hook')
    if not scene:
        raise RuntimeError('DeepSeek returned no scene')
    return hook, scene


def gemini_image(prompt, model, api_key):
    """Appelle le modèle d'image Gemini. Retourne (bytes, mime_type)."""
    url = f"{API_BASE}/models/{model}:generateContent"
    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-goog-api-key', api_key)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    parts = data['candidates'][0]['content']['parts']
    for p in parts:
        inline = p.get('inlineData')
        if inline and inline.get('data'):
            import base64
            return base64.b64decode(inline['data']), inline.get('mimeType', 'image/png')
    raise RuntimeError('Gemini image returned no inlineData')


def previous_hooks():
    """Hooks déjà publiés (toutes dates confondues), pour éviter la répétition de thèmes."""
    _, hooks = load_state()
    return hooks


def load_state():
    """Retourne (posted_set, hooks_list)."""
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return set(), []
    return set(data.get('posted', [])), [h for h in data.get('hooks', []) if h]


def save_state(posted, hooks):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'posted': sorted(posted), 'hooks': hooks}, f, ensure_ascii=False, indent=2)
        f.write('\n')


def publish_photo(image_path, token, page_id):
    """Poste une photo native sur la page SANS légende (multipart/form-data)."""
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/photos"
    boundary = '----geminiImageBoundary9YkQ4m2bNv'
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    parts = []
    parts.append(
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="access_token"\r\n\r\n'
        f"{token}\r\n"
    )
    parts.append(
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="source"; filename="gemini.jpg"\r\n'
        'Content-Type: image/jpeg\r\n\r\n'
    )
    body = ''.join(parts).encode('utf-8') + image_bytes + f"\r\n--{boundary}--\r\n".encode('utf-8')

    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        print(f"[gemini_image] Published daily photo -> {payload.get('id') or payload.get('post_id')}")
        return True
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode('utf-8'))
            err = err_body.get('error', {}).get('message', e.reason)
        except Exception:
            err = e.reason
        print(f"[gemini_image] ERROR publishing photo: {err}")
    except Exception as e:
        print(f"[gemini_image] ERROR publishing photo: {e}")
    return False


def main():
    load_env()
    config = get_config()

    if not config.get('geminiImageEnabled', False):
        print("[gemini_image] Disabled (geminiImageEnabled=false). Skipping.")
        return

    page_id = config.get('facebookPageId')
    token = os.environ.get('FACEBOOK_PAGE_ACCESS_TOKEN', '')
    gemini_key = os.environ.get('GEMINI_API_KEY', '')

    if not page_id or not token:
        print("[gemini_image] WARNING: facebookPageId or FACEBOOK_PAGE_ACCESS_TOKEN missing. Skipping.")
        return
    if not gemini_key:
        print("[gemini_image] WARNING: GEMINI_API_KEY missing. Skipping.")
        return

    image_model = config.get('geminiImageModel', 'gemini-3.1-flash-lite-image')
    deepseek_model = config.get('model', 'deepseek-v4-flash')
    deepseek_base = config.get('apiBase', 'https://api.deepseek.com')

    today = datetime.date.today().isoformat()
    posted, hooks = load_state()
    if today in posted:
        print(f"[gemini_image] Already published an image today ({today}). Skipping.")
        return

    try:
        # 1. Hook + scène : DeepSeek génère les deux ensemble (JSON) pour garantir
        #    que la photo illustre exactement le texte incrusté.
        #    Thème 100% INDÉPENDANT de l'article du jour + anti-répétition des hooks.
        avoid_hooks = ' | '.join(hooks[-20:])
        raw = deepseek_chat(
            get_prompt(config, 'prompts.gemini_image.hook', avoid_hooks=avoid_hooks),
            deepseek_model, deepseek_base, temperature=1.0, max_tokens=300,
        )
        hook, scene = parse_hook_scene(raw)
        print(f"[gemini_image] Hook: {hook}")
        print(f"[gemini_image] Scene: {scene}")

        # 2. Photo : générée à partir de la scène (sans texte, carrée, photoréaliste)
        image_bytes, mime = gemini_image(
            get_prompt(config, 'prompts.gemini_image.image', scene=scene),
            image_model, gemini_key,
        )
        ext = '.png' if mime == 'image/png' else '.jpg'
        os.makedirs(IMAGES_DIR, exist_ok=True)
        raw_path = os.path.join(IMAGES_DIR, f"{today}_raw{ext}")
        with open(raw_path, 'wb') as f:
            f.write(image_bytes)
        print(f"[gemini_image] Generated photo: {raw_path} ({len(image_bytes)} bytes)")

        # 3. Incrustation du hook via sharp (node) -> image finale avec texte
        card_path = os.path.join(IMAGES_DIR, f"{today}.jpg")
        import subprocess
        result = subprocess.run(
            ['node', GEMINI_CARD_SCRIPT, raw_path, card_path, hook],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            print(f"[gemini_image] ERROR overlay: {result.stderr.strip()}")
            return
        print(result.stdout.strip())

        if publish_photo(card_path, token, page_id):
            posted.add(today)
            hooks.append(hook)
            save_state(posted, hooks)
    except Exception as e:
        print(f"[gemini_image] ERROR: {e}")


if __name__ == "__main__":
    main()
