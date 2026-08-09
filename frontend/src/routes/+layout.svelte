<script lang="ts">
	import { browser } from '$app/environment';
	import { register, init, locale, waitLocale } from 'svelte-i18n';
	import { UmamiAnalyticsEnv } from '@lukulent/svelte-umami';
	export let data;

	// Register your translations for each locale
	register('en', () => import('../locales/en.json'));
	register('es', () => import('../locales/es.json'));
	register('fr', () => import('../locales/fr.json'));
	register('de', () => import('../locales/de.json'));
	register('it', () => import('../locales/it.json'));
	register('zh', () => import('../locales/zh.json'));
	register('nl', () => import('../locales/nl.json'));
	register('sv', () => import('../locales/sv.json'));
	register('pl', () => import('../locales/pl.json'));
	register('ko', () => import('../locales/ko.json'));
	register('no', () => import('../locales/no.json'));
	register('ru', () => import('../locales/ru.json'));
	register('ja', () => import('../locales/ja.json'));
	register('ar', () => import('../locales/ar.json'));
	register('pt-br', () => import('../locales/pt-br.json'));
	register('ro', () => import('../locales/ro.json'));
	register('sk', () => import('../locales/sk.json'));
	register('tr', () => import('../locales/tr.json'));
	register('uk', () => import('../locales/uk.json'));
	register('hu', () => import('../locales/hu.json'));
	register('ca', () => import('../locales/ca.json'));
	register('cs', () => import('../locales/cs.json'));

	if (browser) {
		init({
			// The fallback must be a fully translated locale, otherwise a key that is missing
			// from the active locale has nowhere to fall back to and renders as its raw id
			// (e.g. "dashboard.greeting_afternoon"). Deriving it from navigator.language made
			// the fallback identical to the active locale for most users, which defeated it.
			fallbackLocale: 'en',
			initialLocale: data.locale
		});
		// get the locale cookie if it exists and set it as the initial locale if it exists
		const localeCookie = document.cookie
			.split(';')
			.find((cookie) => cookie.trim().startsWith('locale='));
		if (localeCookie) {
			const localeValue = localeCookie.split('=')[1];
			locale.set(localeValue);
		}
	}

	import Navbar from '$lib/components/Navbar.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import CommandPalette from '$lib/components/search/CommandPalette.svelte';
	import 'tailwindcss/tailwind.css';

	// Create a promise that resolves when the locale is ready
	export const localeLoaded = browser ? waitLocale() : Promise.resolve();
</script>

{#await localeLoaded}
	<!-- You can add a loading indicator here if needed -->
{:then}
	<Navbar {data} />
	{#if data.user}
		<CommandPalette />
	{/if}
	<Toast />
	<slot />
{/await}

<UmamiAnalyticsEnv />

<svelte:head>
	<title>AdventureLog</title>
	<meta
		name="description"
		content="Embark, explore, remember with AdventureLog. AdventureLog is the ultimate travel companion."
	/>
</svelte:head>

<style>
	/* Prevent unwanted horizontal scroll and ensure single scrollbar */
	:global(html) {
		overflow-x: hidden;
		overflow-y: auto;
	}

	:global(body) {
		overflow: hidden;
	}

	/* Ensure slot content doesn't create nested scrollbars */
	:global(body > div) {
		overflow: visible;
	}
</style>
