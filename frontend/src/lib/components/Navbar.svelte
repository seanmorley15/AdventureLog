<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	export let data: any;
	import type { SubmitFunction } from '@sveltejs/kit';

	import DotsHorizontal from '~icons/mdi/dots-horizontal';
	import WeatherSunny from '~icons/mdi/weather-sunny';
	import WeatherNight from '~icons/mdi/weather-night';
	import Forest from '~icons/mdi/forest';
	import Flower from '~icons/mdi/flower';
	import Water from '~icons/mdi/water';
	import AboutModal from './AboutModal.svelte';
	import Avatar from './Avatar.svelte';
	import { page } from '$app/stores';

	let query: string = '';

	let isAboutModalOpen: boolean = false;

	const submitUpdateTheme: SubmitFunction = ({ action }) => {
		const theme = action.searchParams.get('theme');
		console.log('theme', theme);
		if (theme) {
			document.documentElement.setAttribute('data-theme', theme);
		}
	};

	const searchGo = async (e: Event) => {
		e.preventDefault();
		let reload: boolean = false;

		if ($page.url.pathname === '/search') {
			reload = true;
		}

		if (query) {
			await goto(`/search?query=${query}`);
			if (reload) {
				window.location.reload();
			}
		}
	};
</script>

{#if isAboutModalOpen}
	<AboutModal on:close={() => (isAboutModalOpen = false)} />
{/if}

<div class="navbar bg-base-100">
	<div class="navbar-start">
		<div class="dropdown">
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
				class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 gap-2"
			>
				{#if data.user}
					<li>
						<button on:click={() => goto('/adventures')}>Adventures</button>
					</li>
					<li>
						<button on:click={() => goto('/collections')}>Collections</button>
					</li>
					<li>
						<button on:click={() => goto('/worldtravel')}>World Travel</button>
					</li>
					<li>
						<button on:click={() => goto('/map')}>Map</button>
					</li>
				{/if}

				{#if !data.user}
					<li>
						<button class="btn btn-primary" on:click={() => goto('/login')}>Login</button>
					</li>
					<li>
						<button class="btn btn-primary" on:click={() => goto('/signup')}>Signup</button>
					</li>
				{/if}

				<form class="flex gap-2">
					<label class="input input-bordered flex items-center gap-2">
						<input type="text" bind:value={query} class="grow" placeholder="Search" />

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
					<button on:click={searchGo} type="submit" class="btn btn-neutral">Search</button>
				</form>
			</ul>
		</div>
		<a class="btn btn-ghost text-xl" href="/"
			>AdventureLog <img src="/favicon.png" alt="Map Logo" class="w-8" /></a
		>
	</div>
	<div class="navbar-center hidden lg:flex">
		<ul class="menu menu-horizontal px-1 gap-2">
			{#if data.user}
				<li>
					<button class="btn btn-neutral" on:click={() => goto('/adventures')}>Adventures</button>
				</li>
				<li>
					<button class="btn btn-neutral" on:click={() => goto('/collections')}>Collections</button>
				</li>
				<li>
					<button class="btn btn-neutral" on:click={() => goto('/worldtravel')}>World Travel</button
					>
				</li>
				<li>
					<button class="btn btn-neutral" on:click={() => goto('/map')}>Map</button>
				</li>
			{/if}

			{#if !data.user}
				<li>
					<button class="btn btn-primary" on:click={() => goto('/login')}>Login</button>
				</li>
				<li>
					<button class="btn btn-primary" on:click={() => goto('/signup')}>Signup</button>
				</li>
			{/if}

			<form class="flex gap-2">
				<label class="input input-bordered flex items-center gap-2">
					<input type="text" bind:value={query} class="grow" placeholder="Search" />

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
				<button on:click={searchGo} type="submit" class="btn btn-neutral">Search</button>
			</form>
		</ul>
	</div>
	<div class="navbar-end">
		{#if data.user}
			<Avatar user={data.user} />
		{/if}
		<div class="dropdown dropdown-bottom dropdown-end">
			<div tabindex="0" role="button" class="btn m-1 ml-4">
				<DotsHorizontal class="w-6 h-6" />
			</div>
			<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
			<ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52">
				<button class="btn" on:click={() => (isAboutModalOpen = true)}>About AdventureLog</button>
				<p class="font-bold m-4 text-lg">Theme Selection</p>
				<form method="POST" use:enhance={submitUpdateTheme}>
					<li>
						<button formaction="/?/setTheme&theme=light"
							>Light<WeatherSunny class="w-6 h-6" />
						</button>
					</li>
					<li>
						<button formaction="/?/setTheme&theme=dark">Dark<WeatherNight class="w-6 h-6" /></button
						>
					</li>
					<li>
						<button formaction="/?/setTheme&theme=night"
							>Night<WeatherNight class="w-6 h-6" /></button
						>
					</li>
					<li>
						<button formaction="/?/setTheme&theme=forest">Forest<Forest class="w-6 h-6" /></button>
						<button formaction="/?/setTheme&theme=garden">Garden<Flower class="w-6 h-6" /></button>
						<button formaction="/?/setTheme&theme=aqua">Aqua<Water class="w-6 h-6" /></button>
					</li>
				</form>
			</ul>
		</div>
	</div>
</div>
