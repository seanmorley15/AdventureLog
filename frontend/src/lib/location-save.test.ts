import { afterEach, describe, expect, it, vi } from 'vitest';
import { saveLocation } from './location-save';

function mockFetch() {
	const fetchMock = vi.fn().mockResolvedValue({
		ok: true,
		json: async () => ({ id: 'loc-1' })
	});
	vi.stubGlobal('fetch', fetchMock);
	return fetchMock;
}

function sentBody(fetchMock: ReturnType<typeof vi.fn>) {
	return JSON.parse(fetchMock.mock.calls[0][1].body);
}

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('saveLocation', () => {
	it('never sends visits on update, so the server cannot delete them', async () => {
		const fetchMock = mockFetch();
		await saveLocation({
			location: { id: 'loc-1', name: 'West Hartford', visits: [] },
			locationToEdit: { id: 'loc-1' }
		});
		expect(fetchMock.mock.calls[0][1].method).toBe('PATCH');
		expect(sentBody(fetchMock)).not.toHaveProperty('visits');
	});

	it('never sends visits on create', async () => {
		const fetchMock = mockFetch();
		await saveLocation({ location: { name: 'New place', visits: [] } });
		expect(fetchMock.mock.calls[0][1].method).toBe('POST');
		expect(sentBody(fetchMock)).not.toHaveProperty('visits');
	});
});
