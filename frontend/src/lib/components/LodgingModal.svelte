<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import type { Collection, Lodging } from '$lib/types';
	import LocationDropdown from './LocationDropdown.svelte';
	import DateRangeCollapse from './DateRangeCollapse.svelte';
	import { isAllDay } from '$lib';
	// @ts-ignore
	import { DateTime } from 'luxon';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let lodgingToEdit: Lodging | null = null;

	let modal: HTMLDialogElement;
	let lodging: Lodging = { ...initializeLodging(lodgingToEdit) };
	let fullStartDate: string = '';
	let fullEndDate: string = '';

	type LodgingType = {
		value: string;
		label: string;
	};

	let lodgingTimezone: string | undefined = lodging.timezone ?? undefined;

	// Initialize hotel with values from lodgingToEdit or default values
	function initializeLodging(lodgingToEdit: Lodging | null): Lodging {
		return {
			id: lodgingToEdit?.id || '',
			user_id: lodgingToEdit?.user_id || '',
			name: lodgingToEdit?.name || '',
			type: lodgingToEdit?.type || 'other',
			description: lodgingToEdit?.description || '',
			rating: lodgingToEdit?.rating || NaN,
			link: lodgingToEdit?.link || '',
			check_in: lodgingToEdit?.check_in || null,
			check_out: lodgingToEdit?.check_out || null,
			reservation_number: lodgingToEdit?.reservation_number || '',
			price: lodgingToEdit?.price || null,
			latitude: lodgingToEdit?.latitude || null,
			longitude: lodgingToEdit?.longitude || null,
			location: lodgingToEdit?.location || '',
			is_public: lodgingToEdit?.is_public || false,
			collection: lodgingToEdit?.collection || collection.id,
			created_at: lodgingToEdit?.created_at || '',
			updated_at: lodgingToEdit?.updated_at || '',
			timezone: lodgingToEdit?.timezone || ''
		};
	}

	// Set full start and end dates from collection
	if (collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	// Handle rating change
	$: {
		if (!lodging.rating) {
			lodging.rating = NaN;
		}
	}

	// Show modal on mount
	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) modal.showModal();
	});

	// Close modal
	function close() {
		dispatch('close');
	}

	// Close modal on escape key press
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') close();
	}

	// Handle form submission (save hotel)
	async function handleSubmit(event: Event) {
		event.preventDefault();

		lodging.timezone = lodgingTimezone || null;

		console.log(lodgingTimezone);

		// Auto-set end date if missing but start date exists
		if (lodging.check_in && !lodging.check_out) {
			if (isAllDay(lodging.check_in)) {
				// For all-day, just add one day and keep at UTC 00:00:00
				const start = DateTime.fromISO(lodging.check_in, { zone: 'utc' });
				const nextDay = start.plus({ days: 1 });
				lodging.check_out = nextDay.toISO();
			} else {
				// For timed events, set to next day at 9:00 AM in lodging's timezone, then convert to UTC
				const start = DateTime.fromISO(lodging.check_in, { zone: lodging.timezone || 'utc' });
				const nextDay = start.plus({ days: 1 });
				const end = nextDay.set({ hour: 9, minute: 0, second: 0, millisecond: 0 });
				lodging.check_out = end.toUTC().toISO();
			}
		}

		// Create or update lodging...
		const url = lodging.id === '' ? '/api/lodging' : `/api/lodging/${lodging.id}`;
		const method = lodging.id === '' ? 'POST' : 'PATCH';
		const res = await fetch(url, {
			method,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(lodging)
		});
		const data = await res.json();
		if (data.id) {
			lodging = data as Lodging;
			const toastMessage =
				lodging.id === '' ? 'adventures.adventure_created' : 'adventures.adventure_updated';
			addToast('success', $t(toastMessage));
			dispatch('save', lodging);
		} else {
			const errorMessage =
				lodging.id === ''
					? 'adventures.adventure_create_error'
					: 'adventures.adventure_update_error';
			addToast('error', $t(errorMessage));
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{lodgingToEdit ? $t('lodging.edit_lodging') : $t('lodging.new_lodging')}
		</h3>
		<div class="modal-action items-center">
			<form method="post" style="width: 100%;" on:submit={handleSubmit}>
				<!-- Basic Information Section -->
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" checked />
					<div class="collapse-title text-xl font-medium">
						{$t('adventures.basic_information')}
					</div>
					<div class="collapse-content">
						<!-- Name -->
						<div>
							<label for="name">
								{$t('adventures.name')}<span class="text-red-500">*</span>
							</label>
							<input
								type="text"
								id="name"
								name="name"
								bind:value={lodging.name}
								class="input input-bordered w-full"
								required
							/>
						</div>
						<div>
							<label for="type">
								{$t('transportation.type')}<span class="text-red-500">*</span>
							</label>
							<div>
								<select
									class="select select-bordered w-full max-w-xs"
									name="type"
									id="type"
									bind:value={lodging.type}
								>
									<option disabled selected>{$t('transportation.type')}</option>
									<option value="hotel">{$t('lodging.hotel')}</option>
									<option value="hostel">{$t('lodging.hostel')}</option>
									<option value="resort">{$t('lodging.resort')}</option>
									<option value="bnb">{$t('lodging.bnb')}</option>
									<option value="campground">{$t('lodging.campground')}</option>
									<option value="cabin">{$t('lodging.cabin')}</option>
									<option value="apartment">{$t('lodging.apartment')}</option>
									<option value="house">{$t('lodging.house')}</option>
									<option value="villa">{$t('lodging.villa')}</option>
									<option value="motel">{$t('lodging.motel')}</option>
									<option value="other">{$t('lodging.other')}</option>
								</select>
							</div>
						</div>
						<!-- Description -->
						<div>
							<label for="description">{$t('adventures.description')}</label><br />
							<MarkdownEditor bind:text={lodging.description} editor_height={'h-32'} />
						</div>
						<!-- Rating -->
						<div>
							<label for="rating">{$t('adventures.rating')}</label><br />
							<input
								type="number"
								min="0"
								max="5"
								hidden
								bind:value={lodging.rating}
								id="rating"
								name="rating"
								class="input input-bordered w-full max-w-xs mt-1"
							/>
							<div class="rating -ml-3 mt-1">
								<input
									type="radio"
									name="rating-2"
									class="rating-hidden"
									checked={Number.isNaN(lodging.rating)}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (lodging.rating = 1)}
									checked={lodging.rating === 1}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (lodging.rating = 2)}
									checked={lodging.rating === 2}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (lodging.rating = 3)}
									checked={lodging.rating === 3}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (lodging.rating = 4)}
									checked={lodging.rating === 4}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (lodging.rating = 5)}
									checked={lodging.rating === 5}
								/>
								{#if lodging.rating}
									<button
										type="button"
										class="btn btn-sm btn-error ml-2"
										on:click={() => (lodging.rating = NaN)}
									>
										{$t('adventures.remove')}
									</button>
								{/if}
							</div>
						</div>
						<!-- Link -->
						<div>
							<label for="link">{$t('adventures.link')}</label>
							<input
								type="url"
								id="link"
								name="link"
								bind:value={lodging.link}
								class="input input-bordered w-full"
							/>
						</div>
					</div>
				</div>

				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" checked />
					<div class="collapse-title text-xl font-medium">
						{$t('adventures.lodging_information')}
					</div>
					<div class="collapse-content">
						<!-- Reservation Number -->
						<div>
							<label for="date">
								{$t('lodging.reservation_number')}
							</label>
							<div>
								<input
									type="text"
									id="reservation_number"
									name="reservation_number"
									bind:value={lodging.reservation_number}
									class="input input-bordered w-full max-w-xs mt-1"
								/>
							</div>
						</div>
						<!-- Price -->
						<div>
							<label for="price">
								{$t('adventures.price')}
							</label>
							<div>
								<input
									type="number"
									id="price"
									name="price"
									bind:value={lodging.price}
									step="0.01"
									class="input input-bordered w-full max-w-xs mt-1"
								/>
							</div>
						</div>
					</div>
				</div>

				<DateRangeCollapse
					type="lodging"
					bind:utcStartDate={lodging.check_in}
					bind:utcEndDate={lodging.check_out}
					bind:selectedStartTimezone={lodgingTimezone}
					{collection}
				/>

				<!-- Location Information -->
				<LocationDropdown bind:item={lodging} />

				<!-- Form Actions -->
				<div class="mt-4">
					<button type="submit" class="btn btn-primary">
						{$t('notes.save')}
					</button>
					<button type="button" class="btn" on:click={close}>
						{$t('about.close')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
