<script lang="ts">
	import { t } from 'svelte-i18n';
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{$t('auth.social_login_error_title')}</title>
</svelte:head>

<div class="min-h-screen bg-base-200 flex items-center justify-center p-6">
	<div class="card bg-base-100 shadow-xl max-w-lg w-full">
		<div class="card-body space-y-4 text-center">
			<h1 class="text-2xl font-bold text-error">{$t('auth.social_login_error_title')}</h1>
			<p class="text-base-content/70">{$t('auth.social_login_error_desc')}</p>
			{#if page.url.searchParams.get('error')}
				<p class="text-sm font-mono text-base-content/50 break-all">
					{page.url.searchParams.get('error')}
				</p>
			{/if}
			<div class="card-actions justify-center pt-2">
				<a href="/login" class="btn btn-primary">{$t('auth.login')}</a>
			</div>
		</div>
	</div>
</div>
