<script lang="ts">
	import { onMount } from 'svelte';
	import type { Attachment } from 'svelte/attachments';
	import { page } from '$app/state';
	import CalendarIcon from '~icons/mdi/calendar';
	import ClockIcon from '~icons/mdi/clock-outline';
	import CloseIcon from '~icons/mdi/close';
	import {
		normalizeDateFormat,
		formatDisplayDate,
		formatDisplayTime,
		getFirstDayOfWeek,
		getDateInputHint,
		parseTypedDate,
		prefersHour12,
		resolveDateFormatLocale
	} from '#lib/dateFormat.js';
	import { attachPopoverFlip } from '#lib/utils/flipDropdown.js';

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
		placeholder,
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
	// Month/weekday names follow the app language; the date *format* (order) follows the preference.
	// YMD maps to a Swedish locale for ISO-style numbers, which would otherwise yield Swedish month names.
	const nameLocale = $derived(
		preference === 'ymd' ? page.data?.locale || navigator.language || 'en-US' : locale
	);
	const firstDayOfWeek = $derived(getFirstDayOfWeek(preference));

	const uniqueId = $derived(id || `${uid}-date`);
	const popoverId = $derived(`${uniqueId}-popover`);
	const timePopoverId = $derived(`${uniqueId}-time-popover`);
	const anchorName = $derived(`--${uniqueId.replace(/[^a-zA-Z0-9_-]/g, '')}`);
	const timeAnchorName = $derived(`${anchorName}-time`);

	const datePart = $derived(value && value.includes('T') ? value.split('T')[0] : value || '');
	const hasTime = $derived(!!(value && value.includes('T')));
	const timePart = $derived(hasTime ? value?.split('T')[1]?.substring(0, 5) || '00:00' : '00:00');

	const displayDate = $derived(datePart ? formatDisplayDate(datePart, preference) : '');
	const hint = $derived(placeholder ?? getDateInputHint(preference));
	const hour12 = $derived(prefersHour12(preference));
	const displayTime = $derived(hasTime ? formatDisplayTime(timePart, preference) : 'Pick a time');
	const hourOptions = $derived(
		hour12
			? [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
			: Array.from({ length: 24 }, (_, index) => index)
	);

	const clock = $derived.by(() => {
		const match = /^(\d{1,2}):(\d{2})/.exec(timePart);
		const hours = Math.min(23, Math.max(0, Number(match?.[1] ?? 0) || 0));
		const minutes = Math.min(59, Math.max(0, Number(match?.[2] ?? 0) || 0));
		return {
			hours,
			minutes,
			period: hours >= 12 ? ('PM' as const) : ('AM' as const),
			hour12Value: hours % 12 === 0 ? 12 : hours % 12
		};
	});
	const minuteOptions = Array.from({ length: 60 }, (_, index) => index);

	const minDate = $derived(min ? min.split('T')[0] : undefined);
	const maxDate = $derived(max ? max.split('T')[0] : undefined);

	const sizeClass = $derived(size === 'xs' ? 'input-xs' : size === 'sm' ? 'input-sm' : '');
	const clearPadding = $derived(size === 'xs' ? 'pr-6' : size === 'sm' ? 'pr-8' : 'pr-10');
	const clearIconClass = $derived(size === 'xs' ? 'size-3.5' : 'size-4');
	const clearHitClass = $derived(size === 'xs' ? 'w-6' : size === 'sm' ? 'w-8' : 'w-9');

	const canClearDate = $derived(!!(clearable && datePart && !readonly && !disabled));
	const canClearTime = $derived(!!(clearable && hasTime && !readonly && !disabled));
	const controlHeightClass = $derived(size === 'md' ? 'date-input-md' : '');

	let popoverElement: HTMLDivElement | undefined = $state();

	// Typed entry: edits stay in `draft` until Enter/blur, then are parsed and committed.
	let editing = $state(false);
	let draft = $state('');
	let invalid = $state(false);

	function startEditing(event: FocusEvent) {
		editing = true;
		draft = displayDate;
		invalid = false;
		(event.currentTarget as HTMLInputElement).select();
	}

	function commitDraft() {
		if (!editing) return;
		editing = false;
		const text = draft.trim();

		if (!text) {
			if (datePart) handleClearDate();
			invalid = false;
			return;
		}

		const parsed = parseTypedDate(text, preference);
		const outOfRange = !!parsed && ((minDate && parsed < minDate) || (maxDate && parsed > maxDate));
		if (!parsed || outOfRange) {
			invalid = true;
			return;
		}

		invalid = false;
		if (parsed === datePart) return;
		value = showTime && hasTime ? `${parsed}T${timePart}` : showTime ? `${parsed}T00:00` : parsed;
		onchange?.(value);
	}

	function openCalendar() {
		if (disabled || readonly || !popoverElement) return;
		if (!popoverElement.matches(':popover-open')) popoverElement.showPopover();
	}

	function handleDateKeydown(event: KeyboardEvent) {
		if (event.key === 'Tab') {
			popoverElement?.hidePopover();
		} else if (event.key === 'Enter') {
			event.preventDefault();
			popoverElement?.hidePopover();
			commitDraft();
			(event.currentTarget as HTMLInputElement).select();
			editing = true;
			draft = displayDate;
		} else if (event.key === 'Escape') {
			editing = false;
			invalid = false;
			(event.currentTarget as HTMLInputElement).blur();
		}
	}

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

	// Calendar navigation: jump by year / pick month+year without paging month by month.
	let calendarElement: (HTMLElement & { focusedDate?: string }) | undefined = $state();
	let viewDate = $state(''); // YYYY-MM-DD of the month being shown

	const todayIso = $derived.by(() => {
		const now = new Date();
		return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
	});
	const viewYear = $derived(Number((viewDate || datePart || todayIso).slice(0, 4)));
	const viewMonth = $derived(Number((viewDate || datePart || todayIso).slice(5, 7)));
	const monthNames = $derived(
		Array.from({ length: 12 }, (_, i) => {
			try {
				return new Intl.DateTimeFormat(nameLocale, { month: 'long' }).format(new Date(2000, i, 1));
			} catch {
				return String(i + 1);
			}
		})
	);
	const yearOptions = $derived.by(() => {
		const current = new Date().getFullYear();
		const from = Math.min(minDate ? Number(minDate.slice(0, 4)) : current - 100, viewYear);
		const to = Math.max(maxDate ? Number(maxDate.slice(0, 4)) : current + 20, viewYear);
		return Array.from({ length: to - from + 1 }, (_, i) => to - i); // newest first
	});

	function clampIso(iso: string) {
		if (minDate && iso < minDate) return minDate;
		if (maxDate && iso > maxDate) return maxDate;
		return iso;
	}

	function goTo(year: number, month: number) {
		// Normalise overflow (month 0 / 13) and keep day within the target month
		const base = new Date(year, month - 1, 1);
		const y = base.getFullYear();
		const m = base.getMonth() + 1;
		const day = Math.min(Number((viewDate || datePart || todayIso).slice(8, 10)) || 1, 28);
		const iso = clampIso(
			`${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`
		);
		viewDate = iso;
		if (calendarElement) calendarElement.focusedDate = iso;
	}

	const attachCalendar: Attachment<HTMLElement> = (element) => {
		calendarElement = element as HTMLElement & { focusedDate?: string };
		const onFocusDay = (event: Event) => {
			const d = (event as CustomEvent<Date>).detail;
			if (d instanceof Date) {
				viewDate = `${String(d.getFullYear()).padStart(4, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
			}
		};
		element.addEventListener('change', handleCalendarChange);
		element.addEventListener('focusday', onFocusDay);
		return () => {
			element.removeEventListener('change', handleCalendarChange);
			element.removeEventListener('focusday', onFocusDay);
			if (calendarElement === element) calendarElement = undefined;
		};
	};

	const capturePopover: Attachment<HTMLDivElement> = (element) => {
		popoverElement = element;
		const onToggle = (event: Event) => {
			if ((event as ToggleEvent).newState === 'open') viewDate = datePart;
		};
		element.addEventListener('toggle', onToggle);
		const detachFlip = attachPopoverFlip(element, () => document.getElementById(uniqueId), 320);
		return () => {
			detachFlip();
			element.removeEventListener('toggle', onToggle);
			if (popoverElement === element) popoverElement = undefined;
		};
	};

	function to24Hour(hour: number, period: 'AM' | 'PM') {
		if (period === 'AM') return hour === 12 ? 0 : hour;
		return hour === 12 ? 12 : hour + 12;
	}

	function commitTime(hours: number, minutes: number) {
		if (!datePart) return;
		const next = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
		value = `${datePart}T${next}`;
		onchange?.(value);
	}

	function selectHour(hour: number) {
		commitTime(hour12 ? to24Hour(hour, clock.period) : hour, clock.minutes);
	}

	function selectMinute(minute: number) {
		commitTime(clock.hours, minute);
	}

	function selectPeriod(period: 'AM' | 'PM') {
		commitTime(to24Hour(clock.hour12Value, period), clock.minutes);
	}

	const scrollTimeSelection: Attachment<HTMLElement> = (element) => {
		const detachFlip = attachPopoverFlip(
			element,
			() => document.getElementById(`${uniqueId}-time`),
			360
		);
		const onToggle = (event: Event) => {
			if ((event as ToggleEvent).newState !== 'open') return;
			element.querySelectorAll('[aria-pressed="true"]').forEach((node) => {
				node.scrollIntoView({ block: 'center' });
			});
		};
		element.addEventListener('toggle', onToggle);
		return () => {
			detachFlip();
			element.removeEventListener('toggle', onToggle);
		};
	};

	function handleClearDate() {
		value = '';
		onchange?.('');
	}

	function handleClearTime() {
		if (!datePart) {
			handleClearDate();
			return;
		}
		value = datePart;
		onchange?.(datePart);
	}
</script>

{#if label}
	<label class="field-label" for={uniqueId}>{label}</label>
{/if}

<div class={['date-field flex w-full min-w-0 flex-col', showTime && 'is-timed', className]}>
	<div class="date-field-row">
		<div class={['date-input-date', canClearDate && 'join']}>
			<div
				class={[
					'input date-input-trigger font-normal',
					sizeClass,
					controlHeightClass,
					canClearDate && 'join-item',
					invalid && 'input-error'
				]}
				style:anchor-name={anchorName}
			>
				<button
					type="button"
					popovertarget={popoverId}
					class="date-input-calendar-btn"
					disabled={disabled || readonly}
					aria-label="Open calendar"
					tabindex="-1"
				>
					<CalendarIcon class={size === 'md' ? 'size-4 shrink-0' : 'size-3.5 shrink-0'} />
				</button>
				<input
					id={uniqueId}
					type="text"
					inputmode="text"
					autocomplete="off"
					class="date-input-text"
					placeholder={hint}
					value={editing ? draft : displayDate}
					{disabled}
					{readonly}
					aria-invalid={invalid}
					onfocus={startEditing}
					oninput={(e) => {
						draft = (e.currentTarget as HTMLInputElement).value;
						invalid = false;
					}}
					onclick={openCalendar}
					onblur={commitDraft}
					onkeydown={handleDateKeydown}
				/>
			</div>

			{#if canClearDate}
				<button
					type="button"
					class={['input date-input-clear join-item', sizeClass, controlHeightClass]}
					onclick={handleClearDate}
					aria-label="Clear date"
				>
					<CloseIcon class="h-4 w-4" />
				</button>
			{/if}
		</div>

		{#if showTime}
			<div class={['date-input-time-wrap', canClearTime && 'join']}>
				<button
					type="button"
					id={`${uniqueId}-time`}
					popovertarget={timePopoverId}
					class={[
						'input date-input-time justify-start font-normal',
						sizeClass,
						controlHeightClass,
						canClearTime && 'join-item'
					]}
					style:anchor-name={timeAnchorName}
					disabled={disabled || readonly || !datePart}
					aria-label="Time"
				>
					<ClockIcon
						class={size === 'md' ? 'size-4 shrink-0 opacity-60' : 'size-3.5 shrink-0 opacity-60'}
					/>
					<span class={['truncate', !hasTime && 'text-base-content/50']}>{displayTime}</span>
				</button>
				{#if canClearTime}
					<button
						type="button"
						class={['input date-input-clear join-item', sizeClass, controlHeightClass]}
						onclick={handleClearTime}
						aria-label="Clear time"
					>
						<CloseIcon class="h-4 w-4" />
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>

<div
	{@attach capturePopover}
	popover
	id={popoverId}
	class="dropdown bg-base-100 rounded-box shadow-lg"
	style:position-anchor={anchorName}
>
	{#if callyReady}
		<div class="cal-nav">
			<button
				type="button"
				class="btn btn-ghost btn-xs btn-square"
				aria-label="Previous year"
				onclick={() => goTo(viewYear - 1, viewMonth)}>«</button
			>
			<select
				class="select select-xs cal-select"
				aria-label="Month"
				value={viewMonth}
				onchange={(e) => goTo(viewYear, Number(e.currentTarget.value))}
			>
				{#each monthNames as name, i (i)}
					<option value={i + 1}>{name}</option>
				{/each}
			</select>
			<select
				class="select select-xs cal-select cal-year"
				aria-label="Year"
				value={viewYear}
				onchange={(e) => goTo(Number(e.currentTarget.value), viewMonth)}
			>
				{#each yearOptions as year (year)}
					<option value={year}>{year}</option>
				{/each}
			</select>
			<button
				type="button"
				class="btn btn-ghost btn-xs btn-square"
				aria-label="Next year"
				onclick={() => goTo(viewYear + 1, viewMonth)}>»</button
			>
			<button
				type="button"
				class="btn btn-ghost btn-xs"
				onclick={() => goTo(Number(todayIso.slice(0, 4)), Number(todayIso.slice(5, 7)))}
				>Today</button
			>
		</div>
		<calendar-date
			class="cally"
			{@attach attachCalendar}
			value={datePart || undefined}
			min={minDate}
			max={maxDate}
			locale={nameLocale}
			{firstDayOfWeek}
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

{#if showTime}
	<div
		{@attach scrollTimeSelection}
		popover
		id={timePopoverId}
		class="dropdown time-popover bg-base-100 rounded-box shadow-lg"
		style:position-anchor={timeAnchorName}
	>
		<p class="mb-2 text-center text-base font-semibold tabular-nums">{displayTime}</p>
		<div class="time-picker">
			<div class="time-col">
				<span class="time-col-label">Hour</span>
				<div class="time-col-list">
					{#each hourOptions as hour (hour)}
						{@const selected = hour12 ? hour === clock.hour12Value : hour === clock.hours}
						<button
							type="button"
							class={['btn btn-sm', selected ? 'btn-primary' : 'btn-ghost']}
							aria-pressed={selected}
							onclick={() => selectHour(hour)}
						>
							{hour12 ? hour : String(hour).padStart(2, '0')}
						</button>
					{/each}
				</div>
			</div>
			<div class="time-col">
				<span class="time-col-label">Minute</span>
				<div class="time-col-list">
					{#each minuteOptions as minute (minute)}
						{@const selected = minute === clock.minutes}
						<button
							type="button"
							class={['btn btn-sm', selected ? 'btn-primary' : 'btn-ghost']}
							aria-pressed={selected}
							onclick={() => selectMinute(minute)}
						>
							{String(minute).padStart(2, '0')}
						</button>
					{/each}
				</div>
			</div>
			{#if hour12}
				<div class="time-col">
					<span class="time-col-label" aria-hidden="true">&nbsp;</span>
					<div class="flex flex-col gap-1">
						<button
							type="button"
							class={['btn btn-sm', clock.period === 'AM' ? 'btn-primary' : 'btn-ghost']}
							aria-pressed={clock.period === 'AM'}
							onclick={() => selectPeriod('AM')}
						>
							AM
						</button>
						<button
							type="button"
							class={['btn btn-sm', clock.period === 'PM' ? 'btn-primary' : 'btn-ghost']}
							aria-pressed={clock.period === 'PM'}
							onclick={() => selectPeriod('PM')}
						>
							PM
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

{#if name}
	<input type="hidden" {name} value={value ?? ''} />
{/if}

<style>
	.date-field {
		container-type: inline-size;
	}

	.date-field-row {
		display: flex;
		width: 100%;
		min-width: 0;
		align-items: stretch;
		gap: 0.5rem;
	}

	.date-input-date {
		display: flex;
		flex: 1 1 auto;
		min-width: 0;
	}

	.date-input-trigger {
		width: 100%;
		max-width: none;
		min-width: 0;
		flex: 1 1 auto;
	}

	.date-input-time-wrap {
		display: flex;
		flex: 0 0 auto;
		min-width: 0;
		align-items: stretch;
	}

	.date-input-time {
		flex: 1 1 auto;
		width: 9.75rem;
		min-width: 9.75rem;
		max-width: 9.75rem;
		padding-inline: 0.65rem;
	}

	.date-input-trigger {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.date-input-calendar-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		flex: 0 0 auto;
		opacity: 0.6;
		cursor: pointer;
	}

	.date-input-calendar-btn:hover:not(:disabled) {
		opacity: 1;
	}

	.date-input-text {
		flex: 1 1 auto;
		min-width: 0;
		width: 100%;
		background: transparent;
		outline: none;
		border: 0;
		font: inherit;
	}

	.date-input-md {
		height: 3rem;
		min-height: 3rem;
		font-size: 1rem;
	}

	.date-input-clear {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 3rem;
		min-width: 3rem;
		max-width: 3rem;
		padding-inline: 0;
		flex: 0 0 3rem;
		cursor: pointer;
	}

	.date-input-clear.input-sm,
	.date-input-clear.input-xs {
		width: 2rem;
		min-width: 2rem;
		max-width: 2rem;
		flex-basis: 2rem;
	}

	.cal-nav {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem 0.5rem 0;
	}

	.cal-select {
		width: auto;
		flex: 1 1 auto;
		min-width: 0;
	}

	.cal-year {
		flex: 0 0 5.25rem;
	}

	.time-popover {
		padding: 0.75rem;
	}

	.time-picker {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.time-col {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.time-col:has(.time-col-list) {
		min-width: 4.25rem;
	}

	.time-col-label {
		font-size: 0.75rem;
		line-height: 1rem;
		font-weight: 600;
		opacity: 0.6;
	}

	.time-col-list {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		max-height: 14rem;
		overflow-y: auto;
		scrollbar-width: thin;
		padding-inline: 0.1rem;
	}

	.time-col-list .btn {
		width: 100%;
	}

	@container (max-width: 22rem) {
		.is-timed .date-field-row {
			flex-direction: column;
		}

		.is-timed .date-input-time-wrap,
		.is-timed .date-input-time {
			flex: 1 1 auto;
			width: 100%;
			min-width: 0;
			max-width: none;
		}
	}
</style>
