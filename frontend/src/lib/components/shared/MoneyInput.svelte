<script lang="ts">
	import type { MoneyValue } from '$lib/types';
	import { CURRENCY_OPTIONS, DEFAULT_CURRENCY } from '$lib/money';
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import CurrencyDropdown from './CurrencyDropdown.svelte';

	interface Props {
		label: string | undefined;
		value: MoneyValue;
		currencyOptions?: string[];
		placeholder?: string;
		min?: number | undefined;
		step?: number | undefined;
		defaultCurrency?: string;
	}

	let {
		label,
		value = $bindable(),
		currencyOptions = CURRENCY_OPTIONS,
		placeholder = '0.00',
		min = 0,
		step = 0.01,
		defaultCurrency = DEFAULT_CURRENCY
	}: Props = $props();

	const dispatch = createEventDispatcher<{ change: MoneyValue }>();
	const currencyId = `money-currency-${Math.random().toString(36).slice(2, 8)}`;

	function updateAmount(event: Event) {
		const target = event.target as HTMLInputElement;
		const amount = target.value === '' ? null : Number(target.value);
		const next: MoneyValue = {
			amount: Number.isNaN(amount) ? null : amount,
			currency: value.currency || defaultCurrency
		};
		dispatch('change', next);
	}

	function updateCurrency(event: CustomEvent<string | null>) {
		const next: MoneyValue = {
			amount: value.amount,
			currency: event.detail || defaultCurrency
		};
		dispatch('change', next);
	}

	function clearValue() {
		dispatch('change', { amount: null, currency: defaultCurrency });
	}
</script>

<div class="flex flex-col">
	{#if label}
		<label class="field-label" for="money-input">{label}</label>
	{/if}
	<div class="join w-full">
		<input
			id="money-input"
			type="number"
			class="input join-item min-w-0 flex-1 bg-base-100"
			{placeholder}
			bind:value={value.amount}
			{min}
			{step}
			oninput={updateAmount}
		/>
		<CurrencyDropdown
			id={currencyId}
			value={value.currency}
			{defaultCurrency}
			options={currencyOptions}
			on:change={updateCurrency}
		/>
		<button type="button" class="btn join-item bg-base-100" onclick={clearValue}>
			{$t('adventures.clear')}
		</button>
	</div>
</div>
