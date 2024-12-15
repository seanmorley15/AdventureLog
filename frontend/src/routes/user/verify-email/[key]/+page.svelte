<script lang="ts">
	import type { PageData } from '../$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;
</script>

{#if data.verified}
	<h1>{$t('settings.email_verified')}</h1>
	<p>{$t('settings.email_verified_success')}</p>
{:else}
	<h1>{$t('settings.email_verified_error')}</h1>
	<p>{$t('settings.email_verified_erorr_desc')}</p>
{/if}
