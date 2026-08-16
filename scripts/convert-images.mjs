// Convertit tous les SVG d'illustration en PNG (requis par Facebook pour og:image).
// Les SVG restent utilisés pour l'affichage du site ; les PNG ne servent qu'à l'aperçu FB.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, '..', 'site', 'package.json'));
const sharp = require('sharp');

const IMAGES_DIR = path.resolve(__dirname, '..', 'site/public/images');

async function main() {
	const files = fs.readdirSync(IMAGES_DIR).filter((f) => f.endsWith('.svg'));
	for (const f of files) {
		const svgPath = path.join(IMAGES_DIR, f);
		const pngPath = path.join(IMAGES_DIR, f.replace(/\.svg$/, '.png'));
		await sharp(svgPath).png().toFile(pngPath);
	}
	console.log(`Converted ${files.length} SVG -> PNG in ${IMAGES_DIR}`);
}

main().catch((e) => {
	console.error(e);
	process.exit(1);
});
