<script lang="ts">
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure, OpenStreetMapPlace } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import { appVersion } from '$lib/config';

	export let data: PageData;

	function deleteAdventure(event: CustomEvent<number>) {
		myAdventures = myAdventures.filter((adventure) => adventure.id !== event.detail);
	}

	let osmResults: OpenStreetMapPlace[] = [];
	let myAdventures: Adventure[] = [];
	let publicAdventures: Adventure[] = [];

	let query: string | null = '';

	onMount(() => {
		const urlParams = new URLSearchParams(window.location.search);
		query = urlParams.get('query');

		fetchData();
	});

	async function fetchData() {
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
			headers: {
				'User-Agent': `AdventureLog / ${appVersion} `
			}
		});
		const data = await res.json();
		osmResults = data;
	}

	onMount(async () => {
		let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
			headers: {
				'User-Agent': `AdventureLog / ${appVersion} `
			}
		});
		const data = await res.json();
		osmResults = data;
	});

	console.log(data);

	if (data.props) {
		myAdventures = data.props.adventures;
		publicAdventures = data.props.adventures;

		if (data.user?.pk != null) {
			myAdventures = myAdventures.filter((adventure) => adventure.user_id === data.user?.pk ?? -1);
		} else {
			myAdventures = [];
		}

		publicAdventures = publicAdventures.filter((adventure) => adventure.user_id !== data.user?.pk);
	}

	let adventureToEdit: Adventure;
	let isEditModalOpen: boolean = false;
	let isShowingCreateModal: boolean = false;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isEditModalOpen = true;
	}

	function saveEdit(event: CustomEvent<Adventure>) {
		myAdventures = myAdventures.map((adventure) => {
			if (adventure.id === event.detail.id) {
				return event.detail;
			}
			return adventure;
		});
		isEditModalOpen = false;
	}
</script>

{#if isEditModalOpen}
	<EditAdventure
		{adventureToEdit}
		on:close={() => (isEditModalOpen = false)}
		on:saveEdit={saveEdit}
	/>
{/if}

{#if myAdventures.length === 0 && osmResults.length === 0}
	<NotFound error={data.error} />
{/if}

{#if myAdventures.length !== 0 && publicAdventures.length !== 0}
	<h2 class="text-center font-bold text-2xl mb-4">AdventureLog Results</h2>
{/if}

{#if myAdventures.length > 0}
	<h2 class="text-center font-bold text-2xl mb-4">My Adventures</h2>
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
	<h2 class="text-center font-bold text-2xl mb-4">Public Adventures</h2>
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
	<h2 class="text-center font-bold text-2xl mb-4">Online Results</h2>
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
