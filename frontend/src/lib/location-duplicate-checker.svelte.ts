import {
	canCheckDuplicates,
	checkDuplicateLocations,
	duplicateCheckFingerprint,
	type DuplicateCheckInput
} from '$lib/location-duplicates';
import type { DuplicateLocationMatch } from '$lib/types';

export class LocationDuplicateChecker {
	matches = $state.raw<DuplicateLocationMatch[]>([]);
	checking = $state(false);
	ignored = $state(false);

	#timer: ReturnType<typeof setTimeout> | null = null;
	#requestId = 0;
	#lastKey = '';
	#ignoredKey = '';
	#inflight: Promise<void> | null = null;
	#queued: DuplicateCheckInput | null = null;

	get blocking(): boolean {
		return !this.ignored && this.matches.length > 0;
	}

	get visible(): boolean {
		return !this.ignored && (this.checking || this.matches.length > 0);
	}

	schedule = (input: DuplicateCheckInput, delayMs = 350) => {
		const key = duplicateCheckFingerprint(input);
		this.#queued = input;

		if (this.ignored && key === this.#ignoredKey) {
			return;
		}
		if (this.ignored && key !== this.#ignoredKey) {
			this.ignored = false;
			this.#ignoredKey = '';
		}

		if (!canCheckDuplicates(input)) {
			this.cancel();
			this.matches = [];
			this.checking = false;
			this.#lastKey = key;
			return;
		}

		if (key === this.#lastKey && !this.#timer && this.#inflight == null) {
			return;
		}

		this.checking = true;
		if (this.#timer) clearTimeout(this.#timer);
		this.#timer = setTimeout(() => {
			this.#timer = null;
			void this.#run(input, key);
		}, delayMs);
	};

	flush = async () => {
		if (this.#timer && this.#queued) {
			clearTimeout(this.#timer);
			this.#timer = null;
			const input = this.#queued;
			await this.#run(input, duplicateCheckFingerprint(input));
			return;
		}
		if (this.#inflight) {
			await this.#inflight;
		}
	};

	ignoreCurrent = () => {
		this.ignored = true;
		this.#ignoredKey = this.#queued ? duplicateCheckFingerprint(this.#queued) : this.#lastKey;
	};

	reset = () => {
		this.cancel();
		this.matches = [];
		this.checking = false;
		this.ignored = false;
		this.#lastKey = '';
		this.#ignoredKey = '';
		this.#queued = null;
	};

	cancel = () => {
		if (this.#timer) {
			clearTimeout(this.#timer);
			this.#timer = null;
		}
		this.#requestId += 1;
	};

	destroy = () => {
		this.cancel();
	};

	#run = async (input: DuplicateCheckInput, key: string) => {
		const requestId = ++this.#requestId;
		this.checking = true;
		const pending = checkDuplicateLocations(input)
			.then((matches) => {
				if (requestId !== this.#requestId) return;
				this.#lastKey = key;
				this.matches = matches;
			})
			.finally(() => {
				if (requestId === this.#requestId) {
					this.checking = false;
					this.#inflight = null;
				}
			});
		this.#inflight = pending;
		await pending;
	};
}
