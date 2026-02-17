<script lang="ts">
	import type { MoneyValue } from '$lib/types';
	import { createEventDispatcher } from 'svelte';
	import CurrencyDropdown from './CurrencyDropdown.svelte';

	type Props = {
		label?: string;
		value: MoneyValue;
		currencyOptions?: string[];
		priorityCurrencies?: string[];
		placeholder?: string;
		min?: number;
		step?: number;
	};

	export let label: string | undefined = undefined;
	export let value: MoneyValue;
	export let currencyOptions: string[] | undefined = undefined; // Use API currencies by default
	export let priorityCurrencies: string[] = []; // Currencies to show first in dropdown
	export let placeholder = '0.00';
	export let min: number | undefined = 0;
	export let step: number | undefined = 0.01;
	export let showClear: boolean = true;
	export let compact: boolean = false;

	const dispatch = createEventDispatcher<{ change: MoneyValue }>();
	const currencyId = `money-currency-${Math.random().toString(36).slice(2, 8)}`;

	function updateAmount(event: Event) {
		const target = event.target as HTMLInputElement;
		const amount = target.value === '' ? null : Number(target.value);
		value = {
			amount: Number.isNaN(amount) ? null : amount,
			currency: value.currency
		};
		dispatch('change', value);
	}

	function updateCurrency(event: CustomEvent<string | null>) {
		value = {
			amount: value.amount,
			currency: event.detail || null
		};
		dispatch('change', value);
	}

	function clearValue() {
		value = { amount: null, currency: null };
		dispatch('change', value);
	}
</script>

<div class="form-control">
	{#if label}
		<label class="label" for="money-input">
			<span class="label-text font-medium">{label}</span>
		</label>
	{/if}
	<div class="flex gap-2 {compact ? 'flex-row items-center' : 'flex-col sm:flex-row gap-3'}">
		<input
			id="money-input"
			type="number"
			class="input input-bordered bg-base-100/80 focus:bg-base-100 {compact ? 'input-sm flex-1 min-w-0' : 'flex-1'}"
			{placeholder}
			bind:value={value.amount}
			{min}
			{step}
			on:input={updateAmount}
		/>
		<CurrencyDropdown
			id={currencyId}
			value={value.currency}
			options={currencyOptions || undefined}
			{priorityCurrencies}
			{compact}
			on:change={updateCurrency}
		/>
		{#if showClear}
			<button type="button" class="btn btn-neutral-200 {compact ? 'btn-sm' : ''}" on:click={clearValue}> Clear </button>
		{/if}
	</div>
</div>
