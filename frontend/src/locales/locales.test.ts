import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';
import { KNOWN_MISSING_KEYS } from './known-missing-keys';

const KNOWN_MISSING = new Set(KNOWN_MISSING_KEYS);

const SRC = join(import.meta.dirname, '..');

function walk(dir: string, out: string[] = []): string[] {
	for (const entry of readdirSync(dir)) {
		const full = join(dir, entry);
		if (statSync(full).isDirectory()) walk(full, out);
		else if (/\.(svelte|ts)$/.test(entry) && !/\.test\.ts$/.test(entry)) out.push(full);
	}
	return out;
}

function flatten(obj: Record<string, unknown>, prefix = '', out = new Set<string>()) {
	for (const [key, value] of Object.entries(obj)) {
		const path = prefix ? `${prefix}.${key}` : key;
		if (value && typeof value === 'object') flatten(value as Record<string, unknown>, path, out);
		else out.add(path);
	}
	return out;
}

const en = JSON.parse(readFileSync(join(SRC, 'locales/en.json'), 'utf8'));
const defined = flatten(en);

// Matches $t('a.b'), $t("a.b"), $_('a.b') and $t(`a.b`) with a plain string literal.
// Dynamic keys (template strings with ${...}) cannot be checked statically and are skipped.
const KEY_CALL = /\$[t_]\(\s*(['"`])([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)\1/g;

function usedKeys() {
	const used = new Map<string, string[]>();
	for (const file of walk(SRC)) {
		const text = readFileSync(file, 'utf8');
		for (const match of text.matchAll(KEY_CALL)) {
			const where = used.get(match[2]) ?? [];
			where.push(relative(SRC, file));
			used.set(match[2], where);
		}
	}
	return used;
}

describe('English translations', () => {
	const used = usedKeys();

	it('define every statically referenced key (beyond the known baseline)', () => {
		const missing = [...used]
			.filter(([key]) => !defined.has(key) && !KNOWN_MISSING.has(key))
			.map(([key, files]) => `${key}  (${[...new Set(files)].join(', ')})`)
			.sort();

		expect(missing, 'new keys used in code but missing from locales/en.json').toEqual([]);
	});

	it('keep the known-missing baseline honest', () => {
		const fixed = [...KNOWN_MISSING].filter((key) => defined.has(key) || !used.has(key));
		expect(fixed, 'now defined or unused: remove these from KNOWN_MISSING').toEqual([]);
	});
});
