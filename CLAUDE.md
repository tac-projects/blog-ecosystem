# Blog Écosystème — Notes projet (mémoire de travail)

Doc utilisateur complète : `README_ECOSYSTEM.md`.

## Objectif
Blog auto-généré sur le VPS, sans dépendance GitHub/Firebase/externes (sauf l'IA DeepSeek).

## Pièges connus
- **DeepSeek v4 Flash en mode "thinking"** : avec `max_tokens` trop petit (<512), `content` revient vide et tout part dans `reasoning_content`. Toujours garder `max_tokens` >= 1024 pour le titre. Ne JAMAIS fallback sur `reasoning_content` (pollue la sortie). `deepseek_chat` a un retry auto sur contenu vide (parfois le raisonnement consomme tout le budget). **Pour une longue réécriture (relecture), passer `thinking={'type': 'disabled'}` + `max_tokens` >= 6000**, sinon le modèle raisonne indéfiniment (des dizaines de milliers de caractères de `reasoning_content`) et ne produit jamais `content`.
- **Emojis** : le modèle met parfois des emojis dans les titres. `strip_emojis()` les retire au titre ET au slug.
- **Catégories** : 5 fixes (Comportement, Sante & Soins, Nutrition, Races, Mode de vie). Le moteur les choisit via DeepSeek et les stocke dans le frontmatter (`category`). Pages : `/categories/` et `/categories/[cat]/`. Accent/`&` encodés dans les URLs via `encodeURIComponent`.
- **Facebook** : page `https://www.facebook.com/nous.aimons.les.chats` centralisée dans `consts.ts` (`FACEBOOK_URL`), lien icône dans le Header, bouton partage `sharer.php` dans les articles.
- **Contrôles qualité** du moteur : dédoublonnage des titres double niveau — (1) Jaccard sur mots (`is_duplicate`, >= 0.55) sur TOUS les articles, (2) contrôle sémantique IA (`is_semantic_duplicate`, température 0) comparant le sujet avec les titres de la MÊME catégorie ; le titre est généré avec le contexte `avoid_titles` des articles de sa catégorie. 5 tentatives. Longueur minimale vérifiée (>= 800 mots), relecture éditoriale (`review_content` avec thinking désactivé). `existing_titles()` retourne des tuples (titre, catégorie).
- **Slugify** : normalise les accents (`NFKD` → ASCII) avant le slug, sinon des noms de fichiers/URLs avec accents (`honnêtement`) casse les routes.
- **Vhost Nginx** : `ecole` est `default_server` (`server_name _`) et capture tout. Le vhost `blog` matche `server_name 62.171.132.178`. Après modif de config, toujours `sudo systemctl reload nginx` sinon l'ancienne config reste active.
- **BASE_URL Astro** : avec `base: '/'`, `import.meta.env.BASE_URL` vaut `/` → `${BASE_URL}/blog` produit `//blog` (URL protocole-relatif, casse les routes). Toujours passer par le helper `url()` de `consts.ts`.
- **Design system** (skill ui-ux-pro-max) : magazine éditorial sérieux mais chaleureux pour communauté 45+ (monétisation future). Palette : fond crème `#FBF7F0`, accent terracotta `#C0673C` (dark `#8A4222`), titre `#2D2320`, texte `#40352F`, cartes blanches, coins sobres (8-12px). Typo **Libre Bodoni** (titres serif, éditoriale) / **Public Sans** (corps) — lisible, sérieuse. Fonts self-hostées dans `public/fonts/` (woff2, jamais de CDN). Les SVG du moteur ont une palette terracotta/brun/crème dérivée du titre. Description des articles en français (frontmatter).
- Après toute modif de `blog_config.json`, le déploiement repart de zéro (le build écrase `dist/`).
- **CLI admin** : syntaxe d'édition `python3 engine/admin.py config publishTime 08:00` (PAS de mot-clé `set`). La clé API n'est jamais affichée.

## État actuel
- `automationActive: false` — génération quotidienne coupée (timer en place mais non activé).
- Le timer `blog-autoblog.timer` est créé mais `inactive` / `disabled`.

## Serveur
- Nginx : vhost `/etc/nginx/sites-available/blog`, root `/var/www/blog-site`.
- IP publique : 62.171.132.178 (pas de TLS/domaine pour l'instant).

## Reste à faire
- Activer le timer systemd (avec accord).
- Sécuriser : domaine + TLS (Certbot).
- Migration Astro 5 -> 7 (+ sharp 0.35) pour éliminer les 4 dernières vulnérabilités npm (non exploitables en site statique — XSS/SSR nécessitent du contenu non fiable, inutilisé). `npm audit fix` a déjà corrigé 12/16.
