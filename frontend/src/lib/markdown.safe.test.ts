import { describe, expect, it } from 'vitest';
import { htmlToText, isSafeUrl, renderMarkdown } from './markdown';

// Payloads from GHSA-hmf9-87cx-w5vj, GHSA-gp78-2vpr-42q5, GHSA-884j-3wwv-x5c4 and GHSA-mcrf-2xj6-8f3w,
// plus the usual markdown link/image tricks.
const PAYLOADS = [
	'<img src=x onerror="document.title=\'XSS\'">',
	'<script>alert(1)</script>',
	'hello <img src=x onerror=alert(1)> world',
	'<svg/onload=alert(1)>',
	'<iframe src="javascript:alert(1)"></iframe>',
	'<a href="javascript:alert(1)">x</a>',
	'<details open ontoggle=alert(1)>',
	'[x](javascript:alert(1))',
	'[x](JaVaScRiPt:alert(1))',
	'[x](java\tscript:alert(1))',
	'[x](javascript&#58;alert(1))',
	'[x](javascript&#x3A;alert(1))',
	'[x](javascript&colon;alert(1))',
	'[x](data:text/html,<script>alert(1)</script>)',
	'[x](vbscript:msgbox(1))',
	'![x](javascript:alert(1))',
	'<javascript:alert(1)>',
	'[x][ref]\n\n[ref]: javascript:alert(1)',
	'[x](" onmouseover="alert(1))',
	'![x](x" onerror="alert(1))',
	'[x](<" onmouseover="alert(1)>)',
	'![x](<x" onerror="alert(1)>)',
	'[x](https://ok.example "t\\" onmouseover=\\"alert(1)")',
	'`<img src=x onerror=alert(1)>`',
	'```\n<script>alert(1)</script>\n```'
];

const ALLOWED_TAGS = new Set([
	'p',
	'br',
	'hr',
	'h1',
	'h2',
	'h3',
	'h4',
	'h5',
	'h6',
	'strong',
	'em',
	'del',
	'code',
	'pre',
	'blockquote',
	'ul',
	'ol',
	'li',
	'a',
	'img',
	'table',
	'thead',
	'tbody',
	'tr',
	'th',
	'td',
	'input'
]);
const ALLOWED_ATTRS = new Set([
	'href',
	'src',
	'alt',
	'title',
	'class',
	'align',
	'start',
	'type',
	'checked',
	'disabled'
]);

// Every real tag in the output (escaped text is `&lt;`, never `<`) must be a plain markdown
// element with quoted, known attributes, and every address must have a safe scheme.
function assertInert(html: string) {
	for (const match of html.matchAll(/<\/?([a-zA-Z0-9]+)([^>]*)>/g)) {
		const [, tag, rest] = match;
		expect(ALLOWED_TAGS.has(tag.toLowerCase()), `tag <${tag}> in ${html}`).toBe(true);
		const attrs = rest.replace(/\/$/, '').trim();
		const leftover = attrs.replace(/([a-zA-Z-]+)(="[^"]*")?/g, (_, name, value) => {
			expect(ALLOWED_ATTRS.has(name.toLowerCase()), `attribute ${name} in ${html}`).toBe(true);
			if (/^(href|src)$/i.test(name)) {
				const url = (value ?? '=""').slice(2, -1).replace(/&amp;/g, '&');
				expect(isSafeUrl(url), `unsafe url ${url}`).toBe(true);
			}
			return '';
		});
		expect(leftover.trim(), `unparsed attributes in ${match[0]}`).toBe('');
	}
}

describe('renderMarkdown', () => {
	it.each(PAYLOADS)('renders %j inert', (payload) => {
		assertInert(renderMarkdown(payload));
	});

	it('keeps ordinary markdown', () => {
		const html = renderMarkdown('# Day 1\n\n**Bold** [map](https://example.com/a?b=1&c=2) `x`');
		expect(html).toContain('<h1>Day 1</h1>');
		expect(html).toContain('<strong>Bold</strong>');
		expect(html).toContain('<a href="https://example.com/a?b=1&c=2">map</a>');
		expect(html).toContain('<code>x</code>');
	});

	it('shows raw HTML as text instead of dropping it', () => {
		expect(renderMarkdown('a <b>b</b>')).toContain('&lt;b&gt;b&lt;/b&gt;');
	});

	it('keeps relative, mailto and tel links', () => {
		expect(renderMarkdown('[a](/locations/1) [b](mailto:a@b.c) [c](tel:123) [d](#x)')).toMatch(
			/href="\/locations\/1".*href="mailto:a@b.c".*href="tel:123".*href="#x"/
		);
	});

	it('handles empty input', () => {
		expect(renderMarkdown(null)).toBe('');
		expect(renderMarkdown('')).toBe('');
	});
});

describe('htmlToText', () => {
	it('drops tags and script bodies', () => {
		expect(
			htmlToText('<p>Nice <b>trail</b></p><script>alert(1)</script><img src=x onerror=alert(1)>')
		).toBe('Nice trail');
	});

	it('decodes entities once, leaving the result for Svelte to escape', () => {
		expect(htmlToText('&lt;img src=x onerror=alert(1)&gt;')).toBe('<img src=x onerror=alert(1)>');
	});
});
