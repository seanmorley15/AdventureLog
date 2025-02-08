<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import type { Collection, Lodging } from '$lib/types';
	import LocationDropdown from './LocationDropdown.svelte';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let lodgingToEdit: Lodging | null = null;

	let modal: HTMLDialogElement;
	let constrainDates: boolean = false;
	let lodging: Lodging = { ...initializeLodging(lodgingToEdit) };
	let fullStartDate: string = '';
	let fullEndDate: string = '';

	// Format date as local datetime
	function toLocalDatetime(value: string | null): string {
		if (!value) return '';
		const date = new Date(value);
		return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm
	}

	type LodgingType = {
		value: string;
		label: string;
	};

	const LODGING_TYPES: LodgingType[] = [
		{ value: 'hotel', label: 'Hotel' },
		{ value: 'hostel', label: 'Hostel' },
		{ value: 'resort', label: 'Resort' },
		{ value: 'bnb', label: 'Bed & Breakfast' },
		{ value: 'campground', label: 'Campground' },
		{ value: 'cabin', label: 'Cabin' },
		{ value: 'apartment', label: 'Apartment' },
		{ value: 'house', label: 'House' },
		{ value: 'villa', label: 'Villa' },
		{ value: 'motel', label: 'Motel' },
		{ value: 'other', label: 'Other' }
	];

	// Initialize hotel with values from hotelToEdit or default values
	function initializeLodging(hotelToEdit: Lodging | null): Lodging {
		return {
			id: hotelToEdit?.id || '',
			user_id: hotelToEdit?.user_id || '',
			name: hotelToEdit?.name || '',
			type: hotelToEdit?.type || 'other',
			description: hotelToEdit?.description || '',
			rating: hotelToEdit?.rating || NaN,
			link: hotelToEdit?.link || '',
			check_in: hotelToEdit?.check_in || null,
			check_out: hotelToEdit?.check_out || null,
			reservation_number: hotelToEdit?.reservation_number || '',
			price: hotelToEdit?.price || null,
			latitude: hotelToEdit?.latitude || null,
			longitude: hotelToEdit?.longitude || null,
			location: hotelToEdit?.location || '',
			is_public: hotelToEdit?.is_public || false,
			collection: hotelToEdit?.collection || collection.id,
			created_at: hotelToEdit?.created_at || '',
			updated_at: hotelToEdit?.updated_at || ''
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

		if (lodging.check_in && !lodging.check_out) {
			const checkInDate = new Date(lodging.check_in);
			checkInDate.setDate(checkInDate.getDate() + 1);
			lodging.check_out = checkInDate.toISOString();
		}

		if (lodging.check_in && lodging.check_out && lodging.check_in > lodging.check_out) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		// Create or update hotel
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
						{$t('adventures.date_information')}
					</div>
					<div class="collapse-content">
						<!-- Start Date -->
						<div>
							<label for="date">
								{$t('lodging.check_in')}
							</label>

							{#if collection && collection.start_date && collection.end_date}<label
									class="label cursor-pointer flex items-start space-x-2"
								>
									<span class="label-text">{$t('adventures.date_constrain')}</span>
									<input
										type="checkbox"
										class="toggle toggle-primary"
										id="constrain_dates"
										name="constrain_dates"
										on:change={() => (constrainDates = !constrainDates)}
									/></label
								>
							{/if}
							<div>
								<input
									type="datetime-local"
									id="date"
									name="date"
									bind:value={lodging.check_in}
									min={constrainDates ? fullStartDate : ''}
									max={constrainDates ? fullEndDate : ''}
									class="input input-bordered w-full max-w-xs mt-1"
								/>
							</div>
						</div>
						<!-- End Date -->
						{#if lodging.check_out}
							<div>
								<label for="end_date">
									{$t('lodging.check_out')}
								</label>
								<div>
									<input
										type="datetime-local"
										id="end_date"
										name="end_date"
										min={constrainDates ? lodging.check_in : ''}
										max={constrainDates ? fullEndDate : ''}
										bind:value={lodging.check_out}
										class="input input-bordered w-full max-w-xs mt-1"
									/>
								</div>
							</div>
						{/if}
					</div>
				</div>

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
