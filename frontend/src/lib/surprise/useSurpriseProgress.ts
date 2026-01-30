import { browser } from '$app/environment';

export function useSurpriseProgress() {
	const storageKey = 'yvette_surprise_progress';

	function getProgress(): number {
		if (!browser) return 0;
		const stored = localStorage.getItem(storageKey);
		return stored ? parseInt(stored, 10) : 0;
	}

	function setProgress(step: number): void {
		if (!browser) return;
		localStorage.setItem(storageKey, String(step));
		window.dispatchEvent(new CustomEvent('surprise-progress', { detail: { step } }));
	}

	function advanceProgress(): number {
		const current = getProgress();
		const newStep = Math.min(current + 1, 6);
		setProgress(newStep);
		return newStep;
	}

	function resetProgress(): void {
		if (!browser) return;
		localStorage.removeItem(storageKey);
	}

	return { getProgress, setProgress, advanceProgress, resetProgress };
}
