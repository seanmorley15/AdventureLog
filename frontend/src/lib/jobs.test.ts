import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { runExport, type Job } from './jobs';

const job = (over: Partial<Job> = {}): Job => ({
	id: 'job-1',
	kind: 'collection_pdf',
	status: 'queued',
	result: null,
	error: '',
	error_code: '',
	filename: 'Trip_trip_book.pdf',
	download_url: null,
	created_at: '',
	started_at: null,
	finished_at: null,
	expires_at: null,
	...over
});

describe('runExport', () => {
	const fetchMock = vi.fn();
	const link = { href: '', download: '', click: vi.fn(), remove: vi.fn() };

	beforeEach(() => {
		vi.useFakeTimers();
		fetchMock.mockReset();
		fetchMock
			.mockResolvedValueOnce(new Response(JSON.stringify(job()), { status: 202 }))
			.mockResolvedValueOnce(
				new Response(
					JSON.stringify(job({ status: 'succeeded', download_url: '/api/jobs/job-1/download/' })),
					{ status: 200 }
				)
			);
		vi.stubGlobal('fetch', fetchMock);
		vi.stubGlobal('document', {
			createElement: () => link,
			body: { appendChild: vi.fn() }
		});
	});

	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	async function run(options?: Parameters<typeof runExport>[1]) {
		const done = runExport('/api/collections/c1/pdf/', options);
		await vi.advanceTimersByTimeAsync(2000);
		return done;
	}

	it('sends the options as a JSON body and downloads the file', async () => {
		const done = await run({ body: { paper: 'letter', photos: false, journal: true } });

		const [url, init] = fetchMock.mock.calls[0];
		expect(url).toBe('/api/collections/c1/pdf/');
		expect(init.method).toBe('POST');
		expect(init.headers).toMatchObject({
			Prefer: 'respond-async',
			'Content-Type': 'application/json'
		});
		expect(JSON.parse(init.body)).toEqual({ paper: 'letter', photos: false, journal: true });
		expect(link.download).toBe('Trip_trip_book.pdf');
		expect(link.click).toHaveBeenCalled();
		expect(done.status).toBe('succeeded');
	});

	it('sends no body when there are no options', async () => {
		await run();

		const init = fetchMock.mock.calls[0][1];
		expect(init.body).toBeUndefined();
		expect(init.headers).not.toHaveProperty('Content-Type');
	});
});
