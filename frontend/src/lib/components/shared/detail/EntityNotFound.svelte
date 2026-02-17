<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import Lost from '$lib/assets/undraw_lost.svg';

	export let title: string = $t('adventures.location_not_found') || 'Not Found';
	export let description: string = $t('adventures.location_not_found_desc') || 'The item you are looking for could not be found.';
</script>

<div class="hero min-h-screen bg-gradient-to-br from-base-200 to-base-300 overflow-x-hidden">
	<div class="hero-content text-center">
		<div class="max-w-md">
			<img src={Lost} alt="Lost" class="w-64 mx-auto mb-8 opacity-80" />
			<h1 class="text-5xl font-bold text-primary mb-4">{title}</h1>
			<p class="text-lg opacity-70 mb-8">{description}</p>
			<button class="btn btn-primary btn-lg" on:click={() => goto('/')}>
				{$t('adventures.homepage')}
			</button>
		</div>
	</div>
</div>
