<script lang="ts">
	/**
	 * CardPrivacyBadge - Public/private indicator for entity cards
	 */
	import { t } from 'svelte-i18n';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';

	export let isPublic: boolean = false;
</script>

<div class="absolute top-2 right-4">
	<div
		class="tooltip tooltip-left"
		data-tip={isPublic ? $t('adventures.public') : $t('adventures.private')}
	>
		<div
			class="badge badge-sm p-1 rounded-full shadow-sm {isPublic ? 'badge-info' : 'badge-ghost'}"
			role="img"
			aria-label={isPublic ? $t('adventures.public') : $t('adventures.private')}
		>
			{#if isPublic}
				<Eye class="w-4 h-4" />
			{:else}
				<EyeOff class="w-4 h-4" />
			{/if}
		</div>
	</div>
</div>
