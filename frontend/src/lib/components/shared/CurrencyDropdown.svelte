<script lang="ts">
	import { tick, onMount } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	import { CURRENCY_LABELS, CURRENCY_OPTIONS } from '$lib/money';
	import { availableCurrencies, fetchExchangeRates, ratesLoaded } from '$lib/stores/exchangeRates';
	import { t } from 'svelte-i18n';

	type CurrencyOption = { code: string; label?: string };

	type Props = {
		value?: string | null;
		options?: string[];
		priorityCurrencies?: string[];
		placeholder?: string;
		disabled?: boolean;
		id?: string;
	};

	export let value: Props['value'] = null;
	export let options: string[] | undefined = undefined; // If provided, use these; otherwise use API
	export let priorityCurrencies: string[] = []; // Currencies to show first in dropdown
	export let placeholder = '';
	export let disabled = false;
	export let id: string | undefined;
	export let compact = false;

	const dispatch = createEventDispatcher<{ change: string | null }>();

	let open = false;
	let search = '';
	let container: HTMLDivElement | null = null;
	let searchInput: HTMLInputElement | null = null;
	let normalizedOptions: CurrencyOption[] = [];

	// Fetch exchange rates on mount to populate currency list
	onMount(() => {
		fetchExchangeRates();
	});

	// Use provided options, or API currencies, or fallback to hardcoded list
	$: baseOptions = options ?? ($ratesLoaded && $availableCurrencies.length > 0 ? $availableCurrencies : CURRENCY_OPTIONS);

	// Reorder options to put priority currencies first
	$: effectiveOptions = (() => {
		if (priorityCurrencies.length === 0) return baseOptions;
		const prioritySet = new Set(priorityCurrencies);
		const priority = priorityCurrencies.filter((c) => baseOptions.includes(c));
		const rest = baseOptions.filter((c) => !prioritySet.has(c));
		return [...priority, ...rest];
	})();

	$: normalizedOptions = effectiveOptions.map((code) => ({
		code,
		label: $t(`currencies.${code}`) || CURRENCY_LABELS[code] || code
	}));

	$: filteredOptions = normalizedOptions.filter((option) => {
		if (!search.trim()) return true;
		const term = search.trim().toLowerCase();
		return (
			option.code.toLowerCase().includes(term) || (option.label || '').toLowerCase().includes(term)
		);
	});

	function closeDropdown() {
		open = false;
		search = '';
	}

	async function openDropdown() {
		if (disabled) return;
		open = true;
		await tick();
		searchInput?.focus();
	}

	function toggleDropdown() {
		open ? closeDropdown() : void openDropdown();
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
	class={`dropdown dropdown-bottom ${compact ? 'w-auto' : 'w-full'} ${open ? 'dropdown-open' : ''}`}
	bind:this={container}
	on:focusout={handleFocusOut}
>
	<button
		type="button"
		class="input input-bordered {compact ? 'input-sm w-auto min-w-[80px]' : 'w-full'} justify-between gap-2 bg-base-100/80 focus:bg-base-100 flex items-center"
		aria-haspopup="listbox"
		aria-expanded={open}
		aria-controls={id ? `${id}-listbox` : undefined}
		on:click={toggleDropdown}
		on:keydown={handleButtonKeydown}
		{disabled}
		{id}
	>
		<span class="flex items-center gap-2 truncate">
			<span class="font-mono text-sm"
				>{value || $t('currencies.select_currency') || placeholder}</span
			>
			{#if value && !compact}
				<span class="text-xs text-base-content/70 truncate"
					>{$t(`currencies.${value}`) || CURRENCY_LABELS[value]}</span
				>
			{/if}
		</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			class={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
			stroke-width="2"
			aria-hidden="true"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	<div class="dropdown-content z-50 w-full">
		<div class="card border border-base-300 bg-base-100 shadow-xl w-80 max-w-full">
			<div class="p-3 space-y-3">
				<label class="input input-bordered flex items-center gap-2">
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
						on:keydown={handleSearchKeydown}
						aria-label={$t('currencies.search') || 'Search currency'}
						bind:this={searchInput}
					/>
				</label>

				{#if filteredOptions.length}
					<ul
						class="space-y-1 w-full max-h-64 overflow-y-auto overflow-x-hidden"
						role="listbox"
						id={id ? `${id}-listbox` : undefined}
					>
						{#each filteredOptions as option}
							<li>
								<button
									type="button"
									class={`w-full text-left flex flex-col items-start gap-1 px-3 py-2 rounded-lg transition-colors ${
										value === option.code
											? 'bg-primary/10 text-primary font-semibold'
											: 'hover:bg-base-200/80'
									}`}
									on:click={() => selectCurrency(option.code)}
									role="option"
									aria-selected={value === option.code}
								>
									<span class="font-mono text-sm">{option.code}</span>
									{#if option.label}
										<span class="text-xs text-base-content/70 truncate w-full">{option.label}</span>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				{:else}
					<div class="text-sm text-base-content/70 px-3 py-2">
						{$t('currencies.no_matches') || 'No matches'}
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
