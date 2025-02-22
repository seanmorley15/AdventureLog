<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';

	import MapWithPins from '$lib/assets/MapWithPins.webp';
	import type { Background } from '$lib/types.js';

	export let data;

	let background: Background = data.props?.background ?? { url: '' };
</script>

<!-- Hero Section -->
<section class="flex items-center justify-center w-full py-20 bg-gray-50 dark:bg-gray-800">
	<div class="container mx-auto px-4 flex flex-col-reverse md:flex-row items-center gap-8">
		<!-- Text Content -->
		<div class="w-full md:w-1/2 space-y-6">
			{#if data.user}
				{#if data.user.first_name && data.user.first_name !== null}
					<h1
						class="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						{data.user.first_name.charAt(0).toUpperCase() + data.user.first_name.slice(1)}, {$t(
							'home.hero_1'
						)}
					</h1>
				{:else}
					<h1
						class="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
					>
						{$t('home.hero_1')}
					</h1>
				{/if}
			{:else}
				<h1
					class="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
				>
					{$t('home.hero_1')}
				</h1>
			{/if}
			<p class="text-xl text-gray-600 dark:text-gray-300 max-w-xl">
				{$t('home.hero_2')}
			</p>
			<div class="flex flex-col sm:flex-row gap-4">
				{#if data.user}
					<button on:click={() => goto('/adventures')} class="btn btn-primary">
						{$t('home.go_to')}
					</button>
				{:else}
					<button on:click={() => goto('/login')} class="btn btn-primary">
						{$t('auth.login')}
					</button>
					<button on:click={() => goto('/signup')} class="btn btn-secondary">
						{$t('auth.signup')}
					</button>
				{/if}
			</div>
		</div>
		<!-- Image -->
		<div class="w-full md:w-1/2">
			<img
				src={background.url}
				alt={background.location}
				class="rounded-lg shadow-lg object-cover w-full h-full"
			/>
		</div>
	</div>
</section>

<!-- Features Section -->
<section id="features" class="py-16 bg-white dark:bg-gray-900">
	<div class="container mx-auto px-4">
		<div class="text-center mb-12">
			<div class="inline-block text-neutral-content bg-neutral px-4 py-2 rounded-full">
				{$t('home.key_features')}
			</div>
			<h2
				class="mt-4 text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
			>
				{$t('home.desc_1')}
			</h2>
			<p class="mt-4 text-gray-600 dark:text-gray-300 max-w-2xl mx-auto text-lg">
				{$t('home.desc_2')}
			</p>
		</div>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
			<!-- Image for Features -->
			<div class="order-1 md:order-2">
				<img
					src={MapWithPins}
					alt="World map with pins"
					class="rounded-lg shadow-lg object-cover"
				/>
			</div>
			<!-- Feature List -->
			<div class="order-2 md:order-1">
				<ul class="space-y-6">
					<li class="space-y-2">
						<h3 class="text-xl font-semibold dark:text-gray-300">{$t('home.feature_1')}</h3>
						<p class="text-gray-600 dark:text-gray-400">
							{$t('home.feature_1_desc')}
						</p>
					</li>
					<li class="space-y-2">
						<h3 class="text-xl font-semibold dark:text-gray-300">{$t('home.feature_2')}</h3>
						<p class="text-gray-600 dark:text-gray-400">
							{$t('home.feature_2_desc')}
						</p>
					</li>
					<li class="space-y-2">
						<h3 class="text-xl font-semibold dark:text-gray-300">{$t('home.feature_3')}</h3>
						<p class="text-gray-600 dark:text-gray-400">
							{$t('home.feature_3_desc')}
						</p>
					</li>
				</ul>
			</div>
		</div>
	</div>
</section>

<svelte:head>
	<title>Home | AdventureLog</title>
	<meta
		name="description"
		content="AdventureLog is a platform to log your adventures and plan your travel."
	/>
</svelte:head>
