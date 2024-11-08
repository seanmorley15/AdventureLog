<script lang="ts">
	import { enhance, deserialize } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AdventureCard from '$lib/components/AdventureCard.svelte';
	import AdventureModal from '$lib/components/AdventureModal.svelte';
	import CategoryFilterDropdown from '$lib/components/CategoryFilterDropdown.svelte';
	import NotFound from '$lib/components/NotFound.svelte';
	import type { Adventure } from '$lib/types';
	import { t } from 'svelte-i18n';

	import Plus from '~icons/mdi/plus';

	export let data: any;
	console.log(data);

	let adventures: Adventure[] = data.props.adventures || [];

	let currentSort = {
		order_by: '',
		order: '',
		visited: true,
		planned: true,
		includeCollections: true,
		is_visited: 'all'
	};

	let resultsPerPage: number = 25;

	let count = data.props.count || 0;

	let totalPages = Math.ceil(count / resultsPerPage);
	let currentPage: number = 1;

	let typeString: string = '';

	$: {
		if (typeof window !== 'undefined' && typeString) {
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

		if (url.searchParams.get('is_visited')) {
			currentSort.is_visited = url.searchParams.get('is_visited') || 'all';
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
				<p class="text-center font-bold text-lg">{$t('adventures.create_new')}</p>
				<button
					class="btn btn-primary"
					on:click={() => {
						isAdventureModalOpen = true;
						adventureToEdit = null;
					}}
				>
					{$t('adventures.adventure')}</button
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
		<h1 class="text-center font-bold text-4xl mb-6">{$t('navbar.my_adventures')}</h1>
		<p class="text-center">{count} {$t('adventures.count_txt')}</p>
		{#if adventures.length === 0}
			<NotFound error={undefined} />
		{/if}
		<div class="p-4">
			<button
				class="btn btn-primary drawer-button lg:hidden mb-4 fixed bottom-0 left-0 ml-2 z-[999]"
				on:click={toggleSidebar}
			>
				{sidebarOpen ? $t(`adventures.close_filters`) : $t(`adventures.open_filters`)}
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
					<h3 class="text-center font-bold text-lg mb-4">{$t('adventures.sort')}</h3>
					<p class="text-lg font-semibold mb-2">{$t('adventures.order_direction')}</p>
					<div class="join">
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_direction"
							id="asc"
							value="asc"
							aria-label={$t('adventures.ascending')}
							checked={currentSort.order === 'asc'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="order_direction"
							id="desc"
							value="desc"
							aria-label={$t('adventures.descending')}
							checked={currentSort.order === 'desc'}
						/>
					</div>
					<br />
					<p class="text-lg font-semibold mt-2 mb-2">{$t('adventures.order_by')}</p>
					<div class="flex flex-wrap gap-2">
						<input
							class="btn btn-neutral text-wrap"
							type="radio"
							name="order_by"
							id="updated_at"
							value="updated_at"
							aria-label={$t('adventures.updated')}
							checked={currentSort.order_by === 'updated_at'}
						/>
						<input
							class="btn btn-neutral text-wrap"
							type="radio"
							name="order_by"
							id="name"
							aria-label={$t('adventures.name')}
							value="name"
							checked={currentSort.order_by === 'name'}
						/>
						<input
							class="btn btn-neutral text-wrap"
							type="radio"
							value="date"
							name="order_by"
							id="date"
							aria-label={$t('adventures.date')}
							checked={currentSort.order_by === 'date'}
						/>
						<input
							class="btn btn-neutral text-wrap"
							type="radio"
							name="order_by"
							id="rating"
							aria-label={$t('adventures.rating')}
							value="rating"
							checked={currentSort.order_by === 'rating'}
						/>
					</div>

					<!-- is visited true false or all -->
					<p class="text-lg font-semibold mt-2 mb-2">{$t('adventures.visited')}</p>
					<div class="join">
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="is_visited"
							id="all"
							value="all"
							aria-label={$t('adventures.all')}
							checked={currentSort.is_visited === 'all'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="is_visited"
							id="true"
							value="true"
							aria-label={$t('adventures.visited')}
							checked={currentSort.is_visited === 'true'}
						/>
						<input
							class="join-item btn btn-neutral"
							type="radio"
							name="is_visited"
							id="false"
							value="false"
							aria-label={$t('adventures.not_visited')}
							checked={currentSort.is_visited === 'false'}
						/>
					</div>
					<div class="divider"></div>
					<div class="form-control">
						<br />
						<p class="text-lg font-semibold mt-2 mb-2">{$t('adventures.sources')}</p>
						<label class="label cursor-pointer">
							<span class="label-text">{$t('adventures.collection_adventures')}</span>
							<input
								type="checkbox"
								name="include_collections"
								id="include_collections"
								class="checkbox checkbox-primary"
								checked={currentSort.includeCollections}
							/>
						</label>
						<button type="submit" class="btn btn-success mt-4">{$t('adventures.filter')}</button>
					</div>
				</form>
			</div>
		</ul>
	</div>
</div>

<svelte:head>
	<title>{$t('navbar.adventures')}</title>
	<meta name="description" content="View your completed and planned adventures." />
</svelte:head>
