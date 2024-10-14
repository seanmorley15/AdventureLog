<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import CollectionCard from '$lib/components/CollectionCard.svelte';
	import EditCollection from '$lib/components/EditCollection.svelte';
	import NewCollection from '$lib/components/NewCollection.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Collection } from '$lib/types';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let collections: Collection[] = data.props.adventures || [];

	let currentSort = { attribute: 'name', order: 'asc' };

	let isShowingCreateModal: boolean = false;
	let newType: string = '';

	let resultsPerPage: number = 25;

	let next: string | null = data.props.next || null;
	let previous: string | null = data.props.previous || null;
	let count = data.props.count || 0;
	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	function handleChangePage() {
		return async ({ result }: any) => {
			if (result.type === 'success') {
				console.log(result.data);
				collections = result.data.body.adventures as Collection[];
				next = result.data.body.next;
				previous = result.data.body.previous;
				count = result.data.body.count;
				currentPage = result.data.body.page;
				totalPages = Math.ceil(count / resultsPerPage);
			}
		};
	}

	function handleSubmit() {
		return async ({ result, update }: any) => {
			// First, call the update function with reset: false
			update({ reset: false });

			// Then, handle the result
			if (result.type === 'success') {
				if (result.data) {
					// console.log(result.data);
					collections = result.data.adventures as Collection[];
					next = result.data.next;
					previous = result.data.previous;
					count = result.data.count;
					totalPages = Math.ceil(count / resultsPerPage);
					currentPage = 1;

					console.log(next);
				}
			}
		};
	}

	function deleteCollection(event: CustomEvent<string>) {
		collections = collections.filter((collection) => collection.id !== event.detail);
	}

	function sort({ attribute, order }: { attribute: string; order: string }) {
		currentSort.attribute = attribute;
		currentSort.order = order;
		if (attribute === 'name') {
			if (order === 'asc') {
				collections = collections.sort((a, b) => b.name.localeCompare(a.name));
			} else {
				collections = collections.sort((a, b) => a.name.localeCompare(b.name));
			}
		}
	}

	let collectionToEdit: Collection;
	let isEditModalOpen: boolean = false;

	function deleteAdventure(event: CustomEvent<string>) {
		collections = collections.filter((adventure) => adventure.id !== event.detail);
	}

	function createAdventure(event: CustomEvent<Collection>) {
		collections = [event.detail, ...collections];
		isShowingCreateModal = false;
	}

	function editCollection(event: CustomEvent<Collection>) {
		collectionToEdit = event.detail;
		isEditModalOpen = true;
	}

	function saveEdit(event: CustomEvent<Collection>) {
		collections = collections.map((adventure) => {
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
	<NewCollection on:create={createAdventure} on:close={() => (isShowingCreateModal = false)} />
{/if}

{#if isEditModalOpen}
	<EditCollection
		{collectionToEdit}
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
					Collection</button
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
		<h1 class="text-center font-bold text-4xl mb-6">My Collections</h1>
		<p class="text-center">This search returned {count} results.</p>
		{#if collections.length === 0}
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
				{#each collections as collection}
					<CollectionCard
						type=""
						{collection}
						on:delete={deleteCollection}
						on:edit={editCollection}
						adventures={collection.adventures}
					/>
				{/each}
			</div>

			<div class="join flex items-center justify-center mt-4">
				{#if next || previous}
					<div class="join">
						{#each Array.from({ length: totalPages }, (_, i) => i + 1) as page}
							<form action="?/changePage" method="POST" use:enhance={handleChangePage}>
								<input type="hidden" name="page" value={page} />
								<input type="hidden" name="next" value={next} />
								<input type="hidden" name="previous" value={previous} />
								{#if currentPage != page}
									<button class="join-item btn btn-lg">{page}</button>
								{:else}
									<button class="join-item btn btn-lg btn-active">{page}</button>
								{/if}
							</form>
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
				<form action="?/get" method="post" use:enhance={handleSubmit}>
					<h3 class="text-center font-semibold text-lg mb-4">Sort</h3>
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

					<input
						type="radio"
						name="order_by"
						id="name"
						class="radio radio-primary"
						checked
						value="name"
						hidden
					/>
					<button type="submit" class="btn btn-success btn-primary mt-4">Sort</button>
				</form>
				<div class="divider"></div>
				<button
					type="submit"
					class="btn btn-neutral btn-primary mt-4"
					on:click={() => goto('/collections/archived')}>Archived Collections</button
				>
			</div>
		</ul>
	</div>
</div>

<svelte:head>
	<title>Collections</title>
	<meta name="description" content="View your adventure collections." />
</svelte:head>
