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
