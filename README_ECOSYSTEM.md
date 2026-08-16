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
- `siteUrl` : URL publique du site (utilisée pour les liens Facebook)
- `facebookEnabled`, `facebookPageId` : auto-publication Facebook

La clé API va dans `.env` (`DEEPSEEK_API_KEY=sk-...`).

## Images des articles (photos réelles)

Chaque article est illustré par une **vraie photo libre** (API Pexels) qui correspond au sujet :
1. DeepSeek traduit le titre + catégorie en requête de recherche anglaise
2. `engine/images.py` cherche sur Pexels (clé `PEXELS_API_KEY` dans `.env`), télécharge la photo
   recadrée 1200x630 en `.jpg`
3. Si Pexels échoue (pas de clé, erreur réseau), le moteur retombe sur un `.svg` généré
   (converti en `.png` par `scripts/convert-images.mjs` au déploiement)

L'`og:image` pointe toujours vers un format lisible par Facebook (jpg/png, jamais svg).

## Auto-publication Facebook (100% automatique)

Après chaque déploiement, `deploy.sh` exécute `engine/facebook.py` qui publie sur la page
Facebook tout nouvel article (`POST /{page}/feed`). Post = titre + description frontmatter + lien.
L'état est suivi dans `.fb_state.json` (idempotent) : un post qui échoue est retenté au passage
suivant. Un échec API ne bloque jamais le déploiement (l'article est publié sur le site quand même,
l'erreur est loggée).

Activation (à faire une fois par Thomas) :
1. Créer une app Facebook sur developers.facebook.com (type Business)
2. Ajouter la permission `pages_manage_posts`
3. Récupérer un **Page access token** (Graph API Explorer : `GET /me/accounts`, token de la page)
4. Le convertir en token longue durée (60 jours) via `oauth/access_token?grant_type=fb_exchange_token`
5. Le mettre dans `.env` : `FACEBOOK_PAGE_ACCESS_TOKEN=...` (jamais affiché par la CLI)
6. Activer : `python3 engine/admin.py config facebookEnabled true`

Le token expire au bout de ~60 jours : renouveler puis mettre à jour `.env`.

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
python3 engine/autoblog.py --dry-run            # test sans écrire
python3 engine/autoblog.py                      # génère un article
python3 engine/autoblog.py --count 12 --days 14 # 12 articles, dates échelonnées sur 14 jours
./scripts/deploy.sh                             # génère, build, publie
```

## Automatisation quotidienne

```bash
sudo systemctl enable --now blog-autoblog.timer   # active le timer 08:00
systemctl list-timers blog-autoblog.timer         # vérifie
```

## Serveur

Nginx sert `http://62.171.132.178` depuis `/var/www/blog-site` (vhost `/etc/nginx/sites-available/blog`).
