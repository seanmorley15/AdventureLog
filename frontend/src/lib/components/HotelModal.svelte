<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import { appVersion } from '$lib/config';
	import { DefaultMarker, MapEvents, MapLibre } from 'svelte-maplibre';
	import type { Collection, Hotel, ReverseGeocode, OpenStreetMapPlace, Point } from '$lib/types';
	import LocationDropdown from './LocationDropdown.svelte';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let hotelToEdit: Hotel | null = null;

	let modal: HTMLDialogElement;
	let constrainDates: boolean = false;
	let hotel: Hotel = { ...initializeHotel(hotelToEdit) };
	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let reverseGeocodePlace: any | null = null;
	let query: string = '';
	let places: OpenStreetMapPlace[] = [];
	let noPlaces: boolean = false;
	let is_custom_location: boolean = false;
	let markers: Point[] = [];

	// Format date as local datetime
	function toLocalDatetime(value: string | null): string {
		if (!value) return '';
		const date = new Date(value);
		return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm
	}

	// Initialize hotel with values from hotelToEdit or default values
	function initializeHotel(hotelToEdit: Hotel | null): Hotel {
		return {
			id: hotelToEdit?.id || '',
			user_id: hotelToEdit?.user_id || '',
			name: hotelToEdit?.name || '',
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
			collection: hotelToEdit?.collection || '',
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
		if (!hotel.rating) {
			hotel.rating = NaN;
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

		if (hotel.check_in && !hotel.check_out) {
			const checkInDate = new Date(hotel.check_in);
			checkInDate.setDate(checkInDate.getDate() + 1);
			hotel.check_out = checkInDate.toISOString();
		}

		if (hotel.check_in && hotel.check_out && hotel.check_in > hotel.check_out) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		// Create or update hotel
		const url = hotel.id === '' ? '/api/hotels' : `/api/hotels/${hotel.id}`;
		const method = hotel.id === '' ? 'POST' : 'PATCH';
		const res = await fetch(url, {
			method,
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(hotel)
		});
		const data = await res.json();
		if (data.id) {
			hotel = data as Hotel;
			const toastMessage =
				hotel.id === '' ? 'adventures.adventure_created' : 'adventures.adventure_updated';
			addToast('success', $t(toastMessage));
			dispatch('save', hotel);
		} else {
			const errorMessage =
				hotel.id === '' ? 'adventures.adventure_create_error' : 'adventures.adventure_update_error';
			addToast('error', $t(errorMessage));
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{hotelToEdit
				? $t('transportation.edit_transportation')
				: $t('transportation.new_transportation')}
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
								bind:value={hotel.name}
								class="input input-bordered w-full"
								required
							/>
						</div>
						<!-- Description -->
						<div>
							<label for="description">{$t('adventures.description')}</label><br />
							<MarkdownEditor bind:text={hotel.description} editor_height={'h-32'} />
						</div>
						<!-- Rating -->
						<div>
							<label for="rating">{$t('adventures.rating')}</label><br />
							<input
								type="number"
								min="0"
								max="5"
								hidden
								bind:value={hotel.rating}
								id="rating"
								name="rating"
								class="input input-bordered w-full max-w-xs mt-1"
							/>
							<div class="rating -ml-3 mt-1">
								<input
									type="radio"
									name="rating-2"
									class="rating-hidden"
									checked={Number.isNaN(hotel.rating)}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (hotel.rating = 1)}
									checked={hotel.rating === 1}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (hotel.rating = 2)}
									checked={hotel.rating === 2}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (hotel.rating = 3)}
									checked={hotel.rating === 3}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (hotel.rating = 4)}
									checked={hotel.rating === 4}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (hotel.rating = 5)}
									checked={hotel.rating === 5}
								/>
								{#if hotel.rating}
									<button
										type="button"
										class="btn btn-sm btn-error ml-2"
										on:click={() => (hotel.rating = NaN)}
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
								bind:value={hotel.link}
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
								{$t('adventures.start_date')}
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
									bind:value={hotel.check_in}
									min={constrainDates ? fullStartDate : ''}
									max={constrainDates ? fullEndDate : ''}
									class="input input-bordered w-full max-w-xs mt-1"
								/>
							</div>
						</div>
						<!-- End Date -->
						{#if hotel.check_in}
							<div>
								<label for="end_date">
									{$t('adventures.end_date')}
								</label>
								<div>
									<input
										type="datetime-local"
										id="end_date"
										name="end_date"
										min={constrainDates ? hotel.check_in : ''}
										max={constrainDates ? fullEndDate : ''}
										bind:value={hotel.check_out}
										class="input input-bordered w-full max-w-xs mt-1"
									/>
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Location Information -->
				<LocationDropdown bind:item={hotel} />

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
