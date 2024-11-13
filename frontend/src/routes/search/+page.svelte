<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure, OpenStreetMapPlace } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import { t } from 'svelte-i18n';

	export let data: PageData;

	function deleteAdventure(event: CustomEvent<string>) {
		myAdventures = myAdventures.filter((adventure) => adventure.id !== event.detail);
	}

	let osmResults: OpenStreetMapPlace[] = [];
	let myAdventures: Adventure[] = [];
	let publicAdventures: Adventure[] = [];

	let query: string | null = '';
	let property: string = 'all';

	// on chage of property, console log the property

	function filterByProperty() {
		let url = new URL(window.location.href);
		url.searchParams.set('property', property);
		goto(url.toString(), { invalidateAll: true });
	}

	onMount(() => {
		const urlParams = new URLSearchParams(window.location.search);
		query = urlParams.get('query');
	});

	console.log(data);
	$: {
		if (data.props) {
			myAdventures = data.props.adventures;
			publicAdventures = data.props.adventures;

			if (data.user?.pk != null) {
				myAdventures = myAdventures.filter((adventure) => adventure.user_id === data.user?.pk);
			} else {
				myAdventures = [];
			}

			publicAdventures = publicAdventures.filter(
				(adventure) => adventure.user_id !== data.user?.pk
			);

			if (data.props.osmData) {
				osmResults = data.props.osmData;
			}
		}
	}

	let adventureToEdit: Adventure;
	let isAdventureModalOpen: boolean = false;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isAdventureModalOpen = true;
	}

	function saveEdit(event: CustomEvent<Adventure>) {
		console.log(event.detail);
		myAdventures = myAdventures.map((adventure) => {
			if (adventure.id === event.detail.id) {
				return event.detail;
			}
			return adventure;
		});
		isAdventureModalOpen = false;
		console.log(myAdventures);
	}
</script>

{#if isAdventureModalOpen}
	<AdventureModal
		{adventureToEdit}
		on:close={() => (isAdventureModalOpen = false)}
		on:save={filterByProperty}
	/>
{/if}

{#if myAdventures.length === 0 && osmResults.length === 0}
	<NotFound error={data.error} />
{/if}

{#if myAdventures.length !== 0}
	<h2 class="text-center font-bold text-2xl mb-4">{$t('search.adventurelog_results')}</h2>
	<div class="flex items-center justify-center mt-2 mb-2">
		<div class="join">
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('adventures.all')}
				id="all"
				checked
				on:change={() => (property = 'all')}
			/>
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('adventures.name')}
				id="name"
				on:change={() => (property = 'name')}
			/>
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('transportation.type')}
				id="type"
				on:change={() => (property = 'type')}
			/>
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('adventures.location')}
				id="location"
				on:change={() => (property = 'location')}
			/>
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('adventures.description')}
				id="description"
				on:change={() => (property = 'description')}
			/>
			<input
				class="join-item btn"
				type="radio"
				name="filter"
				aria-label={$t('adventures.activity_types')}
				id="activity_types"
				on:change={() => (property = 'activity_types')}
			/>
		</div>
		<button class="btn btn-primary ml-2" type="button" on:click={filterByProperty}
			>{$t('adventures.filter')}</button
		>
	</div>
{/if}

{#if myAdventures.length > 0}
	<h2 class="text-center font-bold text-2xl mb-4">{$t('adventures.my_adventures')}</h2>
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each myAdventures as adventure}
			<AdventureCard
				user={data.user}
				type={adventure.type}
				{adventure}
				on:delete={deleteAdventure}
				on:edit={editAdventure}
			/>
		{/each}
	</div>
{/if}

{#if publicAdventures.length > 0}
	<h2 class="text-center font-bold text-2xl mb-4">{$t('search.public_adventures')}</h2>
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each publicAdventures as adventure}
			<AdventureCard
				user={null}
				type={adventure.type}
				{adventure}
				on:delete={deleteAdventure}
				on:edit={editAdventure}
			/>
		{/each}
	</div>
{/if}
{#if myAdventures.length > 0 && osmResults.length > 0 && publicAdventures.length > 0}
	<div class="divider"></div>
{/if}
{#if osmResults.length > 0}
	<h2 class="text-center font-bold mt-2 text-2xl mb-4">{$t('search.online_results')}</h2>
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each osmResults as result}
			<div class="bg-base-300 rounded-lg shadow-md p-4 w-96 mb-2">
				<h2 class="text-xl font-bold">{result.display_name}</h2>
				<p>{result.type}</p>
				<p>{result.lat}, {result.lon}</p>
			</div>
		{/each}
	</div>
{/if}

<svelte:head>
	<title>Search{query ? `: ${query}` : ''}</title>
	<meta name="description" content="Search your adventures." />
</svelte:head>
