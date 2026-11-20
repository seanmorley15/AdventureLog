<script lang="ts">
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import ErrorState from '#lib/components/ErrorState.svelte';
	import MapOff from '~icons/mdi/map-outline';
	import CloudOff from '~icons/mdi/cloud-off-outline';

	// Inside another website: no buttons that would navigate the host's frame, just what happened.
	const unavailable = $derived(page.status >= 500);
</script>

<div class="h-[100dvh] bg-base-100">
	<ErrorState
		fullPage={false}
		compact
		icon={unavailable ? CloudOff : MapOff}
		tone={unavailable ? 'error' : 'info'}
		title={unavailable ? $t('errors.unavailable_title') : $t('errors.map_unavailable_title')}
		description={unavailable
			? $t('errors.unavailable_description')
			: $t('errors.map_unavailable_description')}
	/>
</div>
