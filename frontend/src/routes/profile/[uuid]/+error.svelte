<script lang="ts">
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import NotFound from '#lib/components/NotFound.svelte';
	import AlertCircle from '~icons/mdi/alert-circle-outline';
</script>

{#if page.status === 404}
	<NotFound error={undefined} />
{:else}
	<div class="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
		<AlertCircle class="h-12 w-12 text-warning" />
		<h1 class="text-2xl font-bold">{$t('profile.error_title')}</h1>
		<p class="max-w-md text-base-content/60">{$t('profile.error_hint')}</p>
		<div class="flex gap-2">
			<button class="btn btn-primary" onclick={() => location.reload()}
				>{$t('profile.retry')}</button
			>
			<a href="/users" class="btn btn-ghost">{$t('profile.back_to_profiles')}</a>
		</div>
	</div>
{/if}
