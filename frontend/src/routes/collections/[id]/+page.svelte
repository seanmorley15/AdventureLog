<script lang="ts">
	import type { Adventure, Collection, Note, Transportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';

	import Plus from '~icons/mdi/plus';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureLink from '$lib/components/AdventureLink.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import EditTransportation from '$lib/components/EditTransportation.svelte';
	import NewTransportation from '$lib/components/NewTransportation.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';

	export let data: PageData;
	console.log(data);

	let collection: Collection;

	let adventures: Adventure[] = [];
	let numVisited: number = 0;
	let transportations: Transportation[] = [];
	let notes: Note[] = [];

	let numberOfDays: number = NaN;

	$: {
		numVisited = adventures.filter((a) => a.type === 'visited').length;
	}

	let notFound: boolean = false;
	let isShowingLinkModal: boolean = false;
	let isShowingCreateModal: boolean = false;
	let isShowingTransportationModal: boolean = false;

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
		if (collection.transportations) {
			transportations = collection.transportations;
		}
		if (collection.notes) {
			notes = collection.notes;
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

	function groupTransportationsByDate(
		transportations: Transportation[],
		startDate: Date
	): Record<string, Transportation[]> {
		const groupedTransportations: Record<string, Transportation[]> = {};

		for (let i = 0; i < numberOfDays; i++) {
			const currentDate = new Date(startDate);
			currentDate.setDate(startDate.getDate() + i);
			const dateString = currentDate.toISOString().split('T')[0];
			groupedTransportations[dateString] = [];
		}

		transportations.forEach((transportation) => {
			if (transportation.date) {
				const transportationDate = new Date(transportation.date).toISOString().split('T')[0];
				if (groupedTransportations[transportationDate]) {
					groupedTransportations[transportationDate].push(transportation);
				}
			}
		});

		return groupedTransportations;
	}

	function groupNotesByDate(notes: Note[], startDate: Date): Record<string, Note[]> {
		const groupedNotes: Record<string, Note[]> = {};

		for (let i = 0; i < numberOfDays; i++) {
			const currentDate = new Date(startDate);
			currentDate.setDate(startDate.getDate() + i);
			const dateString = currentDate.toISOString().split('T')[0];
			groupedNotes[dateString] = [];
		}

		notes.forEach((note) => {
			if (note.date) {
				const noteDate = new Date(note.date).toISOString().split('T')[0];
				if (groupedNotes[noteDate]) {
					groupedNotes[noteDate].push(note);
				}
			}
		});

		return groupedNotes;
	}

	function createAdventure(event: CustomEvent<Adventure>) {
		adventures = [event.detail, ...adventures];
		isShowingCreateModal = false;
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
	let transportationToEdit: Transportation;
	let isEditModalOpen: boolean = false;
	let isTransportationEditModalOpen: boolean = false;
	let isNoteModalOpen: boolean = false;
	let noteToEdit: Note;

	let newType: string;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isEditModalOpen = true;
	}

	function saveNewTransportation(event: CustomEvent<Transportation>) {
		transportations = transportations.map((transportation) => {
			if (transportation.id === event.detail.id) {
				return event.detail;
			}
			return transportation;
		});
		isTransportationEditModalOpen = false;
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

{#if isShowingLinkModal}
	<AdventureLink
		user={data?.user ?? null}
		on:close={() => {
			isShowingLinkModal = false;
		}}
		on:add={addAdventure}
	/>
{/if}

{#if isTransportationEditModalOpen}
	<EditTransportation
		{transportationToEdit}
		on:close={() => (isTransportationEditModalOpen = false)}
		on:saveEdit={saveNewTransportation}
		startDate={collection.start_date}
		endDate={collection.end_date}
	/>
{/if}

{#if isEditModalOpen}
	<EditAdventure
		{adventureToEdit}
		on:close={() => (isEditModalOpen = false)}
		on:saveEdit={saveEdit}
		startDate={collection.start_date}
		endDate={collection.end_date}
	/>
{/if}

{#if isNoteModalOpen}
	<NoteModal
		note={noteToEdit}
		on:close={() => (isNoteModalOpen = false)}
		startDate={collection.start_date}
		endDate={collection.end_date}
		{collection}
		on:save={(event) => {
			notes = notes.map((note) => {
				if (note.id === event.detail.id) {
					return event.detail;
				}
				return note;
			});
			isNoteModalOpen = false;
		}}
		on:close={() => (isNoteModalOpen = false)}
	/>
{/if}

{#if isShowingCreateModal}
	<NewAdventure
		type={newType}
		collection_id={collection.id}
		on:create={createAdventure}
		on:close={() => (isShowingCreateModal = false)}
		startDate={collection.start_date}
		endDate={collection.end_date}
	/>
{/if}

{#if isShowingTransportationModal}
	<NewTransportation
		on:close={() => (isShowingTransportationModal = false)}
		on:add={(event) => {
			transportations = [event.detail, ...transportations];
			isShowingTransportationModal = false;
		}}
		{collection}
		startDate={collection.start_date}
		endDate={collection.end_date}
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
	{#if data.user}
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
								isShowingLinkModal = true;
							}}
						>
							Adventure</button
						>
						<p class="text-center font-bold text-lg">Add new...</p>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingCreateModal = true;
								newType = 'visited';
							}}
						>
							Visited Adventure</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingCreateModal = true;
								newType = 'planned';
							}}
						>
							Planned Adventure</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingCreateModal = true;
								newType = 'lodging';
							}}
						>
							Lodging</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingCreateModal = true;
								newType = 'dining';
							}}
						>
							Dining</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingTransportationModal = true;
								newType = '';
							}}
						>
							Transportation</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isNoteModalOpen = true;
								newType = '';
							}}
						>
							Note</button
						>

						<!-- <button
			class="btn btn-primary"
			on:click={() => (isShowingNewTrip = true)}>Trip Planner</button
		  > -->
					</ul>
				</div>
			</div>
		</div>
	{/if}
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

	{#if adventures.length == 0 && transportations.length == 0}
		<NotFound error={undefined} />
	{/if}
	{#if adventures.length > 0}
		<h1 class="text-center font-bold text-4xl mt-4 mb-2">Linked Adventures</h1>

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
	{/if}

	{#if transportations.length > 0}
		<h1 class="text-center font-bold text-4xl mt-4 mb-4">Transportation</h1>
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each transportations as transportation}
				<TransportationCard
					{transportation}
					user={data?.user}
					on:delete={(event) => {
						transportations = transportations.filter((t) => t.id != event.detail);
					}}
					on:edit={(event) => {
						transportationToEdit = event.detail;
						isTransportationEditModalOpen = true;
					}}
				/>
			{/each}
		</div>
	{/if}

	{#if collection.start_date && collection.end_date}
		<h1 class="text-center font-bold text-4xl mt-4">Itinerary by Date</h1>
		{#if numberOfDays}
			<p class="text-center text-lg pl-16 pr-16">Duration: {numberOfDays} days</p>
		{/if}
		<p class="text-center text-lg pl-16 pr-16">
			Dates: {new Date(collection.start_date).toLocaleDateString('en-US', { timeZone: 'UTC' })} - {new Date(
				collection.end_date
			).toLocaleDateString('en-US', { timeZone: 'UTC' })}
		</p>
		<div class="divider"></div>

		{#each Array(numberOfDays) as _, i}
			{@const currentDate = new Date(collection.start_date)}
			{@const temp = currentDate.setDate(currentDate.getDate() + i)}
			{@const dateString = currentDate.toISOString().split('T')[0]}
			{@const dayAdventures = groupAdventuresByDate(adventures, new Date(collection.start_date))[
				dateString
			]}
			{@const dayTransportations = groupTransportationsByDate(
				transportations,
				new Date(collection.start_date)
			)[dateString]}
			{@const dayNotes = groupNotesByDate(notes, new Date(collection.start_date))[dateString]}

			<h2 class="text-center font-semibold text-2xl mb-2 mt-4">
				Day {i + 1} - {currentDate.toLocaleDateString('en-US', { timeZone: 'UTC' })}
			</h2>
			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#if dayAdventures.length > 0}
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
				{/if}
				{#if dayTransportations.length > 0}
					{#each dayTransportations as transportation}
						<TransportationCard
							{transportation}
							user={data?.user}
							on:delete={(event) => {
								transportations = transportations.filter((t) => t.id != event.detail);
							}}
							on:edit={(event) => {
								transportationToEdit = event.detail;
								isTransportationEditModalOpen = true;
							}}
						/>
					{/each}
				{/if}
				{#if dayNotes.length > 0}
					{#each dayNotes as note}
						<NoteCard
							{note}
							on:edit={(event) => {
								noteToEdit = event.detail;
								isNoteModalOpen = true;
							}}
						/>
					{/each}
				{/if}

				{#if dayAdventures.length == 0 && dayTransportations.length == 0 && dayNotes.length == 0}
					<p class="text-center text-lg mt-2">Nothing planned for this day. Enjoy the journey!</p>
				{/if}
			</div>
		{/each}

		<MapLibre
			style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
			class="flex items-center self-center justify-center aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-10/12 mt-4"
			standardControls
		>
			<!-- MapEvents gives you access to map events even from other components inside the map,
  where you might not have access to the top-level `MapLibre` component. In this case
  it would also work to just use on:click on the MapLibre component itself. -->
			<!-- <MapEvents on:click={addMarker} /> -->

			{#each adventures as adventure}
				{#if adventure.longitude && adventure.latitude}
					<DefaultMarker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
						<Popup openOn="click" offset={[0, -10]}>
							<div class="text-lg text-black font-bold">{adventure.name}</div>
							<p class="font-semibold text-black text-md">
								{adventure.type.charAt(0).toUpperCase() + adventure.type.slice(1)}
							</p>
							<p>
								{adventure.date
									? new Date(adventure.date).toLocaleDateString('en-US', { timeZone: 'UTC' })
									: ''}
							</p>
						</Popup>
					</DefaultMarker>
				{/if}
			{/each}
		</MapLibre>
	{/if}
{/if}
