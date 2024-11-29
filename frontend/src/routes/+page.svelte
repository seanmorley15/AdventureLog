<script lang="ts">
	import { goto } from '$app/navigation';

	import AdventureOverlook from '$lib/assets/AdventureOverlook.webp';
	import MapWithPins from '$lib/assets/MapWithPins.webp';
	import { t } from 'svelte-i18n';

	export let data;
</script>

<section class="flex items-center justify-center w-full py-12 md:py-24 lg:py-32">
	<div class="container px-4 md:px-6">
		<div class="grid gap-6 lg:grid-cols-[1fr_550px] lg:gap-12 xl:grid-cols-[1fr_650px]">
			<div class="flex flex-col justify-center space-y-4">
				<div class="space-y-2">
					{#if data.user}
						{#if data.user.first_name && data.user.first_name !== null}
							<h1
								class="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent pb-4"
							>
								{data.user.first_name.charAt(0).toUpperCase() + data.user.first_name.slice(1)},
								{$t('home.hero_1')}
							</h1>
						{:else}
							<h1
								class="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent pb-4"
							>
								{$t('home.hero_1')}
							</h1>
						{/if}
					{:else}
						<h1
							class="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent pb-4"
						>
							{$t('home.hero_1')}
						</h1>
					{/if}
					<p class="max-w-[600px] text-gray-500 md:text-xl dark:text-gray-400">
						{$t('home.hero_2')}
					</p>
				</div>
				<div class="flex flex-col gap-2 min-[400px]:flex-row">
					{#if data.user}
						<button on:click={() => goto('/adventures')} class="btn btn-primary">
							{$t('home.go_to')}
						</button>
					{:else}
						<button on:click={() => goto('/login')} class="btn btn-primary">
							{$t('auth.login')}
						</button>
						<button on:click={() => goto('/signup')} class="btn btn-neutral">
							{$t('auth.signup')}
						</button>
					{/if}
				</div>
			</div>
			<img
				src={AdventureOverlook}
				width="550"
				height="550"
				alt="Hero"
				class="mx-auto aspect-video overflow-hidden rounded-xl object-cover sm:w-full lg:order-last"
			/>
		</div>
	</div>
</section>
<section
	class="flex items-center justify-center w-full py-12 md:py-24 lg:py-32 bg-gray-100 dark:bg-gray-800"
>
	<div class="container px-4 md:px-6">
		<div class="flex flex-col items-center justify-center space-y-4 text-center">
			<div class="space-y-2">
				<div
					class="inline-block rounded-lg bg-gray-100 px-3 py-1 text-md dark:bg-gray-800 dark:text-gray-400"
				>
					{$t('home.key_features')}
				</div>
				<h2
					class="text-3xl font-bold tracking-tighter sm:text-5xl bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
				>
					{$t('home.desc_1')}
				</h2>
				<p
					class="max-w-[900px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400"
				>
					{$t('home.desc_2')}
				</p>
			</div>
		</div>
		<div class="mx-auto grid max-w-5xl items-center gap-6 py-12 lg:grid-cols-2 lg:gap-12">
			<!-- svelte-ignore a11y-img-redundant-alt -->
			<img
				src={MapWithPins}
				width="550"
				height="310"
				alt="Image"
				class="mx-auto aspect-video overflow-hidden rounded-xl object-cover object-center sm:w-full lg:order-last"
			/>
			<div class="flex flex-col justify-center space-y-4">
				<ul class="grid gap-6">
					<li>
						<div class="grid gap-1">
							<h3 class="text-xl font-bold dark:text-gray-400">{$t('home.feature_1')}</h3>
							<p class="text-gray-500 dark:text-gray-400">
								{$t('home.feature_1_desc')}
							</p>
						</div>
					</li>
					<li>
						<div class="grid gap-1">
							<h3 class="text-xl font-bold dark:text-gray-400">{$t('home.feature_2')}</h3>
							<p class="text-gray-500 dark:text-gray-400">
								{$t('home.feature_2_desc')}
							</p>
						</div>
					</li>
					<li>
						<div class="grid gap-1">
							<h3 class="text-xl font-bold dark:text-gray-400">{$t('home.feature_3')}</h3>
							<p class="text-gray-500 dark:text-gray-400">
								{$t('home.feature_3_desc')}
							</p>
						</div>
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
