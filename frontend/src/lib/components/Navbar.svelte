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
	import Avatar from './Avatar.svelte';
	import { page } from '$app/stores';
	import { t, locale, locales } from 'svelte-i18n';
	import { themes } from '$lib';
	import { onMount } from 'svelte';
	let inputElement: HTMLInputElement | null = null;

	let theme = '';

	// Event listener for focusing input
	function handleKeydown(event: KeyboardEvent) {
		// Ignore any keypresses in an input/textarea field, so we don't interfere with typing.
		if (
			event.key === '/' &&
			!['INPUT', 'TEXTAREA'].includes((event.target as HTMLElement)?.tagName)
		) {
			event.preventDefault(); // Prevent browser's search shortcut
			if (inputElement) {
				inputElement.focus();
			}
		}
	}

	onMount(() => {
		// Attach event listener on component mount
		document.addEventListener('keydown', handleKeydown);

		// @ts-ignore
		theme = document.documentElement.getAttribute('data-theme');

		// Cleanup event listener on component destruction
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
		ru: 'Русский'
	};

	let query: string = '';

	let isAboutModalOpen: boolean = false;

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
</script>

{#if isAboutModalOpen}
	<AboutModal on:close={() => (isAboutModalOpen = false)} />
{/if}

<div class="navbar bg-base-100">
	<div class="navbar-start">
		<div class="dropdown z-50">
			<div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-5 w-5"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					><path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 6h16M4 12h8m-8 6h16"
					/></svg
				>
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul
				tabindex="0"
				class="menu dropdown-content mt-3 z-[1] p-2 shadow bg-neutral text-base text-neutral-content rounded-box gap-2 w-96"
			>
				{#if data.user}
					<li>
						<button on:click={() => goto('/adventures')}>{$t('navbar.adventures')}</button>
					</li>
					<li>
						<button on:click={() => goto('/collections')}>{$t('navbar.collections')}</button>
					</li>
					<li>
						<button on:click={() => goto('/worldtravel')}>{$t('navbar.worldtravel')}</button>
					</li>
					<li>
						<button on:click={() => goto('/map')}>{$t('navbar.map')}</button>
					</li>
					<li>
						<button on:click={() => goto('/calendar')}>{$t('navbar.calendar')}</button>
					</li>
					<li>
						<button on:click={() => goto('/users')}>{$t('navbar.users')}</button>
					</li>
				{/if}

				{#if !data.user}
					<li>
						<button class="btn btn-primary" on:click={() => goto('/login')}
							>{$t('auth.login')}</button
						>
					</li>
					<li>
						<button class="btn btn-primary" on:click={() => goto('/signup')}
							>{$t('auth.signup')}</button
						>
					</li>
				{/if}

				{#if data.user}
					<form class="flex gap-2">
						<label class="input input-bordered flex items-center gap-2">
							<input type="text" bind:value={query} placeholder={$t('navbar.search')} />

							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="h-4 w-4 opacity-70"
							>
								<path
									fill-rule="evenodd"
									d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
									clip-rule="evenodd"
								/>
							</svg>
						</label>
						<button on:click={searchGo} type="submit" class="btn btn-primary"
							>{$t('navbar.search')}</button
						>
					</form>
				{/if}
			</ul>
		</div>
		<a class="btn btn-ghost p-0 text-2xl font-bold tracking-normal" href="/">
			<span class="sm:inline hidden">AdventureLog</span>
			<img src="/favicon.png" alt="Map Logo" class="w-10" />
		</a>
	</div>
	<div class="navbar-center hidden lg:flex">
		<ul class="menu menu-horizontal px-1 gap-2">
			{#if data.user}
				<li>
					<button
						class="btn btn-neutral flex items-center gap-1"
						on:click={() => goto('/adventures')}
					>
						<MapMarker class="w-5 h-5" />
						<span>{$t('navbar.adventures')}</span>
					</button>
				</li>
				<li>
					<button
						class="btn btn-neutral flex items-center gap-1"
						on:click={() => goto('/collections')}
					>
						<FormatListBulletedSquare class="w-5 h-5" />
						{$t('navbar.collections')}</button
					>
				</li>
				<li>
					<button
						class="btn btn-neutral flex items-center gap-1"
						on:click={() => goto('/worldtravel')}
					>
						<Earth class="w-5 h-5" />
						{$t('navbar.worldtravel')}
					</button>
				</li>
				<li>
					<button class="btn btn-neutral flex items-center gap-1" on:click={() => goto('/map')}>
						<Map class="w-5 h-5" />
					</button>
				</li>
				<li>
					<button class="btn btn-neutral flex items-center gap-1" on:click={() => goto('/calendar')}
						><Calendar /></button
					>
				</li>
				<li>
					<button class="btn btn-neutral flex items-center gap-1" on:click={() => goto('/users')}
						><AccountMultiple /></button
					>
				</li>
			{/if}

			{#if !data.user}
				<li>
					<button class="btn btn-primary" on:click={() => goto('/login')}>{$t('auth.login')}</button
					>
				</li>
				<li>
					<button class="btn btn-primary" on:click={() => goto('/signup')}
						>{$t('auth.signup')}</button
					>
				</li>
			{/if}

			{#if data.user}
				<form class="flex gap-2">
					<label class="input input-bordered flex items-center gap-2">
						<input
							type="text"
							bind:value={query}
							class="grow"
							placeholder={$t('navbar.search')}
							bind:this={inputElement}
						/><kbd class="kbd">/</kbd>
					</label>
					<button on:click={searchGo} type="submit" class="btn btn-neutral flex items-center gap-1">
						<Magnify class="w-5 h-5" />
					</button>
				</form>
			{/if}
		</ul>
	</div>
	<div class="navbar-end">
		{#if data.user}
			<Avatar user={data.user} />
		{/if}
		<div class="dropdown dropdown-bottom dropdown-end">
			<div tabindex="0" role="button" class="btn m-1 p-2">
				<DotsHorizontal class="w-6 h-6" />
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul
				tabindex="0"
				class="dropdown-content bg-neutral text-neutral-content z-[1] menu p-2 shadow rounded-box w-52"
			>
				<button class="btn" on:click={() => (isAboutModalOpen = true)}>{$t('navbar.about')}</button>
				<button
					class="btn btn-sm mt-2"
					on:click={() => (window.location.href = 'https://adventurelog.app')}
					>{$t('navbar.documentation')}</button
				>
				<button
					class="btn btn-sm mt-2"
					on:click={() => (window.location.href = 'https://discord.gg/wRbQ9Egr8C')}>Discord</button
				>
				<button
					class="btn btn-sm mt-2"
					on:click={() => (window.location.href = 'https://seanmorley.com/sponsor')}
					>{$t('navbar.support')} 💖</button
				>
				<p class="font-bold m-4 text-lg text-center">{$t('navbar.language_selection')}</p>
				<form method="POST" use:enhance>
					<select
						class="select select-bordered w-full max-w-xs bg-base-100 text-base-content"
						on:change={submitLocaleChange}
						bind:value={$locale}
					>
						{#each $locales as loc (loc)}
							<option value={loc} class="text-base-content">{languages[loc]}</option>
						{/each}
					</select>
					<input type="hidden" name="locale" value={$locale} />
				</form>
				<p class="font-bold m-4 text-lg text-center">{$t('navbar.theme_selection')}</p>
				<form method="POST" use:enhance={submitUpdateTheme}>
					<select
						class="select select-bordered w-full max-w-xs bg-base-100 text-base-content"
						bind:value={theme}
						on:change={submitThemeChange}
					>
						{#each themes as theme}
							<option value={theme.name} class="text-base-content"
								>{$t(`navbar.themes.${theme.name}`)}</option
							>
						{/each}
					</select>
				</form>
			</ul>
		</div>
	</div>
</div>
