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

	let locales = ['en', 'es', 'fr', 'de', 'it', 'zh', 'nl', 'sv', 'pl', 'ko', 'no', 'ru'];

	if (browser) {
		init({
			fallbackLocale: locales.includes(navigator.language.split('-')[0])
				? navigator.language.split('-')[0]
				: 'en',
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
	import 'tailwindcss/tailwind.css';

	// Create a promise that resolves when the locale is ready
	export const localeLoaded = browser ? waitLocale() : Promise.resolve();
</script>

{#await localeLoaded}
	<!-- You can add a loading indicator here if needed -->
{:then}
	<Navbar {data} />
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
