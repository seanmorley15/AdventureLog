<script lang="ts">
	import type { Adventure, Checklist, Collection, Note, Transportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { goto } from '$app/navigation';
	import Lost from '$lib/assets/undraw_lost.svg';

	import Plus from '~icons/mdi/plus';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureLink from '$lib/components/AdventureLink.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import { DefaultMarker, MapLibre, Popup } from 'svelte-maplibre';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import EditTransportation from '$lib/components/EditTransportation.svelte';
	import NewTransportation from '$lib/components/NewTransportation.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';

	import {
		groupAdventuresByDate,
		groupNotesByDate,
		groupTransportationsByDate,
		groupChecklistsByDate
	} from '$lib';
	import ChecklistCard from '$lib/components/ChecklistCard.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import AdventureModal from '$lib/components/AdventureModal.svelte';

	export let data: PageData;
	console.log(data);

	let collection: Collection;

	let adventures: Adventure[] = [];

	let numVisited: number = 0;
	let numAdventures: number = 0;

	let transportations: Transportation[] = [];
	let notes: Note[] = [];
	let checklists: Checklist[] = [];

	let numberOfDays: number = NaN;

	$: {
		numAdventures = adventures.filter((a) => a.type === 'visited' || a.type === 'planned').length;
		numVisited = adventures.filter((a) => a.type === 'visited').length;
	}

	let notFound: boolean = false;
	let isShowingLinkModal: boolean = false;
	let isShowingCreateModal: boolean = false;
	let isShowingTransportationModal: boolean = false;
	let isShowingChecklistModal: boolean = false;

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
		if (collection.checklists) {
			checklists = collection.checklists;
		}
	});

	function deleteAdventure(event: CustomEvent<string>) {
		adventures = adventures.filter((a) => a.id !== event.detail);
	}

	async function addAdventure(event: CustomEvent<Adventure>) {
		console.log(event.detail);
		if (adventures.find((a) => a.id === event.detail.id)) {
			return;
		} else {
			let adventure = event.detail;

			let res = await fetch(`/api/adventures/${adventure.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ collection: collection.id.toString() })
			});

			if (res.ok) {
				console.log('Adventure added to collection');
				adventure = await res.json();
				adventures = [...adventures, adventure];
			} else {
				console.log('Error adding adventure to collection');
			}
		}
	}

	function changeType(event: CustomEvent<string>) {
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

	let adventureToEdit: Adventure | null = null;
	let transportationToEdit: Transportation;
	let isAdventureModalOpen: boolean = false;
	let isTransportationEditModalOpen: boolean = false;
	let isNoteModalOpen: boolean = false;
	let noteToEdit: Note | null;
	let checklistToEdit: Checklist | null;

	let newType: string;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isAdventureModalOpen = true;
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

	function saveOrCreate(event: CustomEvent<Adventure>) {
		if (adventures.find((adventure) => adventure.id === event.detail.id)) {
			adventures = adventures.map((adventure) => {
				if (adventure.id === event.detail.id) {
					return event.detail;
				}
				return adventure;
			});
		} else {
			adventures = [event.detail, ...adventures];
		}
		isAdventureModalOpen = false;
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

{#if isAdventureModalOpen}
	<AdventureModal
		{adventureToEdit}
		on:close={() => (isAdventureModalOpen = false)}
		on:save={saveOrCreate}
		{collection}
	/>
{/if}

{#if isNoteModalOpen}
	<NoteModal
		note={noteToEdit}
		user={data.user}
		on:close={() => (isNoteModalOpen = false)}
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
		on:create={(event) => {
			notes = [event.detail, ...notes];
			isNoteModalOpen = false;
		}}
	/>
{/if}

{#if isShowingChecklistModal}
	<ChecklistModal
		{collection}
		user={data.user}
		checklist={checklistToEdit}
		on:close={() => (isShowingChecklistModal = false)}
		on:create={(event) => {
			checklists = [event.detail, ...checklists];
			isShowingChecklistModal = false;
		}}
		on:save={(event) => {
			checklists = checklists.map((checklist) => {
				if (checklist.id === event.detail.id) {
					return event.detail;
				}
				return checklist;
			});
			isShowingChecklistModal = false;
		}}
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
	{#if data.user && !collection.is_archived}
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
						{#if collection.user_id === data.user.pk}
							<p class="text-center font-bold text-lg">Link new...</p>
							<button
								class="btn btn-primary"
								on:click={() => {
									isShowingLinkModal = true;
								}}
							>
								Adventure</button
							>
						{/if}
						<p class="text-center font-bold text-lg">Add new...</p>
						<button
							class="btn btn-primary"
							on:click={() => {
								isAdventureModalOpen = true;
								adventureToEdit = null;
							}}
						>
							Adventure</button
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
								noteToEdit = null;
							}}
						>
							Note</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingChecklistModal = true;
								newType = '';
								checklistToEdit = null;
							}}
						>
							Checklist</button
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
	{#if collection.is_archived}
		<div class="flex items-center justify-center mt-4 mb-4">
			<div role="alert" class="alert alert-warning w-96 inline-flex items-center justify-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-6 w-6 shrink-0 stroke-current"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
					/>
				</svg>
				<span>This collection has been archived.</span>
			</div>
		</div>
	{/if}
	{#if collection.name}
		<h1 class="text-center font-extrabold text-4xl mb-2">{collection.name}</h1>
	{/if}
	{#if collection.description}
		<p class="text-center text-lg mb-2">{collection.description}</p>
	{/if}
	{#if adventures.length > 0}
		<div class="flex items-center justify-center mb-4">
			<div class="stats shadow bg-base-300">
				<div class="stat">
					<div class="stat-title">Collection Stats</div>
					<div class="stat-value">{numVisited}/{numAdventures} Visited</div>
					{#if numAdventures === numVisited}
						<div class="stat-desc">You've completed this collection! 🎉!</div>
					{:else}
						<div class="stat-desc">Keep exploring!</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if adventures.length == 0 && transportations.length == 0 && notes.length == 0 && checklists.length == 0}
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
					{collection}
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
					{collection}
				/>
			{/each}
		</div>
	{/if}

	{#if notes.length > 0}
		<h1 class="text-center font-bold text-4xl mt-4 mb-4">Notes</h1>
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each notes as note}
				<NoteCard
					{note}
					user={data.user || null}
					on:edit={(event) => {
						noteToEdit = event.detail;
						isNoteModalOpen = true;
					}}
					on:delete={(event) => {
						notes = notes.filter((n) => n.id != event.detail);
					}}
					{collection}
				/>
			{/each}
		</div>
	{/if}

	{#if checklists.length > 0}
		<h1 class="text-center font-bold text-4xl mt-4 mb-4">Checklists</h1>
		<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
			{#each checklists as checklist}
				<ChecklistCard
					{checklist}
					user={data.user || null}
					on:delete={(event) => {
						checklists = checklists.filter((n) => n.id != event.detail);
					}}
					on:edit={(event) => {
						checklistToEdit = event.detail;
						isShowingChecklistModal = true;
					}}
					{collection}
				/>
			{/each}
		</div>
	{/if}

	{#if collection.start_date && collection.end_date}
		<div class="divider"></div>
		<h1 class="text-center font-bold text-4xl mt-4">Itinerary by Date</h1>
		{#if numberOfDays}
			<p class="text-center text-lg pl-16 pr-16">Duration: {numberOfDays} days</p>
		{/if}
		<p class="text-center text-lg pl-16 pr-16">
			Dates: {new Date(collection.start_date).toLocaleDateString(undefined, { timeZone: 'UTC' })} - {new Date(
				collection.end_date
			).toLocaleDateString(undefined, { timeZone: 'UTC' })}
		</p>

		{#each Array(numberOfDays) as _, i}
			{@const startDate = new Date(collection.start_date)}
			{@const tempDate = new Date(startDate.getTime())}
			<!-- Clone startDate -->
			{@const adjustedDate = new Date(tempDate.setUTCDate(tempDate.getUTCDate() + i))}
			<!-- Add i days in UTC -->
			{@const dateString = adjustedDate.toISOString().split('T')[0]}

			{@const dayAdventures =
				groupAdventuresByDate(adventures, new Date(collection.start_date), numberOfDays)[
					dateString
				] || []}

			{@const dayTransportations =
				groupTransportationsByDate(transportations, new Date(collection.start_date), numberOfDays)[
					dateString
				] || []}

			{@const dayNotes =
				groupNotesByDate(notes, new Date(collection.start_date), numberOfDays)[dateString] || []}

			{@const dayChecklists =
				groupChecklistsByDate(checklists, new Date(collection.start_date), numberOfDays)[
					dateString
				] || []}

			<h2 class="text-center font-semibold text-2xl mb-2 mt-4">
				Day {i + 1} - {adjustedDate.toLocaleDateString(undefined, { timeZone: 'UTC' })}
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
							user={data.user || null}
							on:edit={(event) => {
								noteToEdit = event.detail;
								isNoteModalOpen = true;
							}}
							on:delete={(event) => {
								notes = notes.filter((n) => n.id != event.detail);
							}}
						/>
					{/each}
				{/if}
				{#if dayChecklists.length > 0}
					{#each dayChecklists as checklist}
						<ChecklistCard
							{checklist}
							user={data.user || null}
							on:delete={(event) => {
								notes = notes.filter((n) => n.id != event.detail);
							}}
							on:edit={(event) => {
								checklistToEdit = event.detail;
								isShowingChecklistModal = true;
							}}
						/>
					{/each}
				{/if}

				{#if dayAdventures.length == 0 && dayTransportations.length == 0 && dayNotes.length == 0 && dayChecklists.length == 0}
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
							<!-- <p>
								{adventure.
									? new Date(adventure.date).toLocaleDateString(undefined, { timeZone: 'UTC' })
									: ''}
							</p> -->
						</Popup>
					</DefaultMarker>
				{/if}
			{/each}
		</MapLibre>
	{/if}
{/if}

<svelte:head>
	<title
		>{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: 'Collection'}</title
	>
	<meta
		name="description"
		content="Learn more about {data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}.`
			: 'your adventures.'}"
	/>
</svelte:head>
