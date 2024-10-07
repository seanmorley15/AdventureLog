<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.props.adventures || [];

	let currentSort = {
		order_by: '',
		order: '',
		visited: true,
		planned: true,
		includeCollections: true
	};

	let resultsPerPage: number = 25;

	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	let typeString: string = '';

	$: {
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			url.searchParams.set('types', typeString);
			goto(url.toString(), { invalidateAll: true, replaceState: true });
		}
	}

	// sets typeString if present in the URL
	$: {
		// check to make sure its running on the client side
		if (typeof window !== 'undefined') {
			let url = new URL(window.location.href);
			let types = url.searchParams.get('types');
			if (types) {
				typeString = types;
			}
		}
	}

	function handleChangePage(pageNumber: number) {
		// let query = new URLSearchParams($page.url.searchParams.toString());

		// query.set('page', pageNumber.toString());

		// console.log(query.toString());
		currentPage = pageNumber;

		let url = new URL(window.location.href);
		url.searchParams.set('page', pageNumber.toString());
		adventures = [];
		adventures = data.props.adventures;

		goto(url.toString(), { invalidateAll: true, replaceState: true });

		// goto(`?${query.toString()}`, { invalidateAll: true });
	}

	$: {
		let url = new URL($page.url);
		let page = url.searchParams.get('page');
		if (page) {
			currentPage = parseInt(page);
		}
	}

	$: {
		if (data.props.adventures) {
			adventures = data.props.adventures;
		}
		if (data.props.count) {
			count = data.props.count;
			totalPages = Math.ceil(count / resultsPerPage);
		}
	}

	$: {
		let url = new URL($page.url);
		currentSort.order_by = url.searchParams.get('order_by') || 'updated_at';
		currentSort.order = url.searchParams.get('order_direction') || 'asc';

		if (url.searchParams.get('planned') === 'on') {
			currentSort.planned = true;
		} else {
			currentSort.planned = false;
		}
		if (url.searchParams.get('visited') === 'on') {
			currentSort.visited = true;
		} else {
			currentSort.visited = false;
		}
		if (url.searchParams.get('include_collections') === 'on') {
			currentSort.includeCollections = true;
		} else {
			currentSort.includeCollections = false;
		}

		if (!currentSort.visited && !currentSort.planned) {
			currentSort.visited = true;
			currentSort.planned = true;
		}
	}

	let adventureToEdit: Adventure | null = null;
	let isAdventureModalOpen: boolean = false;

	function deleteAdventure(event: CustomEvent<string>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
	}

	// function that save changes to an existing adventure or creates a new one if it doesn't exist
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

	function editAdventure(event: CustomEvent<Adventure>) {
		adventureToEdit = event.detail;
		isAdventureModalOpen = true;
	}

	let sidebarOpen = false;

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

{#if isAdventureModalOpen}
	<AdventureModal
		{adventureToEdit}
		on:close={() => (isAdventureModalOpen = false)}
		on:save={saveOrCreate}
	/>
{/if}

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
				<p class="text-center font-bold text-lg">Create new...</p>
				<button
					class="btn btn-primary"
					on:click={() => {
						isAdventureModalOpen = true;
						adventureToEdit = null;
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

<div class="drawer lg:drawer-open">
	<input id="my-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />
	<div class="drawer-content">
		<!-- Page content -->
		<h1 class="text-center font-bold text-4xl mb-6">My Adventures</h1>
		<p class="text-center">This search returned {count} results.</p>
		{#if adventures.length === 0}
			<NotFound error={undefined} />
		{/if}
		<div class="p-4">
			<button
				class="btn btn-primary drawer-button lg:hidden mb-4 fixed bottom-0 left-0 ml-2 z-[999]"
				on:click={toggleSidebar}
			>
				{sidebarOpen ? 'Close Filters' : 'Open Filters'}
			</button>

			<div class="flex flex-wrap gap-4 mr-4 justify-center content-center">
				{#each adventures as adventure}
					<AdventureCard
						user={data.user}
						type={adventure.type}
						{adventure}
						on:delete={deleteAdventure}
						on:edit={editAdventure}
					/>
				{/each}
			</div>

			<div class="join flex items-center justify-center mt-4">
				{#if totalPages > 1}
					<div class="join">
						{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
							{#if currentPage != page}
								<button class="join-item btn btn-lg" on:click={() => handleChangePage(page)}
									>{page}</button
								>
							{:else}
								<button class="join-item btn btn-lg btn-active">{page}</button>
							{/if}
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
	<div class="drawer-side">
		<label for="my-drawer" class="drawer-overlay"></label>

		<ul class="menu p-4 w-80 h-full bg-base-200 text-base-content rounded-lg">
			<!-- Sidebar content here -->
			<div class="form-control">
				<!-- <h3 class="text-center font-bold text-lg mb-4">Adventure Types</h3> -->
				<form method="get">
					<CategoryFilterDropdown bind:types={typeString} />
					<div class="divider"></div>
					<h3 class="text-center font-bold text-lg mb-4">Sort</h3>
					<p class="text-lg font-semibold mb-2">Order Direction</p>
					<div class="join">
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_direction"
							id="asc"
							value="asc"
							aria-label="Ascending"
							checked={currentSort.order === 'asc'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_direction"
							id="desc"
							value="desc"
							aria-label="Descending"
							checked={currentSort.order === 'desc'}
						/>
					</div>
					<br />
					<p class="text-lg font-semibold mt-2 mb-2">Order By</p>
					<div class="flex join overflow-auto">
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_by"
							id="updated_at"
							value="updated_at"
							aria-label="Updated"
							checked={currentSort.order_by === 'updated_at'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_by"
							id="name"
							aria-label="Name"
							value="name"
							checked={currentSort.order_by === 'name'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							value="date"
							name="order_by"
							id="date"
							aria-label="Date"
							checked={currentSort.order_by === 'date'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_by"
							id="rating"
							aria-label="Rating"
							value="rating"
							checked={currentSort.order_by === 'rating'}
						/>
					</div>

					<br />
					<p class="text-lg font-semibold mt-2 mb-2">Sources</p>
					<label class="label cursor-pointer">
						<span class="label-text">Include Collection Adventures</span>
						<input
							type="checkbox"
							name="include_collections"
							id="include_collections"
							class="checkbox checkbox-primary"
							checked={currentSort.includeCollections}
						/>
					</label>
					<button type="submit" class="btn btn-success mt-4">Filter</button>
				</form>
			</div>
		</ul>
	</div>
</div>

<svelte:head>
	<title>Adventures</title>
	<meta name="description" content="View your completed and planned adventures." />
</svelte:head>
