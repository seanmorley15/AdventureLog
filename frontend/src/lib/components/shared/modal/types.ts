/**
 * Shared types for entity modals (Location, Transportation, Lodging)
 */

/**
 * Represents a step in the modal wizard
 */
export interface ModalStep {
	name: string;
	selected: boolean;
	requires_id: boolean;
}

/**
 * Base props shared by all entity modals
 */
export interface BaseEntityModalProps {
	user: import('$lib/types').User | null;
	collection: import('$lib/types').Collection | null;
	initialVisitDate: string | null;
}

/**
 * Icon configuration for modal headers
 */
export interface ModalIconConfig {
	component?: any; // Svelte component (icon)
	svg?: string; // SVG path for inline icons
	class?: string;
}

/**
 * Configuration for modal header
 */
export interface ModalHeaderConfig {
	icon: ModalIconConfig;
	editTitle: string;
	newTitle: string;
	editSubtitle: string;
	newSubtitle: string;
}

/**
 * Events dispatched by entity modals
 */
export interface EntityModalEvents {
	save: CustomEvent<any>;
	create: CustomEvent<any>;
	close: CustomEvent<void>;
}

/**
 * Step navigation handler type
 */
export type StepNavigationHandler = (stepIndex: number) => void;

/**
 * Create default steps for modals
 * @param includeQuickStart - Whether to include a quick start step (Location modal)
 * @param t - Translation function
 */
export function createDefaultSteps(
	t: (key: string) => string,
	includeQuickStart: boolean = false
): ModalStep[] {
	if (includeQuickStart) {
		return [
			{ name: t('adventures.quick_start'), selected: true, requires_id: false },
			{ name: t('adventures.details'), selected: false, requires_id: false },
			{ name: t('settings.media'), selected: false, requires_id: true },
			{ name: t('adventures.visits'), selected: false, requires_id: true }
		];
	}
	return [
		{ name: t('adventures.details'), selected: true, requires_id: false },
		{ name: t('adventures.visits'), selected: false, requires_id: true },
		{ name: t('settings.media'), selected: false, requires_id: true }
	];
}

/**
 * Navigate to a specific step
 */
export function navigateToStep(steps: ModalStep[], targetIndex: number): ModalStep[] {
	return steps.map((step, index) => ({
		...step,
		selected: index === targetIndex
	}));
}

/**
 * Find the currently selected step index
 */
export function getCurrentStepIndex(steps: ModalStep[]): number {
	return steps.findIndex((step) => step.selected);
}

/**
 * Check if navigation to a step is allowed
 */
export function canNavigateToStep(steps: ModalStep[], targetIndex: number, entityId: string): boolean {
	const targetStep = steps[targetIndex];
	if (!targetStep) return false;
	if (targetStep.requires_id && !entityId) return false;
	return true;
}
