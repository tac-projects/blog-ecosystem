// Incruste un hook court (texte) sur la photo du jour générée par Gemini.
// Usage : node scripts/gemini-card.mjs <input.jpg> <output.jpg> <hook>
// Produit une image carrée 1080x1080 : photo plein cadre + bandeau dégradé
// en bas + texte du hook en serif blanc, barre d'accent terracotta.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, '..', 'site', 'package.json'));
const sharp = require('sharp');

const [input, output, hook] = process.argv.slice(2);
if (!input || !output || !hook) {
	console.error('Usage: node scripts/gemini-card.mjs <input> <output> <hook>');
	process.exit(1);
}

const W = 1080;
const H = 1080;
const PAD = 70;
const glyphWidth = (fontSize) => fontSize * 0.55;

function escapeXml(s) {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

function wrap(text, maxWidth, fontSize, maxLines = 3) {
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
	if (lines.length > maxLines) {
		const visible = lines.slice(0, maxLines);
		const last = visible[maxLines - 1].replace(/[.,;:!?…]+$/, '');
		visible[maxLines - 1] = last + ' …';
		return visible;
	}
	return lines;
}

async function main() {
	const photo = await sharp(input)
		.resize(W, H, { fit: 'cover' })
		.toBuffer();

	const hookSize = 76;
	const lines = wrap(hook, W - 2 * PAD, hookSize, 3);
	const lineHeight = 1.25;
	const blockH = lines.length * hookSize * lineHeight;

	// Bandeau dégradé sombre (lisibilité) + texte + barre terracotta
	const textEls = [];
	let y = H - PAD - blockH + hookSize;
	for (const l of lines) {
		textEls.push(
			`<text x="${PAD}" y="${y}" font-family="Georgia, serif" font-size="${hookSize}" font-weight="bold" fill="#ffffff">${escapeXml(l)}</text>`
		);
		y += hookSize * lineHeight;
	}
	const svg = `<svg width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg">
		<defs>
			<linearGradient id="band" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#000000" stop-opacity="0"/>
				<stop offset="0.55" stop-color="#000000" stop-opacity="0.45"/>
				<stop offset="1" stop-color="#000000" stop-opacity="0.75"/>
			</linearGradient>
		</defs>
		<rect x="0" y="${Math.round(H * 0.45)}" width="${W}" height="${Math.round(H * 0.55)}" fill="url(#band)"/>
		<rect x="${PAD}" y="${H - PAD - blockH - 46}" width="72" height="10" fill="#C0673C"/>
		${textEls.join('\n')}
	</svg>`;

	const out = await sharp(photo)
		.composite([{ input: Buffer.from(svg) }])
		.jpeg({ quality: 90 })
		.toBuffer();

	fs.writeFileSync(output, out);
	console.log(`Carte générée: ${output} (${out.length} bytes)`);
}

main().catch((e) => { console.error(e); process.exit(1); });
