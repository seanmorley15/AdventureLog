import { describe, expect, it } from 'vitest';
import { stripMarkdown } from './markdown';

describe('stripMarkdown', () => {
	it('removes emphasis, headings, links, images and code marks', () => {
		expect(
			stripMarkdown('# Title\n**bold** and *it* [site](https://x.y) ![alt](a.png) `code`')
		).toBe('Title\nbold and it site  code');
	});

	it('handles empty input and truncates long text', () => {
		expect(stripMarkdown(null)).toBe('');
		expect(stripMarkdown('a'.repeat(50), 10)).toBe('aaaaaaa...');
	});
});
