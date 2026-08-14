<script lang="ts">
	import { run } from 'svelte/legacy';

	import { createEventDispatcher } from 'svelte';
	import { CURRENCY_LABELS, CURRENCY_OPTIONS } from '$lib/money';
	import { t } from 'svelte-i18n';
	import { shouldFlipDropdownUp } from '$lib/utils/flipDropdown';

	type CurrencyOption = { code: string; label?: string };

	interface Props {
		value?: string | null;
		options?: string[];
		placeholder?: string;
		disabled?: boolean;
		id?: string;
		defaultCurrency?: string | null;
	}

	let {
		value = null,
		options = CURRENCY_OPTIONS,
		placeholder = '',
		disabled = false,
		id,
		defaultCurrency = null
	}: Props = $props();

	const dispatch = createEventDispatcher<{ change: string | null }>();

	let open = $state(false);
	let openUpward = $state(false);
	let search = $state('');
	let container: HTMLDivElement | null = $state(null);
	let normalizedOptions: CurrencyOption[] = $state([]);

	run(() => {
		normalizedOptions = options.map((code) => ({
			code,
			label: $t(`currencies.${code}`) || CURRENCY_LABELS[code]
		}));
	});

	let filteredOptions = $derived.by(() => {
		const term = search.trim().toLowerCase();
		const matches = normalizedOptions.filter((option) => {
			if (!term) return true;
			return (
				option.code.toLowerCase().includes(term) ||
				(option.label || '').toLowerCase().includes(term)
			);
		});

		if (!defaultCurrency) return matches;

		const defaultIndex = matches.findIndex((option) => option.code === defaultCurrency);
		if (defaultIndex <= 0) return matches;

		const next = [...matches];
		const [preferred] = next.splice(defaultIndex, 1);
		next.unshift(preferred);
		return next;
	});

	function closeDropdown() {
		open = false;
		search = '';
	}

	function openDropdown() {
		if (disabled) return;
		openUpward = shouldFlipDropdownUp(container);
		open = true;
	}

	function toggleDropdown() {
		open ? closeDropdown() : openDropdown();
	}

	function handleFocusOut(event: FocusEvent) {
		const nextTarget = event.relatedTarget as Node | null;
		if (nextTarget && container?.contains(nextTarget)) return;
		closeDropdown();
	}

	function selectCurrency(code: string | null) {
		dispatch('change', code);
		closeDropdown();
	}

	function handleButtonKeydown(event: KeyboardEvent) {
		if (['ArrowDown', 'Enter', ' '].includes(event.key)) {
			event.preventDefault();
			openDropdown();
		}
		if (event.key === 'Escape') closeDropdown();
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && filteredOptions.length) {
			event.preventDefault();
			selectCurrency(filteredOptions[0].code);
		}
		if (event.key === 'Escape') {
			event.preventDefault();
			closeDropdown();
		}
	}
</script>

<div
	class={`dropdown dropdown-end flex shrink-0 ${open ? 'dropdown-open' : ''}`}
	class:dropdown-top={openUpward}
	class:dropdown-bottom={!openUpward}
	bind:this={container}
	onfocusout={handleFocusOut}
>
	<button
		type="button"
		class="btn join-item h-full min-w-24 gap-1 bg-base-100 px-3 font-mono font-normal"
		aria-haspopup="listbox"
		aria-expanded={open}
		aria-controls={id ? `${id}-listbox` : undefined}
		aria-label={value
			? `${value} ${$t(`currencies.${value}`) || CURRENCY_LABELS[value] || ''}`
			: $t('currencies.select_currency') || placeholder}
		title={value ? $t(`currencies.${value}`) || CURRENCY_LABELS[value] : undefined}
		onclick={toggleDropdown}
		onkeydown={handleButtonKeydown}
		{disabled}
		{id}
	>
		<span class="font-mono text-sm truncate">{value || '—'}</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class={`h-4 w-4 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
			aria-hidden="true"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	<div
		tabindex="-1"
		class="dropdown-content z-50 w-80 max-w-[calc(100vw-2rem)] [--join-ss:var(--radius-field)] [--join-se:var(--radius-field)] [--join-es:var(--radius-field)] [--join-ee:var(--radius-field)]"
	>
		<div class="card rounded-box border border-base-300 bg-base-100 shadow-xl">
			<div class="space-y-3 p-3">
				{#if defaultCurrency}
					<p class="text-xs text-base-content/70">
						{$t('currencies.default') || 'Default'}
						<span class="font-mono font-semibold text-base-content">{defaultCurrency}</span>
					</p>
				{/if}

				<label class="input input-sm w-full rounded-full">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="h-4 w-4 text-base-content/70"
						fill="none"
						viewBox="0 0 24 24"
						stroke="currentColor"
						stroke-width="2"
						aria-hidden="true"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
					<input
						class="grow"
						type="search"
						placeholder={$t('currencies.search') || 'Search currency'}
						bind:value={search}
						onkeydown={handleSearchKeydown}
						aria-label={$t('currencies.search') || 'Search currency'}
					/>
				</label>

				{#if filteredOptions.length}
					<ul
						class="w-full max-h-64 space-y-1 overflow-y-auto"
						role="listbox"
						id={id ? `${id}-listbox` : undefined}
					>
						{#each filteredOptions as option (option.code)}
							<li>
								<button
									type="button"
									class={[
										'flex w-full flex-col items-start gap-1 rounded-lg px-3 py-2 text-left transition-colors',
										value === option.code
											? 'bg-primary/10 font-semibold text-primary'
											: 'hover:bg-base-200/80'
									]}
									onclick={() => selectCurrency(option.code)}
									role="option"
									aria-selected={value === option.code}
								>
									<span class="flex items-center gap-2">
										<span class="font-mono text-sm">{option.code}</span>
										{#if option.code === defaultCurrency}
											<span class="badge badge-ghost badge-xs font-normal"
												>{$t('currencies.default') || 'Default'}</span
											>
										{/if}
									</span>
									{#if option.label}
										<span class="w-full text-xs font-normal text-base-content/70">{option.label}</span>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<div class="px-3 py-2 text-sm text-base-content/70">
						{$t('currencies.no_matches') || 'No matches'}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
