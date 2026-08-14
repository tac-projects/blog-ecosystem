# Automatic Blog Ecosystem

Blog auto-généré hébergé sur le VPS. Aucune dépendance externe : génération IA via DeepSeek, images SVG locales, déploiement Nginx, cron systemd.

> Mémoire opérationnelle (pièges, état, conventions) : voir `CLAUDE.md`.

## Architecture

```
engine/autoblog.py     Moteur Python (stdlib uniquement) : titre + contenu via DeepSeek, image SVG locale
site/                  Site Astro (markdown dans src/content/blog/)
scripts/deploy.sh      Moteur -> build Astro -> publication dans /var/www/blog-site
blog_config.json       Configuration (niche, langue, ton, modèle IA, heure)
.env                   Clé API DeepSeek (non versionné)
```

## Configuration

Éditez `blog_config.json` :
- `niche`, `language`, `tone` : paramètres de génération du contenu
- `model`, `apiBase` : modèle et endpoint DeepSeek (OpenAI-compatible)
- `automationActive` : active/désactive la génération quotidienne
- `publishTime` : heure de la génération (timer systemd `blog-autoblog.timer`)

La clé API va dans `.env` (`DEEPSEEK_API_KEY=sk-...`).

## Critères de génération d'un article

Pour chaque article, le moteur applique :
1. **Titre unique** : dédoublonnage automatique en 2 niveaux (similarité de mots sur tous les articles + contrôle sémantique IA sur les articles de la même catégorie), emojis supprimés
2. **Contenu** : ~1200 mots visés, minimum 800 mots vérifiés (régénération si trop court), format Markdown avec titres h2/h3, en français
3. **Relecture éditoriale** : correction orthographe/grammaire, suppression des répétitions et du remplissage, avant publication
4. **Catégorie** : classée parmi 5 fixes (Comportement, Sante & Soins, Nutrition, Races, Mode de vie)
5. **Image** : SVG local généré, palette cohérente avec le thème

## CLI admin (aucune page web)

`engine/admin.py` — pilotage du blog via terminal/opencode :

```bash
python3 engine/admin.py status                     # état + dernier article + timer
python3 engine/admin.py start                      # activer l'automatisation
python3 engine/admin.py stop                       # désactiver
python3 engine/admin.py config                     # afficher la config (clé API masquée)
python3 engine/admin.py config publishTime 08:00   # modifier une valeur
python3 engine/admin.py logs                       # 50 dernières lignes du service
```

Aucune surface web : la CLI n'écrit que dans `blog_config.json`.

## Génération manuelle

```bash
python3 engine/autoblog.py --dry-run   # test sans écrire
python3 engine/autoblog.py             # génère un article
./scripts/deploy.sh                    # génère, build, publie
```

## Automatisation quotidienne

```bash
sudo systemctl enable --now blog-autoblog.timer   # active le timer 08:00
systemctl list-timers blog-autoblog.timer         # vérifie
```

## Serveur

Nginx sert `http://62.171.132.178` depuis `/var/www/blog-site` (vhost `/etc/nginx/sites-available/blog`).
