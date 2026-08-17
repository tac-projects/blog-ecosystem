# Automatic Blog Ecosystem

Blog auto-généré hébergé sur le VPS. Génération IA via DeepSeek, photos réelles Pexels, cartes Facebook natives, déploiement Nginx, timer systemd.

> Mémoire opérationnelle (pièges, état, conventions) : voir `CLAUDE.md`.

## Architecture

```
engine/autoblog.py     Moteur Python (stdlib uniquement) : titre + contenu + description via DeepSeek
engine/images.py       Photos réelles via Pexels (recadrées 1200x630), SVG en secours
engine/facebook.py     Auto-publication Facebook (carte photo native + lien)
engine/gemini_image.py Image du jour : hook + photo Gemini, hook incrusté (sharp), post sans légende
scripts/gemini-card.mjs Incruste le hook dans la photo du jour (node + sharp, 1080x1080)
scripts/fb-cards.mjs   Génère les cartes 1080x1080 pour les posts Facebook (sharp)
scripts/convert-images.mjs  Convertit les SVG restants en PNG (og:image FB)
scripts/deploy.sh      Moteur -> cartes -> build Astro -> publication -> posts Facebooksite/                  Site Astro (markdown dans src/content/blog/)
blog_config.json       Configuration + TOUS les prompts (modifiables sans toucher au code)
.env                   Clés API (DeepSeek, Pexels, Facebook, Gemini) — non versionné
```

## Configuration

Éditez `blog_config.json` :
- `niche`, `language`, `tone` : paramètres de génération du contenu
- `model`, `apiBase` : modèle et endpoint DeepSeek (OpenAI-compatible)
- `automationActive` : active/désactive la génération quotidienne
- `publishTime` : heure de la génération (timer systemd `blog-autoblog.timer`)
- `siteUrl` : URL publique du site (utilisée pour les liens Facebook)
- `facebookEnabled`, `facebookPageId` : auto-publication Facebook
- `content` : seuils (minWords, targetWords, minSections, maxSections)
- `prompts` : tous les prompts de génération (topic, content, review, description,
  semantic_duplicate, strip_duplicate_heading, image_query) — placeholders `{...}`

Les clés API vont dans `.env` (`DEEPSEEK_API_KEY`, `PEXELS_API_KEY`,
`FACEBOOK_PAGE_ACCESS_TOKEN`, `GEMINI_API_KEY` — jamais versionnées).

## Images des articles (photos réelles)

Chaque article est illustré par une **vraie photo libre** (API Pexels) qui correspond au sujet :
1. DeepSeek traduit le titre + catégorie en requête de recherche anglaise (prompt dans `blog_config.json`)
2. `engine/images.py` cherche sur Pexels (clé `PEXELS_API_KEY` dans `.env`), télécharge la photo
   recadrée 1200x630 en `.jpg`
3. Si Pexels échoue (pas de clé, erreur réseau), le moteur retombe sur un `.svg` généré
   (converti en `.png` par `scripts/convert-images.mjs` au déploiement)

L'`og:image` pointe toujours vers un format lisible par Facebook (jpg/png, jamais svg).

## Cartes Facebook (posts visuels)

`scripts/fb-cards.mjs` génère une carte **1080x1080** par article (photo + titre + description
avec « … Lire la suite » + logo FB + patte de chat) dans `site/public/fb-cards/`.

## Auto-publication Facebook (100% automatique)

Après chaque déploiement, `deploy.sh` exécute `engine/facebook.py` qui publie sur la page
Facebook tout nouvel article :
- **Photo native** : upload multipart de la carte `fb-cards/{slug}.png` (`POST /{page}/photos`)
- **Texte** : accroche « L'article du jour », titre, lien `{siteUrl}/blog/{slug}` visible tôt
  (avant le pli « Voir plus »), description après
- **Fallback** : post-lien classique si la carte manque
L'état est suivi dans `.fb_state.json` (idempotent) : un post qui échoue est retenté au passage
suivant. Un échec API ne bloque jamais le déploiement.

## Image du jour (100% automatique, générée par IA, publication indépendante)

À **12:00**, le timer systemd `blog-gemini-image.timer` exécute `engine/gemini_image.py` qui
publie **1 image générée par Gemini**, avec un **thème 100% indépendant de l'article du jour** :
- **Hook + scène** : DeepSeek génère un JSON `{hook, scene}` — hook = phrase française courte et
  punchy ; scene = description anglaise de la photo qui l'illustre exactement (cohérence garantie)
- **Anti-répétition** : les hooks déjà publiés sont passés en `{avoid_hooks}` dans le prompt
- **Photo** : générée par le modèle image (`gemini-3.1-flash-lite-image`, ~800 KB JPEG), carrée,
  photoréaliste et **sans aucun texte**
- **Incrustation** : `scripts/gemini-card.mjs` (node + sharp) incruste le hook dans la photo
  (bandeau dégradé, serif blanc, barre terracotta) → carte finale 1080x1080
- **Post** : photo native sur la page **sans légende** (zéro texte hors image)
L'état est suivi par date dans `.gemini_image_state.json` (`posted` = dates, `hooks` = anti-répétition).
Config : `geminiImageEnabled`/`geminiImageModel` + prompts `prompts.gemini_image.*`.

## Critères de génération d'un article

Pour chaque article, le moteur applique :
1. **Titre unique** : dédoublonnage automatique en 2 niveaux (similarité de mots sur tous les articles + contrôle sémantique IA sur les articles de la même catégorie), emojis supprimés
2. **Contenu** : ~1200 mots visés, minimum 800 mots vérifiés (régénération si trop court), format Markdown : intro + 3-10 sections h2 + conclusion, en français
3. **Relecture éditoriale** : correction orthographe/grammaire, suppression des répétitions et du remplissage, avant publication
4. **Catégorie** : classée parmi 6 fixes (Comportement, Sante & Soins, Nutrition, Races, Mode de vie, Adoption)
5. **Image** : photo Pexels réelle (SVG en secours)
6. **Liens internes** : 2 liens inline vers des articles pertinents (slugs vérifiés)
7. **Description** : 2-3 phrases uniques (pas de répétition du titre)

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
./scripts/deploy.sh                             # génère, build, publie l'article (08:00)
```

## Automatisation quotidienne

Deux publications indépendantes chaque jour :
- **08:00** — article du jour : timer `blog-autoblog.timer` → `deploy.sh` (génération + build + publication article)
- **12:00** — image du jour : timer `blog-gemini-image.timer` → `engine/gemini_image.py` (thème indépendant de l'article)

```bash
sudo systemctl enable --now blog-autoblog.timer      # timer article 08:00
sudo systemctl enable --now blog-gemini-image.timer  # timer image 12:00
systemctl list-timers blog-autoblog.timer blog-gemini-image.timer   # vérifie
```

## Référencement

- `robots.txt` : `Allow: /` pour tous les bots (exception `facebookexternalhit`/`Facebot` conservée)
- Sitemap généré par `@astrojs/sitemap` (`sitemap-index.xml`)
- Attention : indexation réelle faible sur IP brute en HTTP — un domaine + TLS est nécessaire.

## Serveur

Nginx sert `http://62.171.132.178` depuis `/var/www/blog-site` (vhost `/etc/nginx/sites-available/blog`).
