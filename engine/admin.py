import os
import sys
import json
import subprocess
import argparse
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, 'blog_config.json')
BLOG_DIR = os.path.join(PROJECT_DIR, 'site/src/content/blog')
SERVICE_NAME = 'blog-autoblog.service'
SENSITIVE_KEYS = {'DEEPSEEK_API_KEY', 'apiKey', 'api_key'}

EDITABLE_KEYS = {'niche', 'language', 'tone', 'model', 'apiBase', 'publishTime', 'automationActive',
                 'siteUrl', 'facebookEnabled', 'facebookPageId'}
BOOLEAN_KEYS = {'automationActive', 'facebookEnabled'}


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write('\n')


def latest_post():
    try:
        files = [f for f in os.listdir(BLOG_DIR) if f.endswith('.md')]
    except FileNotFoundError:
        return None
    if not files:
        return None
    files.sort(key=lambda f: os.path.getmtime(os.path.join(BLOG_DIR, f)), reverse=True)
    newest = files[0]
    mtime = os.path.getmtime(os.path.join(BLOG_DIR, newest))
    return newest, datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')


def timer_state():
    try:
        active = subprocess.run(
            ['systemctl', 'is-active', 'blog-autoblog.timer'],
            capture_output=True, text=True).stdout.strip()
        enabled = subprocess.run(
            ['systemctl', 'is-enabled', 'blog-autoblog.timer'],
            capture_output=True, text=True).stdout.strip()
        return f"{active} / {enabled}"
    except Exception:
        return 'inconnu'


def cmd_status(config):
    post = latest_post()
    print("=== Blog admin status ===")
    print(f"automationActive : {config.get('automationActive')}")
    print(f"niche            : {config.get('niche')}")
    print(f"langue           : {config.get('language')}")
    print(f"ton              : {config.get('tone')}")
    print(f"modèle IA        : {config.get('model')}")
    print(f"heure de publi.  : {config.get('publishTime')}")
    print(f"Facebook         : {'activé' if config.get('facebookEnabled') else 'désactivé'} "
          f"(page {config.get('facebookPageId')})")
    print(f"site URL         : {config.get('siteUrl')}")
    print(f"timer systemd    : {timer_state()}")
    if post:
        print(f"dernier article  : {post[0]} ({post[1]})")
    else:
        print("dernier article  : aucun")


def cmd_start(config):
    config['automationActive'] = True
    save_config(config)
    print("Automatisation activée (automationActive=true)")


def cmd_stop(config):
    config['automationActive'] = False
    save_config(config)
    print("Automatisation désactivée (automationActive=false)")


def cmd_config(config, key=None, value=None):
    if key is None:
        print("=== Configuration ===")
        for k, v in config.items():
            if k in SENSITIVE_KEYS:
                continue
            print(f"{k} : {v}")
        return

    if key not in EDITABLE_KEYS:
        print(f"Clé non éditable. Clés possibles : {', '.join(sorted(EDITABLE_KEYS))}")
        sys.exit(1)

    if value is None:
        print(f"{key} : {config.get(key)}")
        return

    if key in BOOLEAN_KEYS:
        value = value.lower() in ('true', '1', 'oui', 'yes', 'on')
    config[key] = value
    save_config(config)
    print(f"{key} = {value}")


def cmd_logs(lines=50):
    try:
        result = subprocess.run(
            ['sudo', 'journalctl', '-u', SERVICE_NAME, '-n', str(lines), '--no-pager'],
            capture_output=True, text=True, check=True)
        print(result.stdout if result.stdout else "(pas de logs pour le moment)")
    except Exception as e:
        print(f"Erreur lors de la lecture des logs: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Blog admin CLI")
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('status', help="État de l'automatisation et du blog")
    sub.add_parser('start', help="Activer l'automatisation quotidienne")
    sub.add_parser('stop', help="Désactiver l'automatisation quotidienne")

    p_config = sub.add_parser('config', help="Afficher ou modifier la configuration")
    p_config.add_argument('key', nargs='?', help="Clé à lire ou modifier")
    p_config.add_argument('value', nargs='?', help="Nouvelle valeur")

    p_logs = sub.add_parser('logs', help="Dernières lignes du service")
    p_logs.add_argument('-n', type=int, default=50, help="Nombre de lignes")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == 'logs':
        cmd_logs(args.n)
        return

    config = load_config()
    if args.command == 'status':
        cmd_status(config)
    elif args.command == 'start':
        cmd_start(config)
    elif args.command == 'stop':
        cmd_stop(config)
    elif args.command == 'config':
        cmd_config(config, getattr(args, 'key', None), getattr(args, 'value', None))


if __name__ == "__main__":
    main()
