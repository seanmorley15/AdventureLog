import { browser } from '$app/environment';

export default function useSurpriseProgress() {
	const storageKey = 'yvette_surprise_progress';

	function getProgress(): number[] {
		if (!browser) return [];
		try {
			const stored = localStorage.getItem(storageKey);
			return stored ? JSON.parse(stored) : [];
		} catch (error) {
			console.warn('Failed to load surprise progress:', error);
			return [];
		}
	}

	function saveProgress(steps: number[]): void {
		if (!browser) return;
		try {
			localStorage.setItem(storageKey, JSON.stringify(steps));
			window.dispatchEvent(new CustomEvent('surprise-progress', { detail: { steps } }));
		} catch (error) {
			console.warn('Failed to save surprise progress:', error);
		}
	}

	function resetProgress(): void {
		if (!browser) return;
		try {
			localStorage.removeItem(storageKey);
		} catch (error) {
			console.warn('Failed to reset surprise progress:', error);
		}
	}

	return { getProgress, saveProgress, resetProgress };
}
