<script lang="ts">
	import type { MoneyValue } from '$lib/types';
	import { CURRENCY_OPTIONS } from '$lib/money';
	import { createEventDispatcher } from 'svelte';
	import CurrencyDropdown from './CurrencyDropdown.svelte';

	type Props = {
		label?: string;
		value: MoneyValue;
		currencyOptions?: string[];
		placeholder?: string;
		min?: number;
		step?: number;
	};

	interface Props {
		label: string | undefined;
		value: MoneyValue;
		currencyOptions?: string[];
		placeholder?: string;
		min?: number | undefined;
		step?: number | undefined;
	}

	let {
		label,
		value = $bindable(),
		currencyOptions = CURRENCY_OPTIONS,
		placeholder = '0.00',
		min = 0,
		step = 0.01
	}: Props = $props();

	const dispatch = createEventDispatcher<{ change: MoneyValue }>();
	const currencyId = `money-currency-${Math.random().toString(36).slice(2, 8)}`;

	function updateAmount(event: Event) {
		const target = event.target as HTMLInputElement;
		const amount = target.value === '' ? null : Number(target.value);
		const next: MoneyValue = {
			amount: Number.isNaN(amount) ? null : amount,
			currency: value.currency
		};
		dispatch('change', next);
	}

	function updateCurrency(event: CustomEvent<string | null>) {
		const next: MoneyValue = {
			amount: value.amount,
			currency: event.detail || null
		};
		dispatch('change', next);
	}

	function clearValue() {
		dispatch('change', { amount: null, currency: null });
	}
</script>

<div class="flex flex-col">
	{#if label}
		<label class="field-label" for="money-input">{label}</label>
	{/if}
	<div class="flex gap-3 flex-col sm:flex-row">
		<input
			id="money-input"
			type="number"
			class="input bg-base-100/80 focus:bg-base-100 flex-1"
			{placeholder}
			bind:value={value.amount}
			{min}
			{step}
			oninput={updateAmount}
		/>
		<CurrencyDropdown
			id={currencyId}
			value={value.currency}
			options={currencyOptions}
			on:change={updateCurrency}
		/>
		<button type="button" class="btn btn-ghost" onclick={clearValue}> Clear </button>
	</div>
</div>
