import type { Page } from '@playwright/test';
import en from '../../src/locales/en.json' with { type: 'json' };

// Only text that starts with a real top-level section of en.json ("navbar.", "auth.", ...) can
// be a missing key. Anything else that merely looks like one, such as "example.com", cannot.
const SECTIONS = new Set(Object.keys(en));

const KEY_SHAPE = /^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$/;

/**
 * Visible text nodes that look like an untranslated i18n key ("section.some_key") because the
 * key is missing from the locale file.
 */
export async function rawTranslationKeys(page: Page): Promise<string[]> {
	const candidates = await page.evaluate(() => {
		const found = new Set<string>();
		const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
		for (let node = walker.nextNode(); node; node = walker.nextNode()) {
			const el = node.parentElement;
			if (!el || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName)) continue;
			const text = (node.textContent ?? '').trim();
			if (text && el.checkVisibility?.()) found.add(text);
		}
		for (const el of document.querySelectorAll('[aria-label],[title],[placeholder]')) {
			for (const attr of ['aria-label', 'title', 'placeholder']) {
				const value = el.getAttribute(attr)?.trim();
				if (value) found.add(value);
			}
		}
		return [...found];
	});
	return candidates.filter((text) => KEY_SHAPE.test(text) && SECTIONS.has(text.split('.')[0]));
}
