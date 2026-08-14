# Blog — Site Astro "J'aime les chats"

Site statique du blog auto-généré, construit avec Astro.

## Structure

- `src/pages/` — routes (accueil, liste des articles, article, à propos, RSS)
- `src/content/blog/` — articles Markdown générés par le moteur (`engine/autoblog.py`)
- `src/components/` — Header, Footer, BaseHead, etc.
- `src/styles/global.css` — design system (palette douce, typo Caveat/Quicksand)
- `public/fonts/` — fonts self-hostées (woff2, aucun CDN)
- `public/images/` — images SVG générées par le moteur + og:image par défaut

## Commandes

| Commande | Action |
| :------- | :----- |
| `npm install` | Installe les dépendances |
| `npm run dev` | Serveur de dev local |
| `npm run build` | Build de production dans `./dist/` |
| `npm run preview` | Prévisualise le build |

## Déploiement

Le build est copié vers `/var/www/blog-site` par `scripts/deploy.sh` (docroot Nginx).
