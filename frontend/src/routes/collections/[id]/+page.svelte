<script lang="ts">
	import type { Adventure, Checklist, Collection, Note, Transportation } from '$lib/types';
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import { marked } from 'marked'; // Import the markdown parser

	import { t } from 'svelte-i18n';

	// @ts-ignore
	import Calendar from '@event-calendar/core';
	// @ts-ignore
	import TimeGrid from '@event-calendar/time-grid';
	// @ts-ignore
	import DayGrid from '@event-calendar/day-grid';

	import Plus from '~icons/mdi/plus';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureLink from '$lib/components/AdventureLink.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import { DefaultMarker, MapLibre, Marker, Popup } from 'svelte-maplibre';
	import TransportationCard from '$lib/components/TransportationCard.svelte';
	import NoteCard from '$lib/components/NoteCard.svelte';
	import NoteModal from '$lib/components/NoteModal.svelte';

	import {
		groupAdventuresByDate,
		groupNotesByDate,
		groupTransportationsByDate,
		groupChecklistsByDate,
		osmTagToEmoji
	} from '$lib';
	import ChecklistCard from '$lib/components/ChecklistCard.svelte';
	import ChecklistModal from '$lib/components/ChecklistModal.svelte';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import TransportationModal from '$lib/components/TransportationModal.svelte';

	export let data: PageData;
	console.log(data);

	const renderMarkdown = (markdown: string) => {
		return marked(markdown);
	};

	let collection: Collection;

	// add christmas and new years
	// dates = Array.from({ length: 25 }, (_, i) => {
	// 	const date = new Date();
	// 	date.setMonth(11);
	// 	date.setDate(i + 1);
	// 	return {
	// 		id: i.toString(),
	// 		start: date.toISOString(),
	// 		end: date.toISOString(),
	// 		title: '🎄'
	// 	};
	// });

	let dates: Array<{
		id: string;
		start: string;
		end: string;
		title: string;
		backgroundColor?: string;
	}> = [];

	// Initialize calendar plugins and options
	let plugins = [TimeGrid, DayGrid];
	let options = {
		view: 'dayGridMonth',
		events: dates // Assign `dates` reactively
	};

	// Compute `dates` array reactively
	$: {
		dates = [];

		if (adventures) {
			dates = dates.concat(
				adventures.flatMap((adventure) =>
					adventure.visits.map((visit) => ({
						id: adventure.id,
						start: visit.start_date || '', // Ensure it's a string
						end: visit.end_date || visit.start_date || '', // Ensure it's a string
						title: adventure.name + (adventure.category?.icon ? ' ' + adventure.category.icon : '')
					}))
				)
			);
		}

		if (transportations) {
			dates = dates.concat(
				transportations.map((transportation) => ({
					id: transportation.id,
					start: transportation.date || '', // Ensure it's a string
					end: transportation.end_date || transportation.date || '', // Ensure it's a string
					title: transportation.name + (transportation.type ? ` (${transportation.type})` : '')
				}))
			);
		}

		// Update `options.events` when `dates` changes
		options = { ...options, events: dates };
	}

	let currentView: string = 'itinerary';

	let adventures: Adventure[] = [];

	let numVisited: number = 0;
	let numAdventures: number = 0;

	let transportations: Transportation[] = [];
	let notes: Note[] = [];
	let checklists: Checklist[] = [];

	let numberOfDays: number = NaN;

	function getTransportationEmoji(type: string): string {
		switch (type) {
			case 'car':
				return '🚗';
			case 'plane':
				return '✈️';
			case 'train':
				return '🚆';
			case 'bus':
				return '🚌';
			case 'boat':
				return '⛵';
			case 'bike':
				return '🚲';
			case 'walking':
				return '🚶';
			case 'other':
				return '🚀';
			default:
				return '🚀';
		}
	}

	$: {
		numAdventures = adventures.length;
		numVisited = adventures.filter((adventure) => adventure.is_visited).length;
	}

	let notFound: boolean = false;
	let isShowingLinkModal: boolean = false;
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
		if (!collection.start_date) {
			currentView = 'all';
		} else {
			currentView = 'itinerary';
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

	function recomendationToAdventure(recomendation: any) {
		adventureToEdit = {
			id: '',
			user_id: null,
			name: recomendation.name,
			latitude: recomendation.latitude,
			longitude: recomendation.longitude,
			images: [],
			is_visited: false,
			is_public: false,
			visits: [],
			category: {
				display_name: recomendation.tag
					.replace(/_/g, ' ')
					.replace(/\b\w/g, (char: string) => char.toUpperCase()),
				icon: osmTagToEmoji(recomendation.tag),
				id: '',
				name: recomendation.tag,
				user_id: ''
			}
		};
		isAdventureModalOpen = true;
	}

	let adventureToEdit: Adventure | null = null;
	let transportationToEdit: Transportation | null = null;
	let isAdventureModalOpen: boolean = false;
	let isNoteModalOpen: boolean = false;
	let noteToEdit: Note | null;
	let checklistToEdit: Checklist | null;

	let newType: string;

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isAdventureModalOpen = true;
	}

	function editTransportation(event: CustomEvent<Transportation>) {
		transportationToEdit = event.detail;
		isShowingTransportationModal = true;
	}

	function saveOrCreateAdventure(event: CustomEvent<Adventure>) {
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

	let isPopupOpen = false;

	function togglePopup() {
		isPopupOpen = !isPopupOpen;
	}

	let recomendationsData: any;
	let loadingRecomendations: boolean = false;
	let recomendationsRange: number = 1600;
	let recomendationType: string = 'tourism';
	let recomendationTags: { name: string; display_name: string }[] = [];
	let selectedRecomendationTag: string = '';
	let filteredRecomendations: any[] = [];

	$: {
		if (recomendationsData && selectedRecomendationTag) {
			filteredRecomendations = recomendationsData.filter(
				(r: any) => r.tag === selectedRecomendationTag
			);
		} else {
			filteredRecomendations = recomendationsData;
		}
		console.log(filteredRecomendations);
		console.log(selectedRecomendationTag);
	}
	async function getRecomendations(adventure: Adventure) {
		recomendationsData = null;
		selectedRecomendationTag = '';
		loadingRecomendations = true;
		let res = await fetch(
			`/api/overpass/query/?lat=${adventure.latitude}&lon=${adventure.longitude}&radius=${recomendationsRange}&category=${recomendationType}`
		);
		if (!res.ok) {
			console.log('Error fetching recommendations');
			return;
		}
		let data = await res.json();
		recomendationsData = data;

		if (recomendationsData && recomendationsData.some((r: any) => r.longitude && r.latitude)) {
			const tagMap = new Map();
			recomendationsData.forEach((r: any) => {
				const tag = formatTag(r.tag);
				if (tag) {
					tagMap.set(r.tag, { name: r.tag, display_name: tag });
				}
			});
			recomendationTags = Array.from(tagMap.values());

			function formatTag(tag: string): string {
				if (tag) {
					return (
						tag
							.split('_')
							.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
							.join(' ') + osmTagToEmoji(tag)
					);
				} else {
					return '';
				}
			}
		}
		loadingRecomendations = false;
		console.log(recomendationTags);
	}

	function saveOrCreateTransportation(event: CustomEvent<Transportation>) {
		if (transportations.find((transportation) => transportation.id === event.detail.id)) {
			// Update existing transportation
			transportations = transportations.map((transportation) => {
				if (transportation.id === event.detail.id) {
					return event.detail;
				}
				return transportation;
			});
		} else {
			// Create new transportation
			transportations = [event.detail, ...transportations];
		}
		isShowingTransportationModal = false;
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

{#if isShowingTransportationModal}
	<TransportationModal
		{transportationToEdit}
		on:close={() => (isShowingTransportationModal = false)}
		on:save={saveOrCreateTransportation}
		{collection}
	/>
{/if}

{#if isAdventureModalOpen}
	<AdventureModal
		{adventureToEdit}
		on:close={() => (isAdventureModalOpen = false)}
		on:save={saveOrCreateAdventure}
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

{#if !collection && !notFound}
	<div class="flex justify-center items-center w-full mt-16">
		<span class="loading loading-spinner w-24 h-24"></span>
	</div>
{/if}
{#if collection}
	{#if data.user && data.user.uuid && (data.user.uuid == collection.user_id || (collection.shared_with && collection.shared_with.includes(data.user.uuid))) && !collection.is_archived}
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
						{#if collection.user_id === data.user.uuid}
							<p class="text-center font-bold text-lg">{$t('adventures.link_new')}</p>
							<button
								class="btn btn-primary"
								on:click={() => {
									isShowingLinkModal = true;
								}}
							>
								{$t('adventures.adventure')}</button
							>
						{/if}
						<p class="text-center font-bold text-lg">{$t('adventures.add_new')}</p>
						<button
							class="btn btn-primary"
							on:click={() => {
								isAdventureModalOpen = true;
								adventureToEdit = null;
							}}
						>
							{$t('adventures.adventure')}</button
						>

						<button
							class="btn btn-primary"
							on:click={() => {
								// Reset the transportation object for creating a new one
								transportationToEdit = null;
								isShowingTransportationModal = true;
								newType = '';
							}}
						>
							{$t('adventures.transportation')}</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isNoteModalOpen = true;
								newType = '';
								noteToEdit = null;
							}}
						>
							{$t('adventures.note')}</button
						>
						<button
							class="btn btn-primary"
							on:click={() => {
								isShowingChecklistModal = true;
								newType = '';
								checklistToEdit = null;
							}}
						>
							{$t('adventures.checklist')}</button
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
				<span>{$t('adventures.collection_archived')}</span>
			</div>
		</div>
	{/if}
	{#if collection.name}
		<h1 class="text-center font-extrabold text-4xl mb-2">{collection.name}</h1>
	{/if}
	{#if collection.link}
		<div class="flex items-center justify-center mb-2">
			<a href={collection.link} target="_blank" rel="noopener noreferrer" class="btn btn-primary">
				{$t('adventures.visit_link')}
			</a>
		</div>
	{/if}

	{#if collection && !collection.start_date && adventures.length == 0 && transportations.length == 0 && notes.length == 0 && checklists.length == 0}
		<NotFound error={undefined} />
	{/if}

	{#if collection.description}
		<div class="flex justify-center mt-4 max-w-screen-lg mx-auto">
			<article
				class="prose overflow-auto max-h-96 max-w-full p-4 border border-base-300 rounded-lg bg-base-300 mb-4"
				style="overflow-y: auto;"
			>
				{@html renderMarkdown(collection.description)}
			</article>
		</div>
	{/if}

	{#if adventures.length > 0}
		<div class="flex items-center justify-center mb-4">
			<div class="stats shadow bg-base-300">
				<div class="stat">
					<div class="stat-title">{$t('adventures.collection_stats')}</div>
					<div class="stat-value">{numVisited}/{numAdventures} Visited</div>
					{#if numAdventures === numVisited}
						<div class="stat-desc">{$t('adventures.collection_completed')}</div>
					{:else}
						<div class="stat-desc">{$t('adventures.keep_exploring')}</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	{#if collection.id}
		<div class="flex justify-center mx-auto">
			<!-- svelte-ignore a11y-missing-attribute -->
			<div role="tablist" class="tabs tabs-boxed tabs-lg max-w-full">
				<!-- svelte-ignore a11y-missing-attribute -->
				{#if collection.start_date}
					<a
						role="tab"
						class="tab {currentView === 'itinerary' ? 'tab-active' : ''}"
						tabindex="0"
						on:click={() => (currentView = 'itinerary')}
						on:keydown={(e) => e.key === 'Enter' && (currentView = 'itinerary')}>Itinerary</a
					>
				{/if}
				<a
					role="tab"
					class="tab {currentView === 'all' ? 'tab-active' : ''}"
					tabindex="0"
					on:click={() => (currentView = 'all')}
					on:keydown={(e) => e.key === 'Enter' && (currentView = 'all')}>All Linked Items</a
				>
				<a
					role="tab"
					class="tab {currentView === 'calendar' ? 'tab-active' : ''}"
					tabindex="0"
					on:click={() => (currentView = 'calendar')}
					on:keydown={(e) => e.key === 'Enter' && (currentView = 'calendar')}>Calendar</a
				>
				<a
					role="tab"
					class="tab {currentView === 'map' ? 'tab-active' : ''}"
					tabindex="0"
					on:click={() => (currentView = 'map')}
					on:keydown={(e) => e.key === 'Enter' && (currentView = 'map')}>Map</a
				>
				<a
					role="tab"
					class="tab {currentView === 'recommendations' ? 'tab-active' : ''}"
					tabindex="0"
					on:click={() => (currentView = 'recommendations')}
					on:keydown={(e) => e.key === 'Enter' && (currentView = 'recommendations')}
					>Recommendations</a
				>
			</div>
		</div>
	{/if}

	{#if currentView == 'all'}
		{#if adventures.length > 0}
			<h1 class="text-center font-bold text-4xl mt-4 mb-2">{$t('adventures.linked_adventures')}</h1>

			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each adventures as adventure}
					<AdventureCard
						user={data.user}
						on:edit={editAdventure}
						on:delete={deleteAdventure}
						{adventure}
						{collection}
					/>
				{/each}
			</div>
		{/if}

		{#if transportations.length > 0}
			<h1 class="text-center font-bold text-4xl mt-4 mb-4">{$t('adventures.transportations')}</h1>
			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each transportations as transportation}
					<TransportationCard
						{transportation}
						user={data?.user}
						on:delete={(event) => {
							transportations = transportations.filter((t) => t.id != event.detail);
						}}
						on:edit={editTransportation}
						{collection}
					/>
				{/each}
			</div>
		{/if}

		{#if notes.length > 0}
			<h1 class="text-center font-bold text-4xl mt-4 mb-4">{$t('adventures.notes')}</h1>
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
			<h1 class="text-center font-bold text-4xl mt-4 mb-4">{$t('adventures.checklists')}</h1>
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

		<!-- if none found -->
		{#if adventures.length == 0 && transportations.length == 0 && notes.length == 0 && checklists.length == 0}
			<NotFound error={undefined} />
		{/if}
	{/if}

	{#if collection.start_date && collection.end_date}
		{#if currentView == 'itinerary'}
			<div class="hero bg-base-200 py-8 mt-8">
				<div class="hero-content text-center">
					<div class="max-w-md">
						<h1 class="text-5xl font-bold mb-4">{$t('adventures.itineary_by_date')}</h1>
						{#if numberOfDays}
							<p class="text-lg mb-2">
								{$t('adventures.duration')}:
								<span class="badge badge-primary">{numberOfDays} {$t('adventures.days')}</span>
							</p>
						{/if}
						<p class="text-lg">
							Dates: <span class="font-semibold"
								>{new Date(collection.start_date).toLocaleDateString(undefined, {
									timeZone: 'UTC'
								})} -
								{new Date(collection.end_date).toLocaleDateString(undefined, {
									timeZone: 'UTC'
								})}</span
							>
						</p>
					</div>
				</div>
			</div>

			<div class="container mx-auto px-4">
				{#each Array(numberOfDays) as _, i}
					{@const startDate = new Date(collection.start_date)}
					{@const tempDate = new Date(startDate.getTime())}
					{@const adjustedDate = new Date(tempDate.setUTCDate(tempDate.getUTCDate() + i))}
					{@const dateString = adjustedDate.toISOString().split('T')[0]}

					{@const dayAdventures =
						groupAdventuresByDate(adventures, new Date(collection.start_date), numberOfDays)[
							dateString
						] || []}
					{@const dayTransportations =
						groupTransportationsByDate(
							transportations,
							new Date(collection.start_date),
							numberOfDays
						)[dateString] || []}
					{@const dayNotes =
						groupNotesByDate(notes, new Date(collection.start_date), numberOfDays)[dateString] ||
						[]}
					{@const dayChecklists =
						groupChecklistsByDate(checklists, new Date(collection.start_date), numberOfDays)[
							dateString
						] || []}

					<div class="card bg-base-100 shadow-xl my-8">
						<div class="card-body bg-base-200">
							<h2 class="card-title text-3xl justify-center g">
								{$t('adventures.day')}
								{i + 1}
								<div class="badge badge-lg">
									{adjustedDate.toLocaleDateString(undefined, { timeZone: 'UTC' })}
								</div>
							</h2>

							<div class="divider"></div>

							<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
								{#if dayAdventures.length > 0}
									{#each dayAdventures as adventure}
										<AdventureCard
											user={data.user}
											on:edit={editAdventure}
											on:delete={deleteAdventure}
											{adventure}
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
												isShowingTransportationModal = true;
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
							</div>

							{#if dayAdventures.length == 0 && dayTransportations.length == 0 && dayNotes.length == 0 && dayChecklists.length == 0}
								<p class="text-center text-lg mt-2 italic">{$t('adventures.nothing_planned')}</p>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}

	{#if currentView == 'map'}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">Trip Map</h2>
				<MapLibre
					style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
					class="aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max-h-full w-full rounded-lg"
					standardControls
				>
					{#each adventures as adventure}
						{#if adventure.longitude && adventure.latitude}
							<Marker lngLat={{ lng: adventure.longitude, lat: adventure.latitude }}>
								<span class="text-xl">
									{adventure.category?.icon}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{adventure.name}</div>
									<p class="font-semibold text-black text-md">
										{adventure.category?.display_name + ' ' + adventure.category?.icon}
									</p>
								</Popup>
							</Marker>
						{/if}
					{/each}
					{#each transportations as transportation}
						{#if transportation.destination_latitude && transportation.destination_longitude}
							<Marker
								lngLat={{
									lng: transportation.destination_longitude,
									lat: transportation.destination_latitude
								}}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 
								bg-red-300 text-black focus:outline-6 focus:outline-black"
							>
								<span class="text-xl">
									{getTransportationEmoji(transportation.type)}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{transportation.name}</div>
									<p class="font-semibold text-black text-md">
										{transportation.type}
									</p>
								</Popup>
							</Marker>
						{/if}
						{#if transportation.origin_latitude && transportation.origin_longitude}
							<Marker
								lngLat={{
									lng: transportation.origin_longitude,
									lat: transportation.origin_latitude
								}}
								class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 
								bg-green-300 text-black focus:outline-6 focus:outline-black"
							>
								<span class="text-xl">
									{getTransportationEmoji(transportation.type)}
								</span>
								<Popup openOn="click" offset={[0, -10]}>
									<div class="text-lg text-black font-bold">{transportation.name}</div>
									<p class="font-semibold text-black text-md">
										{transportation.type}
									</p>
								</Popup>
							</Marker>
						{/if}
					{/each}
				</MapLibre>
			</div>
		</div>
	{/if}
	{#if currentView == 'calendar'}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">
					{$t('adventures.adventure_calendar')}
				</h2>
				<Calendar {plugins} {options} />
			</div>
		</div>
	{/if}
	{#if currentView == 'recommendations'}
		<div class="card bg-base-200 shadow-xl my-8 mx-auto w-10/12">
			<div class="card-body">
				<h2 class="card-title text-3xl justify-center mb-4">Adventure Recommendations</h2>
				{#each adventures as adventure}
					{#if adventure.longitude && adventure.latitude}
						<button on:click={() => getRecomendations(adventure)} class="btn btn-neutral"
							>{adventure.name}</button
						>
					{/if}
				{/each}
				{#if adventures.length == 0}
					<div class="alert alert-info">
						<p class="text-center text-lg">{$t('adventures.no_adventures_to_recommendations')}</p>
					</div>
				{/if}
				<div class="mt-4">
					<input
						type="range"
						min="1600"
						max="80467"
						class="range"
						step="1600"
						bind:value={recomendationsRange}
					/>
					<div class="flex w-full justify-between px-2">
						<span class="text-lg"
							>{Math.round(recomendationsRange / 1600)} mile ({(
								(recomendationsRange / 1600) *
								1.6
							).toFixed(1)} km)</span
						>
					</div>
					<div class="join flex items-center justify-center mt-4">
						<input
							class="join-item btn"
							type="radio"
							name="options"
							aria-label="Tourism"
							checked={recomendationType == 'tourism'}
							on:click={() => (recomendationType = 'tourism')}
						/>
						<input
							class="join-item btn"
							type="radio"
							name="options"
							aria-label="Food"
							checked={recomendationType == 'food'}
							on:click={() => (recomendationType = 'food')}
						/>
						<input
							class="join-item btn"
							type="radio"
							name="options"
							aria-label="Lodging"
							checked={recomendationType == 'lodging'}
							on:click={() => (recomendationType = 'lodging')}
						/>
					</div>
					{#if recomendationTags.length > 0}
						<select
							class="select select-bordered w-full max-w-xs"
							bind:value={selectedRecomendationTag}
						>
							<option value="">All</option>
							{#each recomendationTags as tag}
								<option value={tag.name}>{tag.display_name}</option>
							{/each}
						</select>
					{/if}
				</div>

				{#if recomendationsData}
					<MapLibre
						style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
						class="aspect-[9/16] max-h-[70vh] sm:aspect-video sm:max
						-h-full w-full rounded-lg"
						standardControls
						center={{ lng: recomendationsData[0].longitude, lat: recomendationsData[0].latitude }}
						zoom={12}
					>
						{#each filteredRecomendations as recomendation}
							{#if recomendation.longitude && recomendation.latitude && recomendation.name}
								<Marker
									lngLat={[recomendation.longitude, recomendation.latitude]}
									class="grid h-8 w-8 place-items-center rounded-full border border-gray-200 bg-blue-300 text-black focus:outline-6 focus:outline-black"
									on:click={togglePopup}
								>
									<span class="text-xl">
										{osmTagToEmoji(recomendation.tag)}
									</span>
									{#if isPopupOpen}
										<Popup openOn="click" offset={[0, -10]} on:close={() => (isPopupOpen = false)}>
											<div class="text-lg text-black font-bold">{recomendation.name}</div>

											<p class="font-semibold text-black text-md">
												{`${recomendation.tag} ${osmTagToEmoji(recomendation.tag)}`}
											</p>

											<button
												class="btn btn-neutral btn-wide btn-sm mt-4"
												on:click={() =>
													window.open(
														`https://www.openstreetmap.org/node/${recomendation.id}`,
														'_blank'
													)}>{$t('map.view_details')}</button
											>
											<button
												class="btn btn-neutral btn-wide btn-sm mt-4"
												on:click={() => recomendationToAdventure(recomendation)}
												>{$t('adventures.create_adventure')}</button
											>
										</Popup>
									{/if}
								</Marker>
							{/if}
						{/each}
					</MapLibre>
					{#each filteredRecomendations as recomendation}
						{#if recomendation.name && recomendation.longitude && recomendation.latitude}
							<div class="card bg-base-100 shadow-xl my-4 w-full">
								<div class="card-body">
									<h2 class="card-title text-xl font-bold">
										{recomendation.name || $t('recomendations.recommendation')}
									</h2>
									<div class="badge badge-primary">{recomendation.tag}</div>
									{#if recomendation.address}
										<p class="text-md">
											<strong>{$t('recomendations.address')}:</strong>
											{recomendation.address.housenumber}
											{recomendation.address.street}, {recomendation.address.city}, {recomendation
												.address.state}
											{recomendation.address.postcode}
										</p>
									{/if}
									{#if recomendation.contact}
										<p class="text-md">
											<strong>{$t('recomendations.contact')}:</strong>
											{#if recomendation.contact.phone}
												{$t('recomendations.phone')}: {recomendation.contact.phone}
											{/if}
											{#if recomendation.contact.email}
												{$t('auth.email')}: {recomendation.contact.email}
											{/if}
											{#if recomendation.contact.website}
												{$t('recomendations.website')}:
												<a
													href={recomendation.contact.website}
													target="_blank"
													rel="noopener noreferrer">{recomendation.contact.website}</a
												>
											{/if}
										</p>
									{/if}
									<button
										class="btn btn-primary"
										on:click={() => recomendationToAdventure(recomendation)}
									>
										{$t('adventures.create_adventure')}
									</button>
								</div>
							</div>
						{/if}
					{/each}
				{/if}
				{#if loadingRecomendations}
					<div class="card bg-base-100 shadow-xl my-4 w-full">
						<div class="card-body">
							<div class="flex flex-col items-center justify-center">
								<span class="loading loading-ring loading-lg"></span>
								<div class="mt-2">
									<p class="text-center text-lg">
										{$t('adventures.finding_recommendations')}...
									</p>
								</div>
							</div>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}
{/if}

<svelte:head>
	<title
		>{data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}`
			: $t('adventures.collection')}</title
	>
	<meta
		name="description"
		content="Learn more about {data.props.adventure && data.props.adventure.name
			? `${data.props.adventure.name}.`
			: 'your adventures.'}"
	/>
</svelte:head>
