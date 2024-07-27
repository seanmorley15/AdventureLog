<script lang="ts">
	import type { Adventure, Collection } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';

	import Plus from '~icons/mdi/plus';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureLink from '$lib/components/AdventureLink.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import NotFound from '$lib/components/NotFound.svelte';

	export let data: PageData;

	let collection: Collection;

	let adventures: Adventure[] = [];
	let numVisited: number = 0;

	let numberOfDays: number = NaN;

	$: {
		numVisited = adventures.filter((a) => a.type === 'visited').length;
	}

	let notFound: boolean = false;
	let isShowingCreateModal: boolean = false;

	onMount(() => {
		if (data.props.adventure) {
			collection = data.props.adventure;
			adventures = collection.adventures as Adventure[];
		} else {
			notFound = true;
		}
		if (collection.start_date && collection.end_date) {
			numberOfDays =
				Math.floor(
					(new Date(collection.end_date).getTime() - new Date(collection.start_date).getTime()) /
						(1000 * 60 * 60 * 24)
				) + 1;
		}
	});

	function deleteAdventure(event: CustomEvent<number>) {
		adventures = adventures.filter((a) => a.id !== event.detail);
	}

	function groupAdventuresByDate(
		adventures: Adventure[],
		startDate: Date
	): Record<string, Adventure[]> {
		const groupedAdventures: Record<string, Adventure[]> = {};

		for (let i = 0; i < numberOfDays; i++) {
			const currentDate = new Date(startDate);
			currentDate.setDate(startDate.getDate() + i);
			const dateString = currentDate.toISOString().split('T')[0];
			groupedAdventures[dateString] = [];
		}

		adventures.forEach((adventure) => {
			if (adventure.date) {
				const adventureDate = new Date(adventure.date).toISOString().split('T')[0];
				if (groupedAdventures[adventureDate]) {
					groupedAdventures[adventureDate].push(adventure);
				}
			}
		});

		return groupedAdventures;
	}

	async function addAdventure(event: CustomEvent<Adventure>) {
		console.log(event.detail);
		if (adventures.find((a) => a.id === event.detail.id)) {
			return;
		} else {
			let adventure = event.detail;
			let formData = new FormData();
			formData.append('collection_id', collection.id.toString());

			let res = await fetch(`/adventures/${adventure.id}?/addToCollection`, {
				method: 'POST',
				body: formData // Remove the Content-Type header
			});

			if (res.ok) {
				console.log('Adventure added to collection');
				adventures = [...adventures, adventure];
			} else {
				console.log('Error adding adventure to collection');
			}
		}
	}

	function changeType(event: CustomEvent<number>) {
		adventures = adventures.map((adventure) => {
			if (adventure.id == event.detail) {
				if (adventure.type == 'visited') {
					adventure.type = 'planned';
				} else {
					adventure.type = 'visited';
				}
			}
			return adventure;
		});
	}

	let adventureToEdit: Adventure;
	let isEditModalOpen: boolean = false;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isEditModalOpen = true;
	}

	function saveEdit(event: CustomEvent<Adventure>) {
		adventures = adventures.map((adventure) => {
			if (adventure.id === event.detail.id) {
				return event.detail;
			}
			return adventure;
		});
		isEditModalOpen = false;
	}
</script>

{#if isShowingCreateModal}
	<AdventureLink
		user={data?.user ?? null}
		on:close={() => {
			isShowingCreateModal = false;
		}}
		on:add={addAdventure}
	/>
{/if}

{#if isEditModalOpen}
	<EditAdventure
		{adventureToEdit}
		on:close={() => (isEditModalOpen = false)}
		on:saveEdit={saveEdit}
	/>
{/if}

{#if notFound}
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8 -mt-20"
	>
		<div class="mx-auto max-w-md text-center">
			<div class="flex items-center justify-center">
				<img src={Lost} alt="Lost" class="w-1/2" />
			</div>
			<h1 class="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
				Adventure not Found
			</h1>
			<p class="mt-4 text-muted-foreground">
				The adventure you were looking for could not be found. Please try a different adventure or
				check back later.
			</p>
			<div class="mt-6">
				<button class="btn btn-primary" on:click={() => goto('/')}>Homepage</button>
			</div>
		</div>
	</div>
{/if}

{#if !collection && !notFound}
	<div class="flex justify-center items-center w-full mt-16">
		<span class="loading loading-spinner w-24 h-24"></span>
	</div>
{/if}
{#if collection}
	<div class="fixed bottom-4 right-4 z-[999]">
		<div class="flex flex-row items-center justify-center gap-4">
			<div class="dropdown dropdown-top dropdown-end">
				<div tabindex="0" role="button" class="btn m-1 size-16 btn-primary">
					<Plus class="w-8 h-8" />
				</div>
				<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
				<ul
					tabindex="0"
					class="dropdown-content z-[1] menu p-4 shadow bg-base-300 text-base-content rounded-box w-52 gap-4"
				>
					<p class="text-center font-bold text-lg">Link new...</p>
					<button
						class="btn btn-primary"
						on:click={() => {
							isShowingCreateModal = true;
						}}
					>
						Adventure</button
					>

					<!-- <button
			class="btn btn-primary"
			on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
		  > -->
				</ul>
			</div>
		</div>
	</div>
	{#if collection.name}
		<h1 class="text-center font-extrabold text-4xl mb-2">{collection.name}</h1>
	{/if}
	{#if adventures.length > 0}
		<div class="flex items-center justify-center mb-4">
			<div class="stats shadow bg-base-300">
				<div class="stat">
					<div class="stat-title">Collection Stats</div>
					<div class="stat-value">{numVisited}/{adventures.length} Visited</div>
					{#if numVisited === adventures.length}
						<div class="stat-desc">You've completed this collection! 🎉!</div>
					{:else}
						<div class="stat-desc">Keep exploring!</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
	<h1 class="text-center font-semibold text-2xl mt-4 mb-2">Linked Adventures</h1>
	{#if adventures.length == 0}
		<NotFound error={undefined} />
	{/if}
	<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
		{#each adventures as adventure}
			<AdventureCard
				user={data.user}
				on:edit={editAdventure}
				on:delete={deleteAdventure}
				type={adventure.type}
				{adventure}
				on:typeChange={changeType}
			/>
		{/each}
	</div>

	{#if numberOfDays}
		<p class="text-center text-lg mt-4 pl-16 pr-16">Duration: {numberOfDays} days</p>
	{/if}
	{#if collection.start_date && collection.end_date}
		<p class="text-center text-lg mt-4 pl-16 pr-16">
			Dates: {new Date(collection.start_date).toLocaleDateString('en-US', { timeZone: 'UTC' })} - {new Date(
				collection.end_date
			).toLocaleDateString('en-US', { timeZone: 'UTC' })}
		</p>

		{#each Array(numberOfDays) as _, i}
			{@const currentDate = new Date(collection.start_date)}
			{@const temp = currentDate.setDate(currentDate.getDate() + i)}
			{@const dateString = currentDate.toISOString().split('T')[0]}
			{@const dayAdventures = groupAdventuresByDate(adventures, new Date(collection.start_date))[
				dateString
			]}

			<h2 class="text-center text-xl mt-4">
				Day {i + 1} - {currentDate.toLocaleDateString('en-US', { timeZone: 'UTC' })}
			</h2>

			{#if dayAdventures.length > 0}
				<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
					{#each dayAdventures as adventure}
						<AdventureCard
							user={data.user}
							on:edit={editAdventure}
							on:delete={deleteAdventure}
							type={adventure.type}
							{adventure}
							on:typeChange={changeType}
						/>
					{/each}
				</div>
			{:else}
				<p class="text-center text-lg mt-2">No adventures planned for this day.</p>
			{/if}
		{/each}
	{/if}
{/if}
