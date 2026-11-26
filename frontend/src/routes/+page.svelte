<script lang="ts">
	import { goto, preloadData } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import { onMount } from 'svelte';
	import type { Background } from '#lib/types.js';

	let { data } = $props();

	let background: Background = $derived(data.props?.background ?? { url: '' });
	let ready = $state(false);

	onMount(() => {
		requestAnimationFrame(() => (ready = true));

		// Warm up the login and signup loads so the transition starts instantly
		const idle = window.requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 600));
		idle(() => {
			preloadData('/login').catch(() => {});
			preloadData('/signup').catch(() => {});
		});
	});
</script>

<section class="hero relative isolate overflow-hidden bg-neutral text-white" class:ready>
	{#if background.url}
		<img
			src={background.url}
			alt={background.location ?? ''}
			class="photo fixed inset-0 -z-20 h-full w-full object-cover"
		/>
	{/if}
	<div class="shade absolute inset-0 -z-10"></div>

	<div
		class="mx-auto flex h-full max-w-6xl flex-col justify-end px-6 pb-10 pt-24 lg:px-10 lg:pb-14"
	>
		<h1 class="headline">
			{$t('home.where_next_1')}
			{$t('home.where_next_2')}
		</h1>
		<p class="lede">{$t('home.welcome_line')}</p>

		<div class="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
			<button onclick={() => goto('/login')} class="btn btn-primary btn-lg px-8">
				{$t('auth.login')}
			</button>
			<a
				href="/signup"
				class="btn btn-lg border-white/30 bg-white/10 px-8 text-white backdrop-blur-sm hover:bg-white/20"
				>{$t('auth.signup')}</a
			>
		</div>

		{#if background.location}
			<p class="note">
				{background.location}{#if background.author}, {background.author}{/if}
			</p>
		{/if}
	</div>
</section>

<svelte:head>
	<title>AdventureLog</title>
	<meta
		name="description"
		content="AdventureLog is a platform to log your adventures and plan your travel."
	/>
</svelte:head>

<style>
	.hero {
		min-height: calc(100svh - 4rem);
		display: flex;
		flex-direction: column;
	}
	.hero > div {
		flex: 1;
		width: 100%;
	}

	/* Only the bottom edge is darkened, so the photo stays close to how it was shot */
	.shade {
		background: linear-gradient(
			0deg,
			rgb(10 14 12 / 0.78) 0%,
			rgb(10 14 12 / 0.45) 32%,
			transparent 62%
		);
	}

	.headline {
		font-size: clamp(3rem, 8vw, 6.5rem);
		font-weight: 800;
		line-height: 1;
		letter-spacing: -0.02em;
		max-width: 14ch;
		text-shadow: 0 1px 24px rgb(0 0 0 / 0.35);
	}
	.lede {
		margin-top: 1rem;
		max-width: 28rem;
		font-size: 1.125rem;
		line-height: 1.55;
		color: rgb(255 255 255 / 0.88);
		text-shadow: 0 1px 12px rgb(0 0 0 / 0.4);
	}
	.note {
		margin-top: 2.25rem;
		font-size: 1rem;
		color: rgb(255 255 255 / 0.8);
		text-shadow: 0 1px 10px rgb(0 0 0 / 0.5);
	}

	/* The one thing that moves: the photo settles in */
	.photo {
		opacity: 0;
	}
	.ready .photo {
		animation: settle 1.6s ease-out forwards;
	}
	@keyframes settle {
		to {
			opacity: 1;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.photo {
			opacity: 1;
			animation: none !important;
		}
	}
</style>
