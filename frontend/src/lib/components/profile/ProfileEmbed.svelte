<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '#lib/toasts.js';
	import type { User } from '#lib/types.js';

	import CodeTags from '~icons/mdi/code-tags';
	import ContentCopy from '~icons/mdi/content-copy';
	import Lock from '~icons/mdi/lock-outline';

	interface Props {
		profile: User;
	}

	let { profile }: Props = $props();

	let height = $state(450);
	let theme = $state<'light' | 'dark'>('light');
	let layout = $state<'open' | 'collapsed'>('open');
	const embeddable = $derived(profile.profile_visibility === 'public');

	const src = $derived(
		`${typeof window === 'undefined' ? '' : window.location.origin}/embed/profile/${encodeURIComponent(profile.username)}?theme=${theme}${layout === 'collapsed' ? '&profile=hide' : ''}`
	);
	const snippet = $derived(
		`<iframe src="${src}" width="100%" height="${height}" style="border:0;border-radius:12px" loading="lazy" title="${profile.username} on AdventureLog"></iframe>`
	);

	async function copy() {
		try {
			await navigator.clipboard.writeText(snippet);
			addToast('success', $t('profile.embed_copied'));
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}
</script>

<div class="collapse collapse-arrow mt-4 rounded-box border border-base-300/60 bg-base-100">
	<input type="checkbox" aria-label={$t('profile.embed_title')} />
	<div class="collapse-title flex items-center gap-2 font-semibold">
		<CodeTags class="h-5 w-5 text-primary" />
		{$t('profile.embed_title')}
	</div>
	<div class="collapse-content space-y-4">
		{#if !embeddable}
			<div class="flex items-start gap-3 rounded-lg bg-warning/10 p-3 text-sm">
				<Lock class="mt-0.5 h-4 w-4 shrink-0 text-warning" />
				<p>
					{$t('profile.embed_needs_public')}
					<a href="/settings" class="link link-primary">{$t('navbar.settings')}</a>
				</p>
			</div>
		{:else}
			<p class="text-sm text-base-content/60">{$t('profile.embed_hint')}</p>
			<div class="flex flex-wrap gap-4">
				<label class="form-control">
					<span class="label-text mb-1 text-xs">{$t('profile.embed_height')}</span>
					<input
						type="number"
						min="200"
						max="1200"
						step="50"
						class="input input-sm input-bordered w-28"
						bind:value={height}
					/>
				</label>
				<label class="form-control">
					<span class="label-text mb-1 text-xs">{$t('profile.embed_layout')}</span>
					<select class="select select-sm select-bordered" bind:value={layout}>
						<option value="open">{$t('profile.embed_layout_open')}</option>
						<option value="collapsed">{$t('profile.embed_layout_collapsed')}</option>
					</select>
				</label>
				<label class="form-control">
					<span class="label-text mb-1 text-xs">{$t('profile.embed_theme')}</span>
					<select class="select select-sm select-bordered" bind:value={theme}>
						<option value="light">{$t('profile.embed_theme_light')}</option>
						<option value="dark">{$t('profile.embed_theme_dark')}</option>
					</select>
				</label>
			</div>
			<div class="relative">
				<textarea
					readonly
					rows="4"
					class="textarea textarea-bordered w-full font-mono text-xs"
					value={snippet}
					onfocus={(e) => e.currentTarget.select()}
				></textarea>
				<button class="btn btn-sm btn-primary absolute right-2 top-2 gap-1" onclick={copy}>
					<ContentCopy class="h-4 w-4" />
					{$t('profile.embed_copy')}
				</button>
			</div>
		{/if}
	</div>
</div>
