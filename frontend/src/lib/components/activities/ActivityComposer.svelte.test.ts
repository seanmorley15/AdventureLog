import { afterEach, describe, expect, it, vi } from 'vitest';
import { page, userEvent } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';
import { addMessages, init } from 'svelte-i18n';
import en from '../../../locales/en.json';
import ActivityComposer from './ActivityComposer.svelte';
import type { ActivityAnalysis } from '#lib/types.js';

// The composer's import chain reaches SvelteKit modules that only exist inside the app.
vi.mock('$app/env/public', () => ({ PUBLIC_CARTO_BASEMAP_API_KEY: '' }));
vi.mock('$app/state', () => ({ page: { data: {} } }));

addMessages('en', en);
init({ fallbackLocale: 'en', initialLocale: 'en' });

const analysis: ActivityAnalysis = {
	values: {
		name: 'Ridge walk',
		sport_type: 'Hike',
		distance: 12000,
		moving_time: '02:30:00',
		elapsed_time: '03:00:00',
		elevation_gain: 640,
		start_date: '2026-06-06T08:00:00Z',
		average_heart_rate: 132
	},
	sources: { distance: 'device', elevation_gain: 'computed' },
	format: 'fit',
	point_count: 900,
	has_timestamps: true,
	has_elevation: true,
	utc_offset_minutes: null,
	warnings: [],
	geojson: null
};

function json(body: unknown, status = 200) {
	return Promise.resolve(
		new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
	);
}

/** Answer the three endpoints the composer talks to, and remember what it sent. */
function mockApi(analyzeStatus = 200) {
	const sent: { url: string; method: string; body: FormData | null }[] = [];
	vi.stubGlobal(
		'fetch',
		vi.fn((url: string, init?: RequestInit) => {
			sent.push({ url, method: init?.method ?? 'GET', body: (init?.body as FormData) ?? null });
			if (url === '/api/integrations') return json({});
			if (url === '/api/activities/analyze/') {
				return analyzeStatus === 200
					? json(analysis)
					: json({ detail: 'This FIT file is not valid.', code: 'activity.unreadable_track' }, 400);
			}
			return json({ id: 'new-activity' }, 201);
		})
	);
	return sent;
}

async function dropFile(name = 'ridge.fit') {
	const input = page.getByLabelText(/drop an activity file/i);
	await userEvent.upload(input, new File(['x'], name));
}

afterEach(() => vi.unstubAllGlobals());

describe('ActivityComposer', () => {
	it('offers the file first, with manual entry as the quiet option', async () => {
		mockApi();
		render(ActivityComposer, { visitId: 'visit-1', onSaved: () => {} });
		await expect.element(page.getByText('Drop an activity file here')).toBeVisible();
		await expect.element(page.getByRole('button', { name: 'Enter manually' })).toBeVisible();
	});

	it('fills the form from a dropped file and saves the file with it', async () => {
		const sent = mockApi();
		const onSaved = vi.fn();
		render(ActivityComposer, { visitId: 'visit-1', timezone: 'UTC', onSaved });

		await dropFile();

		await expect.element(page.getByLabelText(/activity name/i)).toHaveValue('Ridge walk');
		await expect.element(page.getByLabelText(/^Distance/)).toHaveValue(12);
		await expect.element(page.getByLabelText(/elevation gain/i)).toHaveValue(640);
		await expect.element(page.getByText('from device')).toBeVisible();

		await page.getByRole('button', { name: 'Upload Activity' }).click();

		const save = sent.find((request) => request.url === '/api/activities/');
		expect(save?.method).toBe('POST');
		expect(save?.body?.get('visit')).toBe('visit-1');
		expect(save?.body?.get('distance')).toBe('12000');
		expect(save?.body?.get('moving_time')).toBe('PT9000S');
		expect((save?.body?.get('gpx_file') as File).name).toBe('ridge.fit');
		expect(onSaved).toHaveBeenCalledOnce();
	});

	it('attaches to a trip day or to Ideas when given one instead of a visit', async () => {
		const sent = mockApi();
		render(ActivityComposer, { dayId: 'day-3', timezone: 'UTC', onSaved: () => {} });
		await dropFile();
		await page.getByRole('button', { name: 'Upload Activity' }).click();
		const save = sent.find((request) => request.url === '/api/activities/');
		expect(save?.body?.get('day')).toBe('day-3');
		expect(save?.body?.get('visit')).toBeNull();
	});

	it('stays on the file step and shows the reason when the file cannot be read', async () => {
		mockApi(400);
		render(ActivityComposer, { visitId: 'visit-1', onSaved: () => {} });
		await dropFile('broken.fit');
		await expect.element(page.getByText('Drop an activity file here')).toBeVisible();
	});

	it('still lets someone enter an activity by hand', async () => {
		const sent = mockApi();
		render(ActivityComposer, { visitId: 'visit-1', timezone: 'UTC', onSaved: () => {} });
		await page.getByRole('button', { name: 'Enter manually' }).click();
		await page.getByLabelText(/activity name/i).fill('Evening stroll');
		await page.getByRole('button', { name: 'Upload Activity' }).click();
		const save = sent.find((request) => request.url === '/api/activities/');
		expect(save?.body?.get('name')).toBe('Evening stroll');
		expect(save?.body?.get('gpx_file')).toBeNull();
	});

	it('edits a saved activity with a PATCH and no parent', async () => {
		const sent = mockApi();
		const saved = {
			id: 'a1',
			name: 'Old name',
			sport_type: 'Run',
			distance: 5000,
			timezone: 'UTC',
			trail: null,
			gpx_file: '/media/activities/a1.gpx'
		};
		render(ActivityComposer, {
			visitId: 'visit-1',
			activity: saved as never,
			timezone: 'UTC',
			onSaved: () => {}
		});
		await expect.element(page.getByLabelText(/activity name/i)).toHaveValue('Old name');
		await page.getByLabelText(/activity name/i).fill('New name');
		await page.getByRole('button', { name: 'Save changes' }).click();
		const save = sent.find((request) => request.url === '/api/activities/a1/');
		expect(save?.method).toBe('PATCH');
		expect(save?.body?.get('name')).toBe('New name');
	});
});
