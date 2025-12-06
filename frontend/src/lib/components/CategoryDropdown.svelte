<script lang="ts">
	import { onMount } from 'svelte';
	import type { Category } from '$lib/types';
	import { t } from 'svelte-i18n';

	export let selected_category: Category | null = null;
	export let searchTerm: string = '';
	let new_category: Category = {
		name: '',
		display_name: '',
		icon: '',
		id: '',
		user: '',
		num_locations: 0
	};

	$: {
		console.log('Selected category changed:', selected_category);
	}

	let categories: Category[] = [];

	let isOpen: boolean = false;
	let isEmojiPickerVisible: boolean = false;

	function toggleEmojiPicker() {
		isEmojiPickerVisible = !isEmojiPickerVisible;
	}

	function toggleDropdown() {
		isOpen = !isOpen;
	}

	function selectCategory(category: Category) {
		console.log('category', category);
		selected_category = category;
		isOpen = false;
	}

	function custom_category() {
		new_category.name = new_category.display_name.toLowerCase().replace(/ /g, '_');
		if (!new_category.icon) {
			new_category.icon = '🌎'; // Default icon if none selected
		}
		selectCategory(new_category);
	}

	function handleEmojiSelect(event: CustomEvent) {
		new_category.icon = event.detail.unicode;
	}

	// Close dropdown when clicking outside
	let dropdownRef: HTMLDivElement;

	onMount(() => {
		const loadData = async () => {
			await import('emoji-picker-element');
			let res = await fetch('/api/categories');
			categories = await res.json();
			categories = categories.sort((a, b) => (b.num_locations || 0) - (a.num_locations || 0));
		};

		loadData();

		const handleClickOutside = (event: MouseEvent) => {
			if (dropdownRef && !dropdownRef.contains(event.target as Node)) {
				isOpen = false;
			}
		};
		document.addEventListener('click', handleClickOutside);
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="dropdown w-full" bind:this={dropdownRef}>
	<!-- Main dropdown trigger -->
	<div
		tabindex="0"
		role="button"
		class="btn btn-outline w-full justify-between sm:h-auto h-12"
		on:click={toggleDropdown}
	>
		<span class="flex items-center gap-2">
			{#if selected_category && selected_category.name}
				<span class="text-lg">{selected_category.icon}</span>
				<span class="truncate">{selected_category.display_name}</span>
			{:else}
				<span class="text-base-content/70">{$t('categories.select_category')}</span>
			{/if}
		</span>
		<svg
			class="w-4 h-4 transition-transform duration-200 {isOpen ? 'rotate-180' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</div>

	{#if isOpen}
		<!-- Mobile Modal Overlay (only on small screens) -->
		<div class="fixed inset-0 bg-black/50 z-40 sm:hidden" on:click={() => (isOpen = false)}></div>

		<!-- Mobile Bottom Sheet -->
		<div
			class="fixed bottom-0 left-0 right-0 z-50 bg-base-100 rounded-t-2xl shadow-2xl border-t border-base-300 max-h-[90vh] flex flex-col sm:hidden"
		>
			<!-- Mobile Header -->
			<div class="flex-shrink-0 bg-base-100 border-b border-base-300 p-4">
				<div class="flex items-center justify-between">
					<h2 class="text-lg font-semibold">{$t('categories.select_category')}</h2>
					<button class="btn btn-ghost btn-sm btn-circle" on:click={() => (isOpen = false)}>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto min-h-0">
				<!-- Mobile Category Creator Section -->
				<div class="p-4 border-b border-base-300">
					<h3 class="font-semibold text-sm text-base-content/80 mb-3 flex items-center gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						{$t('categories.add_new_category')}
					</h3>

					<div class="space-y-3">
						<div class="space-y-2">
							<input
								type="text"
								placeholder={$t('categories.category_name')}
								class="input input-bordered w-full h-12 text-base"
								bind:value={new_category.display_name}
							/>
							<div class="join w-full">
								<input
									type="text"
									placeholder={$t('categories.icon')}
									class="input input-bordered join-item flex-1 h-12 text-base"
									bind:value={new_category.icon}
								/>
								<button
									on:click={toggleEmojiPicker}
									type="button"
									class="btn join-item h-12 w-12 text-lg"
									class:btn-active={isEmojiPickerVisible}
								>
									😊
								</button>
							</div>
						</div>

						<button
							on:click={custom_category}
							type="button"
							class="btn btn-primary h-12 w-full"
							disabled={!new_category.display_name.trim()}
						>
							<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 6v6m0 0v6m0-6h6m-6 0H6"
								/>
							</svg>
							{$t('adventures.add')}
						</button>

						{#if isEmojiPickerVisible}
							<div class="p-3 rounded-lg border border-base-300 bg-base-50">
								<emoji-picker on:emoji-click={handleEmojiSelect}></emoji-picker>
							</div>
						{/if}
					</div>
				</div>

				<!-- Mobile Categories List -->
				<div class="p-4">
					<h3 class="font-semibold text-sm text-base-content/80 mb-3">
						{$t('categories.select_category')}
					</h3>

					{#if categories.length > 0}
						<div class="form-control mb-4">
							<input
								type="text"
								placeholder={$t('navbar.search')}
								class="input input-bordered w-full h-12 text-base"
								bind:value={searchTerm}
							/>
						</div>

						<div class="space-y-2">
							{#each categories
								.slice()
								.sort((a, b) => (b.num_locations || 0) - (a.num_locations || 0))
								.filter((category) => !searchTerm || category.display_name
											.toLowerCase()
											.includes(searchTerm.toLowerCase())) as category}
								<button
									type="button"
									class="w-full text-left p-4 rounded-lg border border-base-300 hover:border-primary hover:bg-primary/5 transition-colors"
									class:bg-primary={selected_category && selected_category.id === category.id}
									class:text-primary-content={selected_category &&
										selected_category.id === category.id}
									class:border-primary={selected_category && selected_category.id === category.id}
									on:click={() => selectCategory(category)}
								>
									<div class="flex items-center gap-3 w-full">
										<span class="text-2xl flex-shrink-0">{category.icon}</span>
										<div class="flex-1 min-w-0">
											<div class="font-medium text-base truncate">{category.display_name}</div>
											<div class="text-sm opacity-70 mt-1">
												{category.num_locations}
												{$t('locations.locations')}
											</div>
										</div>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			</div>

			<!-- Bottom safe area -->
			<div class="flex-shrink-0 h-4"></div>
		</div>

		<!-- Desktop Dropdown -->
		<div
			class="dropdown-content z-[1] w-full mt-1 bg-base-300 rounded-box shadow-xl border border-base-300 max-h-96 overflow-y-auto hidden sm:block"
		>
			<!-- Desktop Category Creator Section -->
			<div class="p-4 border-b border-base-300">
				<h3 class="font-semibold text-sm text-base-content/80 mb-3 flex items-center gap-2">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 6v6m0 0v6m0-6h6m-6 0H6"
						/>
					</svg>
					{$t('categories.add_new_category')}
				</h3>

				<div class="space-y-3">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
						<div class="form-control">
							<input
								type="text"
								placeholder={$t('categories.category_name')}
								class="input input-bordered input-sm w-full"
								bind:value={new_category.display_name}
							/>
						</div>
						<div class="form-control">
							<div class="input-group">
								<input
									type="text"
									placeholder={$t('categories.icon')}
									class="input input-bordered input-sm flex-1"
									bind:value={new_category.icon}
								/>
								<button
									on:click={toggleEmojiPicker}
									type="button"
									class="btn btn-square btn-sm btn-secondary"
									class:btn-active={isEmojiPickerVisible}
								>
									😊
								</button>
							</div>
						</div>
					</div>

					<div class="flex justify-end">
						<button
							on:click={custom_category}
							type="button"
							class="btn btn-primary btn-sm"
							disabled={!new_category.display_name.trim()}
						>
							<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 6v6m0 0v6m0-6h6m-6 0H6"
								/>
							</svg>
							{$t('adventures.add')}
						</button>
					</div>

					{#if isEmojiPickerVisible}
						<div class="p-3 rounded-lg border border-base-300">
							<emoji-picker on:emoji-click={handleEmojiSelect}></emoji-picker>
						</div>
					{/if}
				</div>
			</div>

			<!-- Desktop Categories List Section -->
			<div class="p-4">
				<h3 class="font-semibold text-sm text-base-content/80 mb-3 flex items-center gap-2">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
						/>
					</svg>
					{$t('categories.select_category')}
				</h3>

				{#if categories.length > 0}
					<div class="form-control mb-3">
						<input
							type="text"
							placeholder={$t('navbar.search')}
							class="input input-bordered input-sm w-full"
							bind:value={searchTerm}
						/>
					</div>

					<div
						class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-60 overflow-y-auto"
					>
						{#each categories
							.slice()
							.sort((a, b) => (b.num_locations || 0) - (a.num_locations || 0))
							.filter((category) => !searchTerm || category.display_name
										.toLowerCase()
										.includes(searchTerm.toLowerCase())) as category}
							<button
								type="button"
								class="btn btn-ghost btn-sm justify-start h-auto py-2 px-3"
								class:btn-active={selected_category && selected_category.id === category.id}
								on:click={() => selectCategory(category)}
								role="option"
								aria-selected={selected_category && selected_category.id === category.id}
							>
								<div class="flex items-center gap-2 w-full">
									<span class="text-lg shrink-0">{category.icon}</span>
									<div class="flex-1 text-left">
										<div class="font-medium text-sm truncate">{category.display_name}</div>
										<div class="text-xs text-base-content/60">
											{category.num_locations}
											{$t('locations.locations')}
										</div>
									</div>
								</div>
							</button>
						{/each}
					</div>

					{#if categories.filter((category) => !searchTerm || category.display_name
								.toLowerCase()
								.includes(searchTerm.toLowerCase())).length === 0}
						<div class="text-center py-8 text-base-content/60">
							<svg
								class="w-12 h-12 mx-auto mb-2 opacity-50"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								/>
							</svg>
							<p class="text-sm">{$t('categories.no_categories_found')}</p>
						</div>
					{/if}
				{:else}
					<div class="text-center py-8 text-base-content/60">
						<svg
							class="w-12 h-12 mx-auto mb-2 opacity-50"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z"
							/>
						</svg>
						<p class="text-sm">{$t('categories.no_categories_yet')}</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
