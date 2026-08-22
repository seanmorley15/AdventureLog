<script lang="ts">
	import UserCard from '$lib/components/cards/UserCard.svelte';
	import type { User } from '$lib/types';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	import AccountGroup from '~icons/mdi/account-group';
	import FilterIcon from '~icons/mdi/filter-variant';
	import SearchIcon from '~icons/mdi/magnify';
	import ClearIcon from '~icons/mdi/close';
	import SortIcon from '~icons/mdi/sort';
	import ShieldAccount from '~icons/mdi/shield-account';

	export let data: PageData;

	let users: User[] = data.props.users;
	let searchQuery = '';
	let sortBy: 'name' | 'recent' = 'name';
	let filterStaff: 'all' | 'staff' = 'all';
	let sidebarOpen = false;

	$: filteredUsers = users
		.filter((user) => {
			if (filterStaff === 'staff' && !user.is_staff) return false;
			const q = searchQuery.trim().toLowerCase();
			if (!q) return true;
			const name = [user.first_name, user.last_name].filter(Boolean).join(' ').toLowerCase();
			return name.includes(q) || user.username.toLowerCase().includes(q);
		})
		.sort((a, b) => {
			if (sortBy === 'recent') {
				const aTime = a.date_joined ? new Date(a.date_joined).getTime() : 0;
				const bTime = b.date_joined ? new Date(b.date_joined).getTime() : 0;
				return bTime - aTime;
			}
			const aName = (a.first_name || a.username).toLowerCase();
			const bName = (b.first_name || b.username).toLowerCase();
			return aName.localeCompare(bName);
		});

	$: staffCount = users.filter((u) => u.is_staff).length;
	$: hasActiveFilters = searchQuery.trim().length > 0 || filterStaff !== 'all';

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function clearFilters() {
		searchQuery = '';
		filterStaff = 'all';
		sortBy = 'name';
	}
</script>

<svelte:head>
	<title>{$t('navbar.users')} - AdventureLog</title>
	<meta name="description" content={$t('users.page_description')} />
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-base-200 via-base-100 to-base-200">
	<div class="drawer lg:drawer-open">
		<input id="users-drawer" type="checkbox" class="drawer-toggle" bind:checked={sidebarOpen} />

		<div class="drawer-content">
			<!-- Header -->
			<div class="sticky top-0 z-30 bg-base-100/80 backdrop-blur-lg border-b border-base-300">
				<div class="container mx-auto px-6 py-4">
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-4 min-w-0">
							<button class="btn btn-ghost btn-square lg:hidden shrink-0" on:click={toggleSidebar}>
								<FilterIcon class="w-5 h-5" />
							</button>
							<div class="flex items-center gap-3 min-w-0">
								<div class="p-2 bg-primary/10 rounded-xl shrink-0">
									<AccountGroup class="w-8 h-8 text-primary" />
								</div>
								<div class="min-w-0">
									<h1 class="text-3xl font-bold text-primary bg-clip-text truncate">
										{$t('navbar.users')}
									</h1>
									<p class="text-sm text-base-content/60">
										{filteredUsers.length}
										{$t('worldtravel.of')}
										{users.length}
										{$t('users.public_profiles')} ·
										<span class="text-secondary">{staffCount} {$t('settings.admin')}</span>
									</p>
								</div>
							</div>
						</div>

						<div class="hidden md:flex items-center gap-2 shrink-0">
							<div class="stats stats-horizontal bg-base-200/50 border border-base-300/50">
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('users.public_profiles')}</div>
									<div class="stat-value text-lg text-primary">{users.length}</div>
								</div>
								<div class="stat py-2 px-4">
									<div class="stat-title text-xs">{$t('settings.admin')}</div>
									<div class="stat-value text-lg text-secondary">{staffCount}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Search -->
					<div class="mt-4 flex flex-wrap items-center gap-4">
						<div class="relative flex-1 max-w-md min-w-[12rem]">
							<SearchIcon
								class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-base-content/40"
							/>
							<input
								type="text"
								placeholder={$t('users.search_placeholder')}
								class="input input-bordered w-full pl-10 pr-10 bg-base-100/80"
								bind:value={searchQuery}
							/>
							{#if searchQuery.length > 0}
								<button
									type="button"
									class="absolute right-3 top-1/2 -translate-y-1/2 text-base-content/40 hover:text-base-content"
									on:click={() => (searchQuery = '')}
								>
									<ClearIcon class="w-4 h-4" />
								</button>
							{/if}
						</div>
					</div>

					<!-- Filter chips -->
					<div class="mt-4 flex flex-wrap items-center gap-2">
						<span class="text-sm font-medium text-base-content/60"
							>{$t('worldtravel.filter_by')}:</span
						>
						<div class="tabs tabs-boxed bg-base-200">
							<button
								type="button"
								class="tab tab-sm gap-1.5 {filterStaff === 'all' ? 'tab-active' : ''}"
								on:click={() => (filterStaff = 'all')}
							>
								<AccountGroup class="w-3.5 h-3.5" />
								{$t('adventures.all')}
							</button>
							<button
								type="button"
								class="tab tab-sm gap-1.5 {filterStaff === 'staff' ? 'tab-active' : ''}"
								on:click={() => (filterStaff = 'staff')}
							>
								<ShieldAccount class="w-3.5 h-3.5" />
								{$t('settings.admin')}
							</button>
						</div>
						{#if hasActiveFilters}
							<button type="button" class="btn btn-ghost btn-xs gap-1" on:click={clearFilters}>
								<ClearIcon class="w-3 h-3" />
								{$t('worldtravel.clear_all')}
							</button>
						{/if}
					</div>
				</div>
			</div>

			<!-- Main content -->
			<div class="container mx-auto px-6 py-8">
				{#if users.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<AccountGroup class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('users.no_users_found')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md">{$t('users.no_users_desc')}</p>
					</div>
				{:else if filteredUsers.length === 0}
					<div class="flex flex-col items-center justify-center py-16">
						<div class="p-6 bg-base-200/50 rounded-2xl mb-6">
							<SearchIcon class="w-16 h-16 text-base-content/30" />
						</div>
						<h3 class="text-xl font-semibold text-base-content/70 mb-2">
							{$t('users.no_match')}
						</h3>
						<p class="text-base-content/50 text-center max-w-md mb-4">
							{$t('users.no_match_desc')}
						</p>
						<button type="button" class="btn btn-ghost btn-sm gap-2" on:click={clearFilters}>
							<ClearIcon class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					</div>
				{:else}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
						{#each filteredUsers as user (user.uuid)}
							<UserCard {user} />
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Sidebar -->
		<div class="drawer-side z-40">
			<label for="users-drawer" class="drawer-overlay"></label>
			<div class="w-80 min-h-full bg-base-100 shadow-2xl">
				<div class="p-6">
					<div class="flex items-center gap-3 mb-8">
						<div class="p-2 bg-primary/10 rounded-lg">
							<SortIcon class="w-6 h-6 text-primary" />
						</div>
						<h2 class="text-xl font-bold">{$t('users.browse_options')}</h2>
					</div>

					<div class="card bg-base-200/50 p-4 mb-4">
						<h3 class="font-semibold text-lg mb-4 flex items-center gap-2">
							<SortIcon class="w-5 h-5" />
							{$t('adventures.sort')}
						</h3>
						<div class="join w-full">
							<button
								type="button"
								class="btn btn-sm join-item flex-1 {sortBy === 'name' ? 'btn-active' : ''}"
								on:click={() => (sortBy = 'name')}
							>
								{$t('users.sort_name')}
							</button>
							<button
								type="button"
								class="btn btn-sm join-item flex-1 {sortBy === 'recent' ? 'btn-active' : ''}"
								on:click={() => (sortBy = 'recent')}
							>
								{$t('users.sort_recent')}
							</button>
						</div>
					</div>

					<div class="card bg-base-200/50 p-4 mb-6">
						<h3 class="font-semibold text-lg mb-3 flex items-center gap-2">
							<AccountGroup class="w-5 h-5" />
							{$t('users.overview')}
						</h3>
						<div class="space-y-3 text-sm">
							<div class="flex justify-between">
								<span class="text-base-content/60">{$t('users.public_profiles')}</span>
								<span class="font-semibold">{users.length}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-base-content/60">{$t('calendar.filtered_results')}</span>
								<span class="font-semibold">{filteredUsers.length}</span>
							</div>
							<div class="flex justify-between">
								<span class="text-base-content/60">{$t('settings.admin')}</span>
								<span class="font-semibold">{staffCount}</span>
							</div>
						</div>
					</div>

					<p class="text-xs text-base-content/50 leading-relaxed">
						{$t('users.page_description')}
					</p>

					{#if hasActiveFilters}
						<button type="button" class="btn btn-ghost w-full gap-2 mt-6" on:click={clearFilters}>
							<ClearIcon class="w-4 h-4" />
							{$t('worldtravel.clear_filters')}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
