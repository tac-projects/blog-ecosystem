// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'http://62.171.132.178',
	base: '/',
	integrations: [mdx(), sitemap()],
});
