<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import { apiErrorMessage } from '#lib/api/index.js';
	import { unlinkLocationFromCollection } from '#lib/collection-membership.js';
	import { fetchUnlinkPreview, hasTravelerImpact } from '#lib/traveler-impact.js';
	import ImpactDialog, { type ImpactPreview } from './ImpactDialog.svelte';

	/**
	 * Taking a place out of a trip, from anywhere. Asks the server who would lose their way to it
	 * (they get their own copy) before anything happens. With nobody affected and at most
	 * ``quietPlacements`` stops on the plan it just does it.
	 */
	interface Props {
		locationId: string;
		collectionId: string;
		collectionName: string;
		meUuid?: string | null;
		/** Stops on the plan the removal drops without asking, when nobody else is affected. */
		quietPlacements?: number;
		/** The place left the trip; ``removed`` stops went from the plan. */
		onunlinked: (removed: number) => void;
		onclose: () => void;
	}

	let {
		locationId,
		collectionId,
		collectionName,
		meUuid = null,
		quietPlacements = 0,
		onunlinked,
		onclose
	}: Props = $props();

	async function confirm(): Promise<boolean> {
		const change = await unlinkLocationFromCollection(locationId, collectionId);
		if (!change.ok) {
			addToast(
				'error',
				apiErrorMessage(change.error, $t('adventures.collection_remove_location_error'))
			);
			return false;
		}
		onunlinked(change.removed);
		return true;
	}

	const quiet = (preview: ImpactPreview) =>
		!hasTravelerImpact(preview) && (preview.removed_placements ?? 0) <= quietPlacements;
</script>

<ImpactDialog
	title={$t('collection.remove_from_named', { values: { name: collectionName } })}
	description={$t('traveler_impact.unlink_intro', { values: { name: collectionName } })}
	confirmLabel={$t('adventures.remove')}
	{meUuid}
	load={() => fetchUnlinkPreview(locationId, collectionId)}
	onconfirm={confirm}
	{onclose}
	{quiet}
>
	{#snippet extra(preview)}
		{#if (preview.removed_placements ?? 0) > 0}
			<p class="pb-2 text-sm">
				{$t('traveler_impact.plan_stops', {
					values: { count: preview.removed_placements ?? 0, name: collectionName }
				})}
			</p>
		{/if}
	{/snippet}
</ImpactDialog>
