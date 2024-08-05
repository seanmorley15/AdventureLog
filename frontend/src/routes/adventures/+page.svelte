<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import EditAdventure from '$lib/components/EditAdventure.svelte';
	import NewAdventure from '$lib/components/NewAdventure.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.props.adventures || [];

	let currentSort = { attribute: 'name', order: 'asc' };

	let isShowingCreateModal: boolean = false;
	let newType: string = '';

	let resultsPerPage: number = 25;

	// let next: string | null = data.props.next || null;
	// let previous: string | null = data.props.previous || null;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	function handleChangePage(pageNumber: number) {
		// let query = new URLSearchParams($page.url.searchParams.toString());

		// query.set('page', pageNumber.toString());

		// console.log(query.toString());
		currentPage = pageNumber;

		let url = new URL(window.location.href);
		url.searchParams.set('page', pageNumber.toString());
		adventures = [];
		adventures = data.props.adventures;
		console.log(adventures);
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

	function sort({ attribute, order }: { attribute: string; order: string }) {
		currentSort.attribute = attribute;
		currentSort.order = order;
		if (attribute === 'name') {
			if (order === 'asc') {
				adventures = adventures.sort((a, b) => b.name.localeCompare(a.name));
			} else {
				adventures = adventures.sort((a, b) => a.name.localeCompare(b.name));
			}
		}
	}

	let adventureToEdit: Adventure;
	let isEditModalOpen: boolean = false;

	function deleteAdventure(event: CustomEvent<number>) {
		adventures = adventures.filter((adventure) => adventure.id !== event.detail);
	}

	function createAdventure(event: CustomEvent<Adventure>) {
		adventures = [event.detail, ...adventures];
		isShowingCreateModal = false;
	}

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

	let sidebarOpen = false;

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}
</script>

{#if isShowingCreateModal}
	<NewAdventure
		type={newType}
		on:create={createAdventure}
		on:close={() => (isShowingCreateModal = false)}
	/>
{/if}

{#if isEditModalOpen}
	<EditAdventure
		{adventureToEdit}
		on:close={() => (isEditModalOpen = false)}
		on:saveEdit={saveEdit}
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
				<h3 class="text-center font-bold text-lg mb-4">Adventure Types</h3>
				<form method="get">
					<label class="label cursor-pointer">
						<span class="label-text">Completed</span>
						<input
							type="checkbox"
							name="visited"
							id="visited"
							class="checkbox checkbox-primary"
							checked
						/>
					</label>
					<label class="label cursor-pointer">
						<span class="label-text">Planned</span>
						<input
							type="checkbox"
							id="planned"
							name="planned"
							class="checkbox checkbox-primary"
							checked
						/>
					</label>
					<!-- <div class="divider"></div> -->
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
							checked
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_direction"
							id="desc"
							value="desc"
							aria-label="Descending"
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
							checked
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_by"
							id="name"
							aria-label="Name"
							value="name"
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							value="date"
							name="order_by"
							id="date"
							aria-label="Date"
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_by"
							id="rating"
							aria-label="Rating"
							value="rating"
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
						/>
					</label>
					<button type="submit" class="btn btn-success mt-4">Filter</button>
				</form>
			</div>
		</ul>
	</div>
</div>
