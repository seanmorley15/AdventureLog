/**
 * Background jobs: exports, imports and PDFs the server makes in a worker.
 *
 * An endpoint answers `202` with a job when asked with `Prefer: respond-async`. Poll the job until it
 * finishes; an export then has a `download_url`. See "Background jobs" in backend/server/API.md.
 */

export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export interface Job {
	id: string;
	kind: string;
	status: JobStatus;
	/** What the job produced: counts, the id of what it created. */
	result: Record<string, any> | null;
	error: string;
	error_code: string;
	filename: string;
	download_url: string | null;
	created_at: string;
	started_at: string | null;
	finished_at: string | null;
	expires_at: string | null;
}

/** A job that failed, was cancelled, or could not be started. `message` is safe to show. */
export class JobError extends Error {
	code: string;
	job?: Job;

	constructor(message: string, code = 'job_failed', job?: Job) {
		super(message);
		this.name = 'JobError';
		this.code = code;
		this.job = job;
	}
}

const FIRST_POLL_MS = 1000;
const SLOWEST_POLL_MS = 5000;
/** A job that has not finished by then is left running on the server; the page stops waiting. */
const GIVE_UP_AFTER_MS = 30 * 60 * 1000;

const isFinished = (job: Job) => ['succeeded', 'failed', 'cancelled'].includes(job.status);

async function errorFrom(res: Response, fallback: string): Promise<JobError> {
	let detail = fallback;
	let code = 'invalid';
	try {
		const body = await res.json();
		detail = body.detail || fallback;
		code = body.code || code;
	} catch {
		// not JSON
	}
	return new JobError(detail, code);
}

/** Start a job. Throws a `JobError` with the server's message if it was refused (400, 403, 413...). */
export async function startJob(url: string, init: RequestInit = {}): Promise<Job> {
	const res = await fetch(url, {
		method: 'POST',
		...init,
		headers: { ...(init.headers as Record<string, string>), Prefer: 'respond-async' }
	});
	if (res.status !== 202) {
		throw await errorFrom(res, 'The job could not be started.');
	}
	return (await res.json()) as Job;
}

const sleep = (ms: number, signal?: AbortSignal) =>
	new Promise<void>((resolve, reject) => {
		const timer = setTimeout(resolve, ms);
		signal?.addEventListener('abort', () => {
			clearTimeout(timer);
			reject(new DOMException('Aborted', 'AbortError'));
		});
	});

/**
 * Poll a job until it succeeds. Throws a `JobError` when it fails or is cancelled.
 * `onUpdate` sees every poll, for a progress label.
 */
export async function waitForJob(
	id: string,
	options: { signal?: AbortSignal; onUpdate?: (job: Job) => void } = {}
): Promise<Job> {
	const started = Date.now();
	let delay = FIRST_POLL_MS;
	for (;;) {
		await sleep(delay, options.signal);
		const res = await fetch(`/api/jobs/${id}/`, { signal: options.signal });
		if (!res.ok) throw await errorFrom(res, 'The job could not be read.');
		const job = (await res.json()) as Job;
		options.onUpdate?.(job);
		if (isFinished(job)) {
			if (job.status === 'succeeded') return job;
			throw new JobError(job.error || 'The job did not finish.', job.error_code || job.status, job);
		}
		if (Date.now() - started > GIVE_UP_AFTER_MS) {
			throw new JobError('The job is taking too long. Check back later.', 'job_timeout', job);
		}
		delay = Math.min(delay * 1.5, SLOWEST_POLL_MS);
	}
}

/** Save a finished job's file with the browser's download. */
export function downloadJobFile(job: Job): void {
	if (!job.download_url) {
		throw new JobError('This job has no file to download.', 'not_found', job);
	}
	const link = document.createElement('a');
	link.href = job.download_url;
	link.download = job.filename;
	document.body.appendChild(link);
	link.click();
	link.remove();
}

/**
 * Start an export, wait for it, and download the file. `body` is sent as JSON, for exports that
 * take options (the PDF's paper size, for one).
 */
export async function runExport(
	url: string,
	options: { signal?: AbortSignal; onUpdate?: (job: Job) => void; body?: unknown } = {}
): Promise<Job> {
	const started = await startJob(
		url,
		options.body === undefined
			? {}
			: { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(options.body) }
	);
	const done = await waitForJob(started.id, options);
	downloadJobFile(done);
	return done;
}

/** The message to show for anything thrown while running a job. */
export function jobErrorMessage(error: unknown, fallback: string): string {
	return error instanceof JobError && error.message ? error.message : fallback;
}
