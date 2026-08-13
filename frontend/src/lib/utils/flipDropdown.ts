const VIEWPORT_PADDING = 8;
const DEFAULT_MENU_HEIGHT = 320;

/**
 * Returns true when a daisyUI dropdown should open upward (`dropdown-top`)
 * because there is not enough viewport space below the trigger.
 */
export function shouldFlipDropdownUp(
	anchor: HTMLElement | null | undefined,
	fallbackHeight = DEFAULT_MENU_HEIGHT
): boolean {
	if (!anchor || typeof window === 'undefined') return false;

	const rect = anchor.getBoundingClientRect();
	const spaceBelow = window.innerHeight - rect.bottom - VIEWPORT_PADDING;
	const spaceAbove = rect.top - VIEWPORT_PADDING;
	const content = anchor.querySelector('.dropdown-content') as HTMLElement | null;
	const needed = Math.max(fallbackHeight, content?.scrollHeight ?? 0);

	return spaceBelow < needed && spaceAbove > spaceBelow;
}
