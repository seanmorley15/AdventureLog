<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import { getSearchTypeIcon } from '$lib/search/icons';
	import type { SearchEntityType, SearchHit } from '$lib/search/types';

	export let hit: SearchHit;
	export let selected = false;
	export let compact = false;
	export let spotlight = false;

	const dispatch = createEventDispatcher<{ select: SearchHit }>();

	function typeLabel(type: SearchEntityType): string {
		const key = `search.types.${type}`;
		const translated = $t(key);
		return translated === key ? type : translated;
	}

	$: emojiIcon =
		hit.type === 'location' && hit.meta?.category_icon
			? String(hit.meta.category_icon)
			: null;

	$: rowClass = [
		'w-full text-left flex items-center gap-3 transition-colors',
		spotlight ? 'mx-2 px-3 py-2.5 rounded-xl' : compact ? 'px-4 py-2 rounded-lg' : 'px-4 py-3 rounded-lg',
		selected
			? 'bg-primary text-primary-content'
			: spotlight
				? 'bg-base-200/25 hover:bg-base-200/45'
				: 'hover:bg-base-200'
	].join(' ');
</script>

<button
	type="button"
	class={rowClass}
	on:click={() => dispatch('select', hit)}
>
	<div
		class="flex shrink-0 items-center justify-center rounded-xl"
		class:h-10={spotlight}
		class:w-10={spotlight}
		class:text-2xl={spotlight && emojiIcon}
		class:h-9={!spotlight}
		class:w-9={!spotlight}
		class:text-xl={!spotlight && emojiIcon}
		class:bg-primary-content={selected}
		class:text-primary={selected && !emojiIcon}
		class:bg-base-200={!selected}
		class:text-base-content={!selected && !emojiIcon}
	>
		{#if emojiIcon}
			<span aria-hidden="true">{emojiIcon}</span>
		{:else}
			<svelte:component this={getSearchTypeIcon(hit.type)} class={spotlight ? 'w-5 h-5' : 'w-4 h-4'} />
		{/if}
	</div>

	<div class="min-w-0 flex-1">
		<div class="flex items-start justify-between gap-3 min-w-0">
			<div class="min-w-0 flex-1">
				<p class="font-medium truncate leading-snug">{hit.title}</p>
				{#if hit.subtitle}
					<p
						class="truncate leading-snug mt-0.5"
						class:text-sm={spotlight}
						class:opacity-70={selected}
						class:text-base-content={!selected}
						class:opacity-60={!selected}
					>
						{hit.subtitle}
					</p>
				{/if}
			</div>
			<div class="flex flex-wrap items-center justify-end gap-1 shrink-0 max-w-[45%]">
				<span
					class="badge badge-xs whitespace-nowrap"
					class:badge-primary={selected}
					class:badge-ghost={!selected}
				>
					{typeLabel(hit.type)}
				</span>
				{#if hit.meta?.is_visited}
					<span class="badge badge-xs badge-success whitespace-nowrap">{$t('search.visited')}</span>
				{/if}
				{#if hit.meta?.is_shared}
					<span class="badge badge-xs badge-info whitespace-nowrap">{$t('navbar.shared_with_me')}</span>
				{/if}
			</div>
		</div>
	</div>
</button>
