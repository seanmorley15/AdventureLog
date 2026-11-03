<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import Lost from '#lib/assets/undraw_lost.svg';

	interface Props {
		title: string;
		description?: string;
	}

	let { title, description = '' }: Props = $props();
</script>

<div class="hero min-h-[70vh] overflow-x-hidden bg-gradient-to-br from-base-200 to-base-300">
	<div class="hero-content text-center">
		<div class="max-w-md">
			<img src={Lost} alt="" class="mx-auto mb-8 w-56 opacity-80" />
			<h1 class="mb-3 text-4xl font-bold text-primary">{title}</h1>
			{#if description}
				<p class="mb-6 text-base-content/70">{description}</p>
			{/if}
			<button class="btn btn-primary" onclick={() => goto('/')}>{$t('adventures.homepage')}</button>
		</div>
	</div>
</div>
