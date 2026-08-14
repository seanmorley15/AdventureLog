<script lang="ts">
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import { t } from 'svelte-i18n';
	import DOMPurify from 'dompurify';
	import FetchIcon from '~icons/mdi/download';
	import type { IntegrationsResponse } from '$lib/integrations';

	interface Props {
		text?: string | null | undefined;
		editor_height?: string;
		id?: string;
		enableFetch?: boolean;
		fetchName?: string;
		fetchLang?: string;
		fetchDisabled?: boolean;
	}

	let {
		text = $bindable(''),
		editor_height = 'h-64',
		id = undefined,
		enableFetch = false,
		fetchName = '',
		fetchLang = 'en',
		fetchDisabled = false
	}: Props = $props();

	let is_preview = $state(false);
	let isFetching = $state(false);
	let fetchError = $state('');
	let googleMapsEnabled = $state(false);

	let canFetch = $derived(enableFetch && !fetchDisabled && Boolean(fetchName?.trim()) && !isFetching);

	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	onMount(async () => {
		if (!enableFetch) return;
		try {
			const res = await fetch('/api/integrations/');
			if (!res.ok) return;
			const integrations: IntegrationsResponse = await res.json();
			googleMapsEnabled = Boolean(integrations?.google_maps);
		} catch {
			googleMapsEnabled = false;
		}
	});

	async function fetchDescription(source: 'wikipedia' | 'google') {
		const name = fetchName?.trim();
		if (!name || isFetching) return;

		isFetching = true;
		fetchError = '';

		try {
			const params = new URLSearchParams({
				name,
				lang: fetchLang || 'en',
				source
			});
			const response = await fetch(`/api/generate/desc/?${params.toString()}`);
			const data = await response.json().catch(() => ({}));
			if (response.ok && data.extract) {
				text = data.extract;
				return;
			}
			fetchError =
				source === 'google'
					? $t('adventures.google_maps_error') || 'Failed to fetch description from Google Maps'
					: $t('adventures.wikipedia_error') || 'Failed to fetch description from Wikipedia';
		} catch {
			fetchError =
				source === 'google'
					? $t('adventures.google_maps_error') || 'Failed to fetch description from Google Maps'
					: $t('adventures.wikipedia_error') || 'Failed to fetch description from Wikipedia';
		} finally {
			isFetching = false;
		}
	}
</script>

<div
	class="overflow-hidden rounded-lg border border-base-300 bg-base-100 focus-within:border-primary"
>
	<div
		class="flex items-center justify-between gap-2 border-b border-base-300 bg-base-200/50 px-2 py-1.5"
	>
		<div class="join">
			<button
				type="button"
				class={['join-item btn btn-xs h-7 min-h-7', !is_preview ? 'btn-neutral' : 'btn-ghost']}
				onclick={() => (is_preview = false)}
			>
				{$t('transportation.edit')}
			</button>
			<button
				type="button"
				class={['join-item btn btn-xs h-7 min-h-7', is_preview ? 'btn-neutral' : 'btn-ghost']}
				onclick={() => (is_preview = true)}
			>
				{$t('adventures.preview')}
			</button>
		</div>

		{#if enableFetch}
			{#if googleMapsEnabled}
				<div class="dropdown dropdown-end">
					<button
						type="button"
						tabindex="0"
						class="btn btn-ghost btn-xs h-7 min-h-7 gap-1.5"
						disabled={!canFetch}
					>
						{#if isFetching}
							<span class="loading loading-spinner loading-xs"></span>
						{:else}
							<FetchIcon class="w-3.5 h-3.5" />
						{/if}
						{$t('adventures.generate_desc')}
					</button>
					<ul
						tabindex="-1"
						class="dropdown-content menu bg-base-100 rounded-box z-30 w-44 p-1 shadow-lg border border-base-300"
					>
						<li>
							<button type="button" onclick={() => fetchDescription('wikipedia')}>
								{$t('adventures.wikipedia')}
							</button>
						</li>
						<li>
							<button type="button" onclick={() => fetchDescription('google')}>
								{$t('adventures.google_maps')}
							</button>
						</li>
					</ul>
				</div>
			{:else}
				<button
					type="button"
					class="btn btn-ghost btn-xs h-7 min-h-7 gap-1.5"
					onclick={() => fetchDescription('wikipedia')}
					disabled={!canFetch}
				>
					{#if isFetching}
						<span class="loading loading-spinner loading-xs"></span>
					{:else}
						<FetchIcon class="w-3.5 h-3.5" />
					{/if}
					{$t('adventures.generate_desc')}
				</button>
			{/if}
		{/if}
	</div>

	{#if !is_preview}
		<textarea
			{id}
			class="{editor_height} w-full min-h-0 resize-y bg-transparent p-3 leading-relaxed text-base outline-none"
			bind:value={text}
			placeholder={$t('adventures.md_instructions')}
		></textarea>
	{:else}
		<article class="prose overflow-auto {editor_height} max-w-full w-full p-3">
			{#if (text || '').trim()}
				{@html DOMPurify.sanitize(renderMarkdown(text || ''))}
			{:else}
				<p class="m-0 italic text-base-content/50">{$t('adventures.md_instructions')}</p>
			{/if}
		</article>
	{/if}

	{#if fetchError}
		<div class="border-t border-error/20 bg-error/10 px-3 py-2 text-xs text-error">
			{fetchError}
		</div>
	{/if}
</div>
