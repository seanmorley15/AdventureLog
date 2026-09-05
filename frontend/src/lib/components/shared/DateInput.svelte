<script lang="ts">
	import { onMount } from 'svelte';
	import type { Attachment } from 'svelte/attachments';
	import { page } from '$app/state';
	import {
		normalizeDateFormat,
		formatDisplayDate,
		getFirstDayOfWeek,
		resolveDateFormatLocale
	} from '$lib/dateFormat';

	interface Props {
		value?: string | null;
		label?: string;
		id?: string;
		name?: string;
		min?: string;
		max?: string;
		disabled?: boolean;
		readonly?: boolean;
		showTime?: boolean;
		placeholder?: string;
		size?: 'xs' | 'sm' | 'md';
		clearable?: boolean;
		onchange?: (value: string | null) => void;
		class?: string;
	}

	let {
		value = $bindable(''),
		label,
		id,
		name,
		min,
		max,
		disabled = false,
		readonly = false,
		showTime = false,
		placeholder = 'Pick a date',
		size = 'md',
		clearable = true,
		onchange,
		class: className
	}: Props = $props();

	// Cally registers custom elements and touches `document` at import time — client only.
	let callyReady = $state(false);
	onMount(() => {
		void import('cally').then(() => {
			callyReady = true;
		});
	});

	const uid = $props.id();

	const preference = $derived(normalizeDateFormat(page.data?.user?.date_format));
	const locale = $derived(resolveDateFormatLocale(preference));
	const firstDayOfWeek = $derived(getFirstDayOfWeek(preference));

	const uniqueId = $derived(id || `${uid}-date`);
	const popoverId = $derived(`${uniqueId}-popover`);
	const anchorName = $derived(`--${uniqueId.replace(/[^a-zA-Z0-9_-]/g, '')}`);

	const datePart = $derived(value && value.includes('T') ? value.split('T')[0] : value || '');
	const timePart = $derived(
		value && value.includes('T') ? value.split('T')[1]?.substring(0, 5) || '00:00' : '00:00'
	);

	const displayDate = $derived(datePart ? formatDisplayDate(datePart, preference) : placeholder);

	const minDate = $derived(min ? min.split('T')[0] : undefined);
	const maxDate = $derived(max ? max.split('T')[0] : undefined);

	const sizeClass = $derived(size === 'xs' ? 'input-xs' : size === 'sm' ? 'input-sm' : '');

	const canClear = $derived(!!(clearable && value && !readonly && !disabled));

	let popoverElement: HTMLDivElement | undefined = $state();

	function handleCalendarChange(e: Event) {
		const target = e.currentTarget as HTMLElement & { value: string };
		const newDate = target.value;
		if (!newDate) return;

		if (showTime) {
			value = `${newDate}T${timePart || '00:00'}`;
		} else {
			value = newDate;
		}

		onchange?.(value);
		popoverElement?.hidePopover();
	}

	const listenForCalendarChange: Attachment<HTMLElement> = (element) => {
		element.addEventListener('change', handleCalendarChange);
		return () => element.removeEventListener('change', handleCalendarChange);
	};

	const capturePopover: Attachment<HTMLDivElement> = (element) => {
		popoverElement = element;
		return () => {
			if (popoverElement === element) popoverElement = undefined;
		};
	};

	function handleTimeChange(e: Event) {
		const target = e.currentTarget as HTMLInputElement;
		const newTime = target.value || '00:00';

		if (datePart) {
			value = `${datePart}T${newTime}`;
			onchange?.(value);
		}
	}

	function handleClear() {
		value = '';
		onchange?.('');
	}
</script>

{#if label}
	<label class="field-label" for={uniqueId}>{label}</label>
{/if}

<div class={['flex gap-2 items-center w-full', className]}>
	<div class={['flex-1 min-w-0', canClear && 'join']}>
		<button
			popovertarget={popoverId}
			class={['input w-full justify-start font-normal', sizeClass, canClear && 'join-item']}
			id={uniqueId}
			style:anchor-name={anchorName}
			disabled={disabled || readonly}
			type="button"
		>
			<span class={!datePart ? 'text-base-content/50' : ''}>{displayDate}</span>
		</button>

		{#if canClear}
			<button
				type="button"
				class={['btn btn-square', sizeClass || 'btn-md', 'join-item bg-base-100']}
				onclick={handleClear}
				aria-label="Clear date"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-4 w-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		{/if}
	</div>

	{#if showTime}
		<input
			type="time"
			class={['input', sizeClass]}
			value={timePart}
			oninput={handleTimeChange}
			disabled={disabled || readonly || !datePart}
			aria-label="Time"
		/>
	{/if}
</div>

<div
	{@attach capturePopover}
	popover
	id={popoverId}
	class="dropdown bg-base-100 rounded-box shadow-lg"
	style:position-anchor={anchorName}
>
	{#if callyReady}
		<calendar-date
			class="cally"
			{@attach listenForCalendarChange}
			value={datePart || undefined}
			min={minDate}
			max={maxDate}
			{locale}
			firstDayOfWeek={firstDayOfWeek}
		>
			<svg
				aria-label="Previous"
				class="fill-current size-4"
				slot="previous"
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
			>
				<path d="M15.75 19.5 8.25 12l7.5-7.5"></path>
			</svg>
			<svg
				aria-label="Next"
				class="fill-current size-4"
				slot="next"
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
			>
				<path d="m8.25 4.5 7.5 7.5-7.5 7.5"></path>
			</svg>
			<calendar-month></calendar-month>
		</calendar-date>
	{/if}
</div>

{#if name}
	<input type="hidden" {name} value={value ?? ''} />
{/if}
