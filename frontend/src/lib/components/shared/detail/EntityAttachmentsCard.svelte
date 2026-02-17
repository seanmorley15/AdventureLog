<script lang="ts">
	import { t } from 'svelte-i18n';
	import AttachmentCard from '$lib/components/cards/AttachmentCard.svelte';
	import LightbulbOn from '~icons/mdi/lightbulb-on';

	export let attachments: any[] = [];
	export let title: string = $t('adventures.attachments') || 'Attachments';
	export let icon: string = '📎';
	export let showGpxTip: boolean = false;
</script>

{#if attachments && attachments.length > 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-lg mb-4">
				{icon} {title}
				{#if showGpxTip}
					<div class="tooltip" data-tip={$t('adventures.gpx_tip')}>
						<LightbulbOn class="w-4 h-4 opacity-60" />
					</div>
				{/if}
			</h3>
			<div class="space-y-2">
				{#each attachments as attachment}
					<AttachmentCard {attachment} />
				{/each}
			</div>
		</div>
	</div>
{/if}
