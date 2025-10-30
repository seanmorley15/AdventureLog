<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	export let data: any;
	import type { SubmitFunction } from '@sveltejs/kit';

	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import Calendar from '~icons/mdi/calendar';
	import AboutModal from './AboutModal.svelte';
	import AccountMultiple from '~icons/mdi/account-multiple';
	import MapMarker from '~icons/mdi/map-marker';
	import FormatListBulletedSquare from '~icons/mdi/format-list-bulleted-square';
	import Earth from '~icons/mdi/earth';
	import Magnify from '~icons/mdi/magnify';
	import Map from '~icons/mdi/map';
	import Target from '~icons/mdi/target';
	import Menu from '~icons/mdi/menu';
	import Avatar from './Avatar.svelte';
	import { page } from '$app/stores';
	import { t, locale, locales } from 'svelte-i18n';
	import { themes } from '$lib';
	import { onMount } from 'svelte';

	let inputElement: HTMLInputElement | null = null;
	let theme = '';
	let query: string = '';
	let isAboutModalOpen: boolean = false;

	// Event listener for focusing input
	function handleKeydown(event: KeyboardEvent) {
		if (
			event.key === '/' &&
			!['INPUT', 'TEXTAREA'].includes((event.target as HTMLElement)?.tagName)
		) {
			event.preventDefault();
			if (inputElement) {
				inputElement.focus();
			}
		}
	}

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);
		// @ts-ignore
		theme = document.documentElement.getAttribute('data-theme');

		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});

	let languages: { [key: string]: string } = {
		en: 'English',
		de: 'Deutsch',
		es: 'Español',
		fr: 'Français',
		it: 'Italiano',
		nl: 'Nederlands',
		sv: 'Svenska',
		zh: '中文',
		pl: 'Polski',
		ko: '한국어',
		no: 'Norsk',
		ru: 'Русский',
		ja: '日本語',
		ar: 'العربية',
		'pt-br': 'Português (Brasil)',
		sk: 'Slovenský',
		tr: 'Türkçe',
		hu: 'Magyar'
	};

	const submitLocaleChange = (event: Event) => {
		const select = event.target as HTMLSelectElement;
		const newLocale = select.value;
		document.cookie = `locale=${newLocale}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;
		locale.set(newLocale);
		window.location.reload();
	};

	const submitThemeChange = (event: Event) => {
		// @ts-ignore
		const theme = event.target.value;
		// @ts-ignore
		const themeForm = event.target.parentNode;
		themeForm.action = `/?/setTheme&theme=${theme}`;
		themeForm.submit();
	};

	const submitUpdateTheme: SubmitFunction = ({ action }) => {
		const theme = action.searchParams.get('theme');
		if (theme) {
			document.documentElement.setAttribute('data-theme', theme);
		}
	};

	const searchGo = async (e: Event) => {
		e.preventDefault();

		if ($page.url.pathname === '/search') {
			let url = new URL(window.location.href);
			url.searchParams.set('query', query);
			goto(url.toString(), { invalidateAll: true });
		}

		if (query) {
			goto(`/search?query=${query}`);
		}
	};

	// Navigation items for better organization
	const navigationItems = [
		{ path: '/locations', icon: MapMarker, label: 'locations.locations' },
		{ path: '/collections', icon: FormatListBulletedSquare, label: 'navbar.collections' },
		{ path: '/bucketlist', icon: Target, label: 'Bucket List' },
		{ path: '/worldtravel', icon: Earth, label: 'navbar.worldtravel' },
		{ path: '/map', icon: Map, label: 'navbar.map' },
		{ path: '/calendar', icon: Calendar, label: 'navbar.calendar' },
		{ path: '/users', icon: AccountMultiple, label: 'navbar.users' }
	];
</script>

{#if isAboutModalOpen}
	<AboutModal on:close={() => (isAboutModalOpen = false)} />
{/if}

<div class="navbar bg-base-100/95 backdrop-blur-lg border-b border-base-300 top-0 z-[999] relative">
	<div class="navbar-start">
		<!-- Mobile Menu -->
		<div class="dropdown z-[999]">
			<div tabindex="0" role="button" class="btn btn-ghost btn-square lg:hidden">
				<Menu class="h-5 w-5" />
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul
				tabindex="0"
				class="menu dropdown-content mt-3 z-[999] p-4 shadow-2xl bg-base-100 border border-base-300 rounded-2xl gap-2 w-80 max-h-[80vh] overflow-y-auto"
			>
				{#if data.user}
					<!-- Navigation Items -->
					<div class="mb-4">
						<h3
							class="text-sm font-semibold text-base-content/60 uppercase tracking-wide mb-2 px-2"
						>
							{$t('navbar.navigation')}
						</h3>
						{#each navigationItems as item}
							<li>
								<a
									href={item.path}
									class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl"
									class:btn-active={$page.url.pathname === item.path}
								>
									<svelte:component this={item.icon} class="w-5 h-5" />
									{$t(item.label)}
								</a>
							</li>
						{/each}
					</div>

					<div class="divider my-2"></div>

					<!-- Search Section -->
					<div class="mb-4">
						<h3
							class="text-sm font-semibold text-base-content/60 uppercase tracking-wide mb-2 px-2"
						>
							{$t('navbar.search')}
						</h3>
						<form class="flex gap-2" on:submit={searchGo}>
							<label class="input input-bordered flex items-center gap-2 flex-1">
								<Magnify class="h-4 w-4 opacity-70" />
								<input
									type="text"
									bind:value={query}
									placeholder={$t('navbar.search')}
									class="grow"
								/>
							</label>
							<button type="submit" class="btn btn-primary btn-square">
								<Magnify class="w-4 h-4" />
							</button>
						</form>
					</div>
				{:else}
					<!-- Auth Buttons -->
					<div class="space-y-2">
						<li>
							<button class="btn btn-primary w-full" on:click={() => goto('/login')}>
								{$t('auth.login')}
							</button>
						</li>
						<li>
							<button class="btn btn-outline w-full" on:click={() => goto('/signup')}>
								{$t('auth.signup')}
							</button>
						</li>
					</div>
				{/if}
			</ul>
		</div>

		<!-- Logo -->
		<a class="btn btn-ghost hover:bg-transparent p-2 text-2xl font-bold tracking-tight" href="/">
			<div class="flex items-center gap-3">
				<img src="/favicon.png" alt="AdventureLog" class="w-10 h-10" />
				<span class="hidden sm:inline mb-1"> AdventureLog </span>
			</div>
		</a>
	</div>

	<!-- Desktop Navigation -->
	<div class="navbar-center hidden lg:flex">
		{#if data.user}
			<ul class="menu menu-horizontal gap-1">
				{#each navigationItems as item}
					<li>
						<a
							href={item.path}
							class="btn btn-ghost gap-2 rounded-xl transition-all duration-200 hover:bg-base-200"
							class:bg-primary-10={$page.url.pathname === item.path}
							class:text-primary={$page.url.pathname === item.path}
						>
							<svelte:component this={item.icon} class="w-4 h-4" />
							<span class="hidden xl:inline">{$t(item.label)}</span>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="navbar-end gap-3">
		<!-- Desktop Search -->
		{#if data.user}
			<form class="hidden lg:flex gap-2" on:submit={searchGo}>
				<label
					class="input input-bordered input-sm flex items-center gap-2 w-64 focus-within:w-80 transition-all duration-300"
				>
					<input
						type="text"
						bind:value={query}
						class="grow"
						placeholder={$t('navbar.search')}
						bind:this={inputElement}
					/>
					<kbd class="kbd kbd-xs opacity-60">/</kbd>
				</label>
				<button type="submit" class="btn btn-ghost btn-sm btn-square">
					<Magnify class="w-4 h-4" />
				</button>
			</form>
		{/if}

		<!-- Auth Buttons (Desktop) -->
		{#if !data.user}
			<div class="hidden lg:flex gap-2">
				<button class="btn btn-primary btn-sm" on:click={() => goto('/login')}>
					{$t('auth.login')}
				</button>
				<button class="btn btn-neutral btn-sm" on:click={() => goto('/signup')}>
					{$t('auth.signup')}
				</button>
			</div>
		{/if}

		<!-- User Avatar -->
		{#if data.user}
			<Avatar user={data.user} />
		{/if}

		<!-- Settings Dropdown -->
		<div class="dropdown dropdown-bottom dropdown-end z-[999]">
			<div tabindex="0" role="button" class="btn btn-neutral-300 btn-sm btn-square">
				<DotsHorizontal class="w-5 h-5" />
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul
				tabindex="0"
				class="dropdown-content bg-base-100 border border-base-300 shadow-2xl z-[999] menu p-4 rounded-2xl w-80"
			>
				<!-- Quick Actions -->
				<div class="space-y-2 mb-4">
					<button
						class="btn btn-ghost w-full justify-start gap-3"
						on:click={() => (isAboutModalOpen = true)}
					>
						{$t('navbar.about')}
					</button>
					<button
						class="btn btn-ghost w-full justify-start gap-3"
						on:click={() => (window.location.href = 'https://adventurelog.app')}
					>
						{$t('navbar.documentation')}
					</button>
					<button
						class="btn btn-ghost w-full justify-start gap-3"
						on:click={() => (window.location.href = 'https://discord.gg/wRbQ9Egr8C')}
					>
						Discord
					</button>
					<button
						class="btn btn-ghost w-full justify-start gap-3"
						on:click={() => (window.location.href = 'https://seanmorley.com/sponsor')}
					>
						{$t('navbar.support')} 💖
					</button>
				</div>

				<div class="divider my-3"></div>

				<!-- Language Selection -->
				<div class="mb-4">
					<h3 class="font-semibold text-sm text-base-content/70 mb-3 flex items-center gap-2">
						<Earth class="w-4 h-4" />
						{$t('navbar.language_selection')}
					</h3>
					<form method="POST" use:enhance>
						<select
							class="select select-bordered select-sm w-full bg-base-100"
							on:change={submitLocaleChange}
							bind:value={$locale}
						>
							{#each $locales as loc (loc)}
								<option value={loc}>{languages[loc]}</option>
							{/each}
						</select>
						<input type="hidden" name="locale" value={$locale} />
					</form>
				</div>

				<!-- Theme Selection -->
				<div>
					<h3 class="font-semibold text-sm text-base-content/70 mb-3">
						{$t('navbar.theme_selection')}
					</h3>
					<form method="POST" use:enhance={submitUpdateTheme}>
						<select
							class="select select-bordered select-sm w-full bg-base-100"
							bind:value={theme}
							on:change={submitThemeChange}
						>
							{#each themes as themeOption}
								<option value={themeOption.name}>
									{$t(`navbar.themes.${themeOption.name}`)}
								</option>
							{/each}
						</select>
					</form>
				</div>
			</ul>
		</div>
	</div>
</div>
