import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, '..', 'site', 'package.json'));
const sharp = require('sharp');

const ROOT = path.resolve(__dirname, '..');
const BLOG_DIR = path.join(ROOT, 'site/src/content/blog');
const IMAGES_DIR = path.join(ROOT, 'site/public/images');
const OUT_DIR = path.join(ROOT, 'site/public/fb-cards');

const W = 1080;
const H = 1080;
const PHOTO_H = 480;
const PAD = 80;
const FRAME = 24; // épaisseur du cadre interne
const CR = 36;

const glyphWidth = (fontSize) => fontSize * 0.55;

function escapeXml(s) {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

function wrap(text, maxWidth, fontSize, maxLines = 99, ellipsis = false) {
	const maxChars = Math.floor(maxWidth / glyphWidth(fontSize));
	const words = text.split(/\s+/);
	const lines = [];
	let line = '';
	for (const word of words) {
		const candidate = line ? line + ' ' + word : word;
		if (candidate.length > maxChars && line) {
			lines.push(line);
			line = word;
		} else {
			line = candidate;
		}
	}
	if (line) lines.push(line);
	if (ellipsis && lines.length > maxLines) {
		// La dernière ligne visible reçoit les 3 petits points si le texte est coupé
		const visible = lines.slice(0, maxLines);
		const last = visible[maxLines - 1];
		visible[maxLines - 1] = last + '…';
		return visible;
	}
	return lines;
}

// Rend chaque ligne comme un <text> séparé avec y absolu (fiable, pas de tspan/dy)
// Retourne un SVG complet avec racine, valide pour sharp.
function textBlocks(lines, startY, fontSize, lineHeight, color, weight = 'normal', opacity = 1) {
	let y = startY;
	const els = lines.map((l) => {
		const el = `<text x="${PAD}" y="${y}" font-family="Georgia, serif" font-size="${fontSize}" font-weight="${weight}" fill="${color}" opacity="${opacity}">${escapeXml(l)}</text>`;
		y += fontSize * lineHeight;
		return el;
	});
	const svg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${els.join('\n')}</svg>`;
	return { svg, nextY: y };
}

async function makeCard(article) {
	const { slug, title, description } = article;

	// --- Fond ---
	const bg = `
	<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
		<defs>
			<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#FBF7F0"/>
				<stop offset="1" stop-color="#F3E9DB"/>
			</linearGradient>
		</defs>
		<rect width="${W}" height="${H}" fill="url(#bg)"/>
	</svg>`;

	// --- Photo (bandeau haut, dans le cadre) ---
	const photo = await sharp(path.join(IMAGES_DIR, article.image))
		.resize(W - 2 * FRAME, PHOTO_H, { fit: 'cover' })
		.toBuffer();

	// --- Texte ---
	const titleSize = 64;
	const titleLines = wrap(title, W - 2 * PAD, titleSize, 3, true);
	let titleSvg = '';
	let yTitle = PAD - FRAME + PHOTO_H + 64;
	titleSvg = textBlocks(titleLines, yTitle, titleSize, 1.18, '#2D2320', 'bold').svg;
	yTitle = textBlocks(titleLines, yTitle, titleSize, 1.18, '#2D2320', 'bold').nextY;

	// Description en sous-titre : 3 lignes max, "… Lire la suite" en terracotta sur la dernière
	const descSize = 30;
	const suffix = ' … Lire la suite';
	const suffixChars = Math.ceil(suffix.length * 0.62);
	const fullDescLines = wrap(description || '', W - 2 * PAD, descSize);
	const descLines = fullDescLines.slice(0, 3);
	let yDesc = yTitle + 16;
	let descSvg = '';
	if (descLines.length) {
		const headLines = descLines.slice(0, -1);
		let inner = '';
		for (const l of headLines) {
			inner += `<text x="${PAD}" y="${yDesc}" font-family="Georgia, serif" font-size="${descSize}" fill="#6B5D55">${escapeXml(l)}</text>`;
			yDesc += descSize * 1.45;
		}
		// La dernière ligne est raccourcie à la limite du dernier mot complet,
		// pour laisser la place au suffixe (qui inclut déjà "…")
		let lastLine = descLines[descLines.length - 1];
		const maxChars = Math.floor((W - 2 * PAD) / (descSize * 0.55));
		if (lastLine.length + suffixChars > maxChars) {
			let limit = Math.max(maxChars - suffixChars, 1);
			const trimmed = lastLine.slice(0, limit);
			const spaceIdx = trimmed.lastIndexOf(' ');
			lastLine = spaceIdx > 0 ? trimmed.slice(0, spaceIdx) : trimmed;
		}
		inner += `<text x="${PAD}" y="${yDesc}" font-family="Georgia, serif" font-size="${descSize}">
			<tspan fill="#6B5D55">${escapeXml(lastLine)}</tspan>
			<tspan fill="#C0673C" font-weight="bold">${escapeXml(suffix)}</tspan>
		</text>`;
		yDesc += descSize * 1.45;
		descSvg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
	}

	// Branding en bas : logo Facebook officiel + nom du blog
	const tagline = "J'aime les chats";
	const brandSvg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
		<g transform="translate(${PAD}, ${H - FRAME - 64})">
			<svg width="46" height="46" viewBox="0 0 24 24" fill="#C0673C" xmlns="http://www.w3.org/2000/svg">
				<path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.026 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971H15.83c-1.491 0-1.956.93-1.956 1.886v2.264h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/>
			</svg>
		</g>
		<text x="${PAD + 72}" y="${H - FRAME - 28}" font-family="Georgia, serif" font-size="36" font-weight="bold" fill="#C0673C">${escapeXml(tagline)}</text>
	</svg>`;

	// Patte de chat décorative, en bas à droite (terracotta)
	const pawSvg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
		<g transform="translate(${W - PAD - 80}, ${H - FRAME - 72})" fill="#C0673C">
			<ellipse cx="8" cy="34" rx="5" ry="8"/>
			<ellipse cx="22" cy="28" rx="5" ry="9"/>
			<ellipse cx="36" cy="28" rx="5" ry="9"/>
			<ellipse cx="50" cy="34" rx="5" ry="8"/>
			<path d="M29 38c-7 0-13 5-13 11 0 4 4 7 9 7 2 0 3-1 4-1s2 1 4 1c5 0 9-3 9-7 0-6-6-11-13-11z"/>
		</g>
	</svg>`;

	// --- Assemblage ---
	const card = await sharp(Buffer.from(bg))
		.composite([
			{ input: photo, top: FRAME, left: FRAME },
			{ input: Buffer.from(titleSvg) },
			{ input: Buffer.from(descSvg) },
			{ input: Buffer.from(brandSvg) },
			{ input: Buffer.from(pawSvg) },
		])
		.png()
		.toBuffer();
	return card;
}

function readArticles() {
	const articles = [];
	for (const f of fs.readdirSync(BLOG_DIR)) {
		if (!f.endsWith('.md')) continue;
		const slug = f.slice(0, -3);
		const head = fs.readFileSync(path.join(BLOG_DIR, f), 'utf-8').slice(0, 1200);
		const title = head.match(/^title:\s*"?(.+?)"?\s*$/m)?.[1]?.trim() || '';
		const desc = head.match(/^description:\s*"?(.+?)"?\s*$/m)?.[1]?.trim() || '';
		const heroImage = head.match(/^heroImage:\s*['"](.+?)['"]\s*$/m)?.[1] || '';
		articles.push({ slug, title, description: desc, image: heroImage.replace('/images/', '') });
	}
	return articles;
}

async function main() {
	fs.mkdirSync(OUT_DIR, { recursive: true });
	const articles = readArticles().filter((a) => a.image);
	let done = 0;
	for (const a of articles) {
		const png = path.join(OUT_DIR, `${a.slug}.png`);
		try {
			const buf = await makeCard(a);
			fs.writeFileSync(png, buf);
			console.log(`OK ${a.slug}`);
			done++;
		} catch (e) {
			console.error(`ERREUR ${a.slug}: ${e.message}`);
		}
	}
	console.log(`Cartes générées: ${done}/${articles.length}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
