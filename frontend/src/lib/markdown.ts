import { Marked, Renderer, type Tokens } from 'marked';

const HTML_ESCAPES: Record<string, string> = {
	'&': '&amp;',
	'<': '&lt;',
	'>': '&gt;',
	'"': '&quot;',
	"'": '&#39;'
};

export function escapeHtml(value: string): string {
	return value.replace(/[&<>"']/g, (char) => HTML_ESCAPES[char]);
}

const SAFE_URL_SCHEMES = new Set(['http', 'https', 'mailto', 'tel']);

/**
 * Whether a link or image address may be put in an href/src. Relative addresses and
 * http(s), mailto and tel are fine; javascript:, data:, vbscript: and anything else are not.
 * Entities and the control characters a browser ignores inside a scheme are undone first,
 * so `java&#x09;script:` or `javascript&colon;` cannot slip through.
 */
export function isSafeUrl(href: string | null | undefined): boolean {
	if (!href) return false;
	const decoded = href
		.replace(/&#x([0-9a-f]+);?/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
		.replace(/&#(\d+);?/g, (_, dec) => String.fromCodePoint(parseInt(dec, 10)))
		.replace(/&colon;/gi, ':')
		.replace(/&(tab|newline);/gi, '')
		// eslint-disable-next-line no-control-regex
		.replace(/[\u0000- \u007f-\u009f]/g, '');
	const scheme = /^([a-z][a-z0-9+.-]*):/i.exec(decoded);
	if (!scheme) return true; // relative path, fragment or query
	return SAFE_URL_SCHEMES.has(scheme[1].toLowerCase());
}

/**
 * Markdown for text other people wrote (notes, descriptions).
 *
 * It needs no DOM, so the server render and the browser render are identical: Svelte does
 * not repair an {@html} block that differs after hydration, and DOMPurify cannot run on
 * the server. Raw HTML in the source is shown as text, and links or images with an unsafe
 * scheme lose their address. Links to other websites open in a new tab, so a reader keeps
 * their place; in-app, mailto and tel links stay in the same tab.
 */
const WEB_LINK = /^(https?:)?\/\//i;

const safeMarked = new Marked({
	gfm: true,
	async: false,
	walkTokens(token) {
		if (token.type === 'link' || token.type === 'image') {
			const link = token as Tokens.Link | Tokens.Image;
			if (!isSafeUrl(link.href)) link.href = '#';
		}
	},
	renderer: {
		html(token: Tokens.HTML | Tokens.Tag) {
			return escapeHtml(token.text);
		},
		link(this: Renderer, token: Tokens.Link) {
			const html = Renderer.prototype.link.call(this, token);
			if (!WEB_LINK.test(token.href) || !html.startsWith('<a ')) return html;
			return `<a target="_blank" rel="noopener noreferrer" ${html.slice(3)}`;
		}
	}
});

export function renderMarkdown(value: string | null | undefined): string {
	if (!value) return '';
	return safeMarked.parse(String(value)) as string;
}

/** Plain text from an HTML fragment, for showing a third-party description as text. */
export function htmlToText(value: string | null | undefined): string {
	if (!value) return '';
	return String(value)
		.replace(/<(script|style)[\s\S]*?<\/\1\s*>/gi, ' ')
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/<\/(p|div|li|h[1-6])\s*>/gi, '\n')
		.replace(/<[^>]*>/g, '')
		.replace(/&nbsp;/g, ' ')
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>')
		.replace(/&quot;/g, '"')
		.replace(/&#39;/g, "'")
		.replace(/&amp;/g, '&')
		.replace(/[ \t]+/g, ' ')
		.replace(/\n\s*\n\s*/g, '\n\n')
		.trim();
}

const MARKDOWN_PATTERNS: Array<[RegExp, string]> = [
	[/!\[.*?\]\(.*?\)/g, ''],
	[/\[([^\]]+)\]\([^)]+\)/g, '$1'],
	[/#{1,6}\s*/g, ''],
	[/\*\*([^*]+)\*\*/g, '$1'],
	[/\*([^*]+)\*/g, '$1'],
	[/`([^`]+)`/g, '$1']
];

export function stripMarkdown(value: string | null | undefined, maxLength = 200): string {
	if (!value) return '';
	let text = String(value);
	for (const [pattern, replacement] of MARKDOWN_PATTERNS) {
		text = text.replace(pattern, replacement);
	}
	text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
	text = text.replace(/\n{3,}/g, '\n\n').trim();
	if (text.length > maxLength) {
		return `${text.slice(0, maxLength - 3)}...`;
	}
	return text;
}
