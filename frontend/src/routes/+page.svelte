<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';

	import MapWithPins from '$lib/assets/MapWithPins.webp';
	import type { Background } from '$lib/types.js';

	// Icons
	import MapIcon from '~icons/mdi/map-outline';
	import CameraIcon from '~icons/mdi/camera-outline';
	import CalendarIcon from '~icons/mdi/calendar-outline';
	import TrophyIcon from '~icons/mdi/trophy-outline';
	import ChevronRight from '~icons/mdi/chevron-right';
	import PlayIcon from '~icons/mdi/play';
	import CheckIcon from '~icons/mdi/check-circle';
	import StarIcon from '~icons/mdi/star';
	import GlobeIcon from '~icons/mdi/earth';
	import LightningIcon from '~icons/mdi/lightning-bolt';

	export let data;

	let background: Background = data.props?.background ?? { url: '' };
	let isVisible = false;

	onMount(() => {
		setTimeout(() => (isVisible = true), 100);
	});

	const features = [
		{
			icon: MapIcon,
			title: $t('home.feature_1'),
			description: $t('home.feature_1_desc'),
			color: 'text-blue-500',
			bgColor: 'bg-blue-50 dark:bg-blue-900/20'
		},
		{
			icon: CameraIcon,
			title: $t('home.feature_2'),
			description: $t('home.feature_2_desc'),
			color: 'text-green-500',
			bgColor: 'bg-green-50 dark:bg-green-900/20'
		},
		{
			icon: TrophyIcon,
			title: $t('home.feature_3'),
			description: $t('home.feature_3_desc'),
			color: 'text-yellow-500',
			bgColor: 'bg-yellow-50 dark:bg-yellow-900/20'
		}
	];

	// const stats = [
	// 	{ label: 'Countries Tracked', value: '195+', icon: GlobeIcon },
	// 	{ label: 'Adventures Logged', value: '10K+', icon: CalendarIcon },
	// 	{ label: 'Active Travelers', value: '5K+', icon: StarIcon }
	// ];
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<!-- Hero Section -->
	<section class="relative min-h-screen flex items-center justify-center overflow-hidden">
		<!-- Background Pattern -->
		<div class="absolute inset-0 opacity-5">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 to-secondary/20"></div>
			<svg class="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
				<defs>
					<pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
						<path d="M 10 0 L 0 0 0 10" fill="none" stroke="currentColor" stroke-width="0.5" />
					</pattern>
				</defs>
				<rect width="100" height="100" fill="url(#grid)" />
			</svg>
		</div>

		<div class="container mx-auto px-6 py-20 relative z-10">
			<div class="grid lg:grid-cols-2 gap-12 items-center">
				<!-- Left Content -->
				<div class="space-y-8 {isVisible ? 'animate-fade-in-up' : 'opacity-0'}">
					<div class="space-y-4">
						<div
							class="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-full border border-primary/20"
						>
							<LightningIcon class="w-4 h-4" />
							<span class="text-sm font-medium">{$t('home.start_your_journey')}</span>
						</div>
						<h1 class="text-5xl lg:text-7xl font-black leading-tight">
							<span
								class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
							>
								{$t('home.hero_1')}
							</span>
						</h1>
					</div>

					<p class="text-xl lg:text-2xl text-base-content/70 leading-relaxed font-light max-w-2xl">
						{$t('home.hero_2')}
					</p>

					<!-- CTA Buttons -->
					<div class="flex flex-col sm:flex-row gap-4 pt-4">
						{#if data.user}
							<button
								on:click={() => goto('/adventures')}
								class="btn btn-primary btn-lg gap-3 shadow-lg hover:shadow-xl transition-all duration-300 group"
							>
								<PlayIcon class="w-5 h-5 group-hover:scale-110 transition-transform" />
								{$t('home.go_to')}
								<ChevronRight class="w-4 h-4 group-hover:translate-x-1 transition-transform" />
							</button>
						{:else}
							<button
								on:click={() => goto('/login')}
								class="btn btn-primary btn-lg gap-3 shadow-lg hover:shadow-xl transition-all duration-300 group"
							>
								{$t('auth.login')}
								<ChevronRight class="w-4 h-4 group-hover:translate-x-1 transition-transform" />
							</button>
							<button
								on:click={() => goto('/signup')}
								class="btn btn-outline btn-lg gap-3 hover:shadow-lg transition-all duration-300"
							>
								{$t('auth.signup')}
							</button>
						{/if}
					</div>
				</div>

				<!-- Right Content - Hero Image -->
				<div class="relative {isVisible ? 'animate-fade-in-right' : 'opacity-0'}">
					<div class="relative">
						<!-- Decorative Elements -->
						<div class="absolute -top-4 -left-4 w-24 h-24 bg-primary/10 rounded-2xl rotate-6"></div>
						<div
							class="absolute -bottom-4 -right-4 w-32 h-32 bg-secondary/10 rounded-2xl -rotate-6"
						></div>

						<!-- Main Image -->
						<div class="relative bg-base-100 p-4 rounded-3xl shadow-2xl">
							<img
								src={background.url}
								alt={background.location}
								class="rounded-2xl object-cover w-full h-[500px] shadow-lg"
							/>

							<!-- Floating Badge -->
							<div
								class="absolute top-8 left-8 bg-base-100/90 backdrop-blur-sm px-4 py-2 rounded-full shadow-lg border"
							>
								<div class="flex items-center gap-2">
									<div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
									<span class="text-sm font-medium"
										>{background.location || 'Adventure Awaits'}</span
									>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Scroll Indicator -->
		<div class="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
			<div class="w-6 h-10 border-2 border-base-content/30 rounded-full flex justify-center">
				<div class="w-1 h-3 bg-base-content/30 rounded-full mt-2 animate-pulse"></div>
			</div>
		</div>
	</section>

	<!-- Features Section -->
	<section id="features" class="py-24 bg-base-100">
		<div class="container mx-auto px-6">
			<!-- Section Header -->
			<div class="text-center mb-16 space-y-4">
				<div
					class="inline-flex items-center gap-2 px-4 py-2 bg-neutral text-neutral-300 rounded-full border border-neutral"
				>
					<StarIcon class="w-4 h-4" />
					<span class="text-sm font-medium">{$t('home.key_features')}</span>
				</div>
				<h2 class="text-4xl lg:text-5xl font-bold">
					<span class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
						{$t('home.desc_1')}
					</span>
				</h2>
				<p class="text-xl text-base-content/70 max-w-3xl mx-auto leading-relaxed">
					{$t('home.desc_2')}
				</p>
			</div>

			<div class="grid lg:grid-cols-2 gap-16 items-center">
				<!-- Features List -->
				<div class="space-y-8">
					{#each features as feature, index}
						<div
							class="group hover:bg-base-200/50 p-6 rounded-2xl transition-all duration-300 hover:shadow-lg"
						>
							<div class="flex items-start gap-4">
								<div class="flex-shrink-0 p-3 {feature.bgColor} rounded-xl">
									<svelte:component this={feature.icon} class="w-6 h-6 {feature.color}" />
								</div>
								<div class="space-y-2">
									<h3
										class="text-xl font-bold text-base-content group-hover:text-primary transition-colors"
									>
										{feature.title}
									</h3>
									<p class="text-base-content/70 leading-relaxed">
										{feature.description}
									</p>
								</div>
							</div>
						</div>
					{/each}
				</div>

				<!-- Feature Image -->
				<div class="relative">
					<div class="relative bg-gradient-to-br from-primary/5 to-secondary/5 p-8 rounded-3xl">
						<img
							src={MapWithPins}
							alt="World map with pins"
							class="rounded-2xl shadow-2xl object-cover w-full"
						/>
					</div>
				</div>
			</div>
		</div>
	</section>
</div>

<svelte:head>
	<title>Home | AdventureLog</title>
	<meta
		name="description"
		content="AdventureLog is a platform to log your adventures and plan your travel."
	/>
</svelte:head>

<style>
	@keyframes fade-in-up {
		from {
			opacity: 0;
			transform: translateY(30px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes fade-in-right {
		from {
			opacity: 0;
			transform: translateX(30px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	@keyframes float {
		0%,
		100% {
			transform: translateY(0px);
		}
		50% {
			transform: translateY(-10px);
		}
	}

	@keyframes float-delayed {
		0%,
		100% {
			transform: translateY(0px);
		}
		50% {
			transform: translateY(-8px);
		}
	}

	.animate-fade-in-up {
		animation: fade-in-up 0.8s ease-out;
	}

	.animate-fade-in-right {
		animation: fade-in-right 0.8s ease-out 0.2s both;
	}

	.animate-float {
		animation: float 3s ease-in-out infinite;
	}

	.animate-float-delayed {
		animation: float-delayed 3s ease-in-out infinite 1.5s;
	}
</style>
