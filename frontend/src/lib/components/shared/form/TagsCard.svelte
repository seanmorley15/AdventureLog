<script lang="ts">
	/**
	 * TagsCard - Shared tags section card for entity forms
	 */
	import { t } from 'svelte-i18n';
	import TagComplete from '../../TagComplete.svelte';

	export let tags: string[] = [];
</script>

<div class="card bg-base-100 border border-base-300 shadow-lg">
	<div class="card-body p-6">
		<div class="flex items-center gap-3 mb-6">
			<div class="p-2 bg-warning/10 rounded-lg">
				<svg class="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
					/>
				</svg>
			</div>
			<h2 class="text-xl font-bold">{$t('adventures.tags')} ({tags?.length || 0})</h2>
		</div>
		<div class="space-y-4">
			<input type="text" id="tags" name="tags" hidden bind:value={tags} />
			<TagComplete bind:tags />
		</div>
	</div>
</div>
