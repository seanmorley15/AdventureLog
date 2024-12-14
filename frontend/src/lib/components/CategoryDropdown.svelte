<script lang="ts">
	import { onMount } from 'svelte';
	import type { Category } from '$lib/types';
	import { t } from 'svelte-i18n';

	export let categories: Category[] = [];
	export let selected_category: Category | null = null;
	let new_category: Category = {
		name: '',
		display_name: '',
		icon: '',
		id: '',
		user_id: '',
		num_adventures: 0
	};

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
		selectCategory(new_category);
	}

	function handleEmojiSelect(event: CustomEvent) {
		new_category.icon = event.detail.unicode;
	}

	// Close dropdown when clicking outside
	let dropdownRef: HTMLDivElement;

	onMount(() => {
		categories = categories.sort((a, b) => (b.num_adventures || 0) - (a.num_adventures || 0));
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
	onMount(async () => {
		await import('emoji-picker-element');
	});
</script>

<div class="mt-2 relative" bind:this={dropdownRef}>
	<button type="button" class="btn btn-outline w-full text-left" on:click={toggleDropdown}>
		{selected_category && selected_category.name
			? selected_category.display_name + ' ' + selected_category.icon
			: $t('categories.select_category')}
	</button>

	{#if isOpen}
		<div class="absolute z-10 w-full mt-1 bg-base-300 rounded shadow-lg p-2">
			<!-- svelte-ignore a11y-click-events-have-key-events -->
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<input
						type="text"
						placeholder={$t('categories.category_name')}
						class="input input-bordered w-full max-w-xs"
						bind:value={new_category.display_name}
					/>
					<input
						type="text"
						placeholder={$t('categories.icon')}
						class="input input-bordered w-full max-w-xs"
						bind:value={new_category.icon}
					/>
					<button on:click={toggleEmojiPicker} type="button" class="btn btn-secondary">
						{isEmojiPickerVisible ? 'Hide' : 'Show'} Emoji Picker
					</button>
					<button on:click={custom_category} type="button" class="btn btn-primary">
						{$t('adventures.add')}
					</button>
				</div>

				{#if isEmojiPickerVisible}
					<div class="mt-2">
						<emoji-picker on:emoji-click={handleEmojiSelect}></emoji-picker>
					</div>
				{/if}
			</div>

			<div class="flex flex-wrap gap-2 mt-2">
				<!-- Sort the categories dynamically before rendering -->
				{#each categories
					.slice()
					.sort((a, b) => (b.num_adventures || 0) - (a.num_adventures || 0)) as category}
					<button
						type="button"
						class="btn btn-neutral flex items-center space-x-2"
						on:click={() => selectCategory(category)}
						role="option"
						aria-selected={selected_category && selected_category.id === category.id}
					>
						<span>{category.display_name} {category.icon} ({category.num_adventures})</span>
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>
