<script lang="ts">
	import { t } from 'svelte-i18n';
	import Eye from '~icons/mdi/eye';
	import EyeOff from '~icons/mdi/eye-off';
	import LinkVariant from '~icons/mdi/link-variant';
	import AccountMultiple from '~icons/mdi/account-multiple-outline';
	import type { CollectionVisibility } from '#lib/types.js';

	interface Props {
		visibility: CollectionVisibility;
		/** True when it sits on a photo and needs its own backdrop. */
		onPhoto?: boolean;
	}

	let { visibility, onPhoto = true }: Props = $props();
	let text = $derived($t(`share.visibility_${visibility}`));
</script>

<div class="tooltip tooltip-left" data-tip={text}>
	<span
		class="flex h-7 w-7 items-center justify-center rounded-full text-base-content {onPhoto
			? 'bg-base-100/85 shadow-xs backdrop-blur-sm'
			: 'bg-base-200'}"
		role="img"
		aria-label={text}
	>
		{#if visibility === 'public'}
			<Eye class="h-4 w-4" />
		{:else if visibility === 'unlisted'}
			<LinkVariant class="h-4 w-4" />
		{:else if visibility === 'signed_in'}
			<AccountMultiple class="h-4 w-4" />
		{:else}
			<EyeOff class="h-4 w-4" />
		{/if}
	</span>
</div>
