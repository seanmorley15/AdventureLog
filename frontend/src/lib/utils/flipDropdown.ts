const VIEWPORT_PADDING = 8;
const PAGE_EDGE_SLACK = 32;
const DEFAULT_MENU_HEIGHT = 320;

function isOverflowYScrollable(style: CSSStyleDeclaration): boolean {
	const overflowY = style.overflowY;
	return overflowY === 'auto' || overflowY === 'scroll' || overflowY === 'overlay';
}

function viewportHeight(): number {
	return window.visualViewport?.height ?? window.innerHeight;
}

/**
 * Nearest ancestor that actually scrolls. Skip body: this app sets
 * `body { overflow: hidden }` and scrolls `html` / nested drawers instead.
 */
function nearestYScroller(anchor: HTMLElement): HTMLElement | 'window' {
	let node: HTMLElement | null = anchor.parentElement;
	while (node && node !== document.body && node !== document.documentElement) {
		const style = getComputedStyle(node);
		if (isOverflowYScrollable(style) && node.scrollHeight > node.clientHeight + 1) {
			return node;
		}
		node = node.parentElement;
	}
	return 'window';
}

/** How far the user can still scroll down — not leftover layout under the trigger. */
function remainingScrollBelow(anchor: HTMLElement): number {
	const scroller = nearestYScroller(anchor);
	if (scroller !== 'window') {
		return Math.max(0, scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight);
	}

	const html = document.documentElement;
	const body = document.body;
	const top = window.scrollY || html.scrollTop;
	const htmlRemaining = html.scrollHeight - top - html.clientHeight;
	// body is overflow:hidden; its box still tracks page length and moves with window scroll
	const bodyRemaining = body.getBoundingClientRect().bottom - window.innerHeight;
	return Math.max(0, htmlRemaining, bodyRemaining);
}

function remainingScrollAbove(anchor: HTMLElement): number {
	const scroller = nearestYScroller(anchor);
	if (scroller !== 'window') return scroller.scrollTop;
	const html = document.documentElement;
	const body = document.body;
	return Math.max(0, window.scrollY || html.scrollTop, -body.getBoundingClientRect().top);
}

function menuHeight(anchor: HTMLElement, fallbackHeight: number): number {
	const content = anchor.querySelector('.dropdown-content') as HTMLElement | null;
	if (content && content.scrollHeight > 0) return content.scrollHeight;
	return fallbackHeight;
}

/**
 * Flip a downward menu upward only when the user cannot scroll further down.
 * Viewport clipping alone is not enough if the page can still move.
 */
export function shouldFlipDropdownUp(
	anchor: HTMLElement | null | undefined,
	fallbackHeight = DEFAULT_MENU_HEIGHT
): boolean {
	if (!anchor || typeof window === 'undefined') return false;

	if (remainingScrollBelow(anchor) > PAGE_EDGE_SLACK) return false;

	const rect = anchor.getBoundingClientRect();
	const spaceBelow = viewportHeight() - rect.bottom - VIEWPORT_PADDING;
	const spaceAbove = rect.top - VIEWPORT_PADDING;
	const needed = menuHeight(anchor, fallbackHeight);

	if (spaceBelow >= needed) return false;
	return spaceAbove > spaceBelow;
}

/**
 * Flip an upward menu downward only at the top of the page.
 */
export function shouldFlipDropdownDown(
	anchor: HTMLElement | null | undefined,
	fallbackHeight = DEFAULT_MENU_HEIGHT
): boolean {
	if (!anchor || typeof window === 'undefined') return false;

	if (remainingScrollAbove(anchor) > PAGE_EDGE_SLACK) return false;

	const rect = anchor.getBoundingClientRect();
	const spaceAbove = rect.top - VIEWPORT_PADDING;
	const spaceBelow = viewportHeight() - rect.bottom - VIEWPORT_PADDING;
	const needed = menuHeight(anchor, fallbackHeight);

	if (spaceAbove >= needed) return false;
	return spaceBelow > spaceAbove;
}

export function applyDropdownFlip(
	anchor: HTMLElement | null | undefined,
	fallbackHeight = DEFAULT_MENU_HEIGHT
) {
	if (!anchor) return;
	anchor.classList.toggle('dropdown-top', shouldFlipDropdownUp(anchor, fallbackHeight));
}
