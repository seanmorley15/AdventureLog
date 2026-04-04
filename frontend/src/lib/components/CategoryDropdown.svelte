<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { t } from 'svelte-i18n';
	import type { Category } from '$lib/types';

	export let selected_category: Category | null = null;
	export let searchTerm = '';

	const emptyCategory: Category = {
		name: '',
		display_name: '',
		icon: '',
		id: '',
		user: '',
		num_locations: 0
	};

	let newCategory: Category = { ...emptyCategory };
	let categories: Category[] = [];
	let isOpen = false;
	let isEmojiPickerVisible = false;
	let dropdownRef: HTMLDivElement;
	let mobileSearchInputRef: HTMLInputElement;
	let desktopSearchInputRef: HTMLInputElement;

	$: sortedCategories = [...categories].sort(
		(a, b) => (b.num_locations || 0) - (a.num_locations || 0)
	);

	$: filteredCategories = sortedCategories.filter((category) => {
		if (!searchTerm) return true;
		return category.display_name.toLowerCase().includes(searchTerm.toLowerCase());
	});

	function closeDropdown() {
		isOpen = false;
		isEmojiPickerVisible = false;
	}

	async function openDropdown() {
		isOpen = true;
		await tick();
		(mobileSearchInputRef ?? desktopSearchInputRef)?.focus();
	}

	function toggleDropdown() {
		isOpen ? closeDropdown() : openDropdown();
	}

	function toggleEmojiPicker() {
		isEmojiPickerVisible = !isEmojiPickerVisible;
	}

	function selectCategory(category: Category) {
		selected_category = category;
		closeDropdown();
	}

	function createCustomCategory() {
		const displayName = newCategory.display_name.trim();
		if (!displayName) return;

		const generatedId =
			newCategory.id ||
			(typeof crypto !== 'undefined' && 'randomUUID' in crypto
				? crypto.randomUUID()
				: `custom-${Date.now()}`);

		const category: Category = {
			...newCategory,
			id: generatedId,
			name: displayName.toLowerCase().replace(/\s+/g, '_'),
			icon: newCategory.icon || '🌎'
		};

		categories = [category, ...categories];
		selectCategory(category);
		newCategory = { ...emptyCategory };
	}

	function handleEmojiSelect(event: CustomEvent) {
		newCategory.icon = event.detail.unicode;
	}

	onMount(() => {
		const loadData = async () => {
			try {
				await import('emoji-picker-element');
			} catch (error) {
				console.error('Emoji picker failed to load', error);
			}

			try {
				const res = await fetch('/api/categories');
				const data = await res.json();
				categories = Array.isArray(data) ? data : [];
			} catch (error) {
				console.error('Unable to load categories', error);
			}
		};

		loadData();

		const handleOutside = (event: Event) => {
			if (!dropdownRef) return;
			const target = event.target as Node | null;
			if (target && !dropdownRef.contains(target)) {
				closeDropdown();
			}
		};

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				closeDropdown();
			}
		};

		const outsideEvents: Array<keyof DocumentEventMap> = ['pointerdown', 'mousedown', 'touchstart'];
		outsideEvents.forEach((eventName) => document.addEventListener(eventName, handleOutside));
		document.addEventListener('keydown', handleKeyDown);

		return () => {
			outsideEvents.forEach((eventName) => document.removeEventListener(eventName, handleOutside));
			document.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<div class="dropdown w-full" class:dropdown-open={isOpen} bind:this={dropdownRef}>
	<button
		type="button"
		class="btn btn-outline w-full justify-between sm:h-auto h-12"
		aria-haspopup="listbox"
		aria-expanded={isOpen}
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
			class={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
			aria-hidden="true"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	{#if isOpen}
		<button
			type="button"
			class="fixed inset-0 bg-black/50 z-40 sm:hidden focus:outline-none"
			aria-label={$t('adventures.back')}
			on:click={closeDropdown}
			on:keydown={(event) => event.key === 'Enter' && closeDropdown()}
		></button>

		<div
			class="fixed bottom-0 left-0 right-0 z-50 bg-base-100 rounded-t-2xl shadow-2xl border-t border-base-300 max-h-[90vh] flex flex-col sm:hidden"
		>
			<div class="flex-shrink-0 bg-base-100 border-b border-base-300 p-4">
				<div class="flex items-center justify-between">
					<h2 class="text-lg font-semibold">{$t('categories.select_category')}</h2>
					<button
						type="button"
						class="btn btn-ghost btn-sm btn-circle"
						aria-label={$t('about.close')}
						title={$t('about.close')}
						on:click={closeDropdown}
					>
						<svg
							class="w-5 h-5"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
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
				<div class="p-4 border-b border-base-300 space-y-4">
					<div class="flex items-center gap-2 text-sm font-semibold text-base-content/80">
						<svg
							class="w-4 h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 6v6m0 0v6m0-6h6m-6 0H6"
							/>
						</svg>
						{$t('categories.add_new_category')}
					</div>

					<div class="space-y-3">
						<input
							type="text"
							placeholder={$t('categories.category_name')}
							class="input input-bordered w-full h-12 text-base"
							bind:value={newCategory.display_name}
						/>
						<div class="join w-full">
							<input
								type="text"
								placeholder={$t('categories.icon')}
								class="input input-bordered join-item flex-1 h-12 text-base"
								bind:value={newCategory.icon}
							/>
							<button
								type="button"
								class="btn join-item h-12 w-12 text-lg"
								on:click={toggleEmojiPicker}
								class:btn-active={isEmojiPickerVisible}
							>
								😊
							</button>
						</div>

						<button
							type="button"
							class="btn btn-primary h-12 w-full"
							on:click={createCustomCategory}
							disabled={!newCategory.display_name.trim()}
						>
							<svg
								class="w-4 h-4 mr-1"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
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

				<div class="p-4 space-y-4">
					<div class="flex items-center gap-2 text-sm font-semibold text-base-content/80">
						<svg
							class="w-4 h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
							/>
						</svg>
						{$t('categories.select_category')}
					</div>

					{#if categories.length > 0}
						<div class="form-control">
							<input
								type="text"
								placeholder={$t('navbar.search')}
								class="input input-bordered w-full h-12 text-base"
								bind:value={searchTerm}
								bind:this={mobileSearchInputRef}
							/>
						</div>

						<div class="space-y-2">
							{#each filteredCategories as category}
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
					{:else}
						<div class="text-center py-8 text-base-content/60">
							<svg
								class="w-12 h-12 mx-auto mb-2 opacity-50"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
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

				<div class="flex-shrink-0 h-4"></div>
			</div>
		</div>

		<div
			tabindex="-1"
			class="dropdown-content z-[1] w-full mt-1 bg-base-100 rounded-box shadow-xl border border-base-300 max-h-[28rem] overflow-y-auto hidden sm:block"
		>
			<div class="p-4 border-b border-base-300 space-y-3">
				<div class="flex items-center gap-2 text-sm font-semibold text-base-content/80">
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 6v6m0 0v6m0-6h6m-6 0H6"
						/>
					</svg>
					{$t('categories.add_new_category')}
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
					<input
						type="text"
						placeholder={$t('categories.category_name')}
						class="input input-bordered input-sm w-full"
						bind:value={newCategory.display_name}
					/>
					<div class="input-group">
						<input
							type="text"
							placeholder={$t('categories.icon')}
							class="input input-bordered input-sm flex-1"
							bind:value={newCategory.icon}
						/>
						<button
							type="button"
							class="btn btn-square btn-sm btn-secondary"
							on:click={toggleEmojiPicker}
							class:btn-active={isEmojiPickerVisible}
						>
							😊
						</button>
					</div>
				</div>

				<div class="flex justify-end">
					<button
						type="button"
						class="btn btn-primary btn-sm"
						on:click={createCustomCategory}
						disabled={!newCategory.display_name.trim()}
					>
						<svg
							class="w-4 h-4 mr-1"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
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

			<div class="p-4 space-y-3">
				<div class="flex items-center gap-2 text-sm font-semibold text-base-content/80">
					<svg
						class="w-4 h-4"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
						/>
					</svg>
					{$t('categories.select_category')}
				</div>

				{#if categories.length > 0}
					<input
						type="text"
						placeholder={$t('navbar.search')}
						class="input input-bordered input-sm w-full"
						bind:value={searchTerm}
						bind:this={desktopSearchInputRef}
					/>

					<div
						class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-60 overflow-y-auto"
						role="listbox"
					>
						{#each filteredCategories as category (category.id)}
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

					{#if filteredCategories.length === 0}
						<div class="text-center py-8 text-base-content/60">
							<svg
								class="w-12 h-12 mx-auto mb-2 opacity-50"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
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
							aria-hidden="true"
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
