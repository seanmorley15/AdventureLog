import { browser } from '$app/environment';

export default function useSurpriseProgress() {
	const storageKey = 'yvette_surprise_progress';

	function getProgress(): number[] {
		if (!browser) return [];
		const stored = localStorage.getItem(storageKey);
		return stored ? JSON.parse(stored) : [];
	}

	function saveProgress(steps: number[]): void {
		if (!browser) return;
		localStorage.setItem(storageKey, JSON.stringify(steps));
		window.dispatchEvent(new CustomEvent('surprise-progress', { detail: { steps } }));
	}

	function resetProgress(): void {
		if (!browser) return;
		localStorage.removeItem(storageKey);
	}

	return { getProgress, saveProgress, resetProgress };
}
