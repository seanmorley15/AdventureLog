<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Collection, Hotel } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import MarkdownEditor from './MarkdownEditor.svelte';
	import { appVersion } from '$lib/config';
	import { DefaultMarker, MapLibre } from 'svelte-maplibre';

	export let collection: Collection;
	export let hotelToEdit: Hotel | null = null;

	let constrainDates: boolean = false;

	function toLocalDatetime(value: string | null): string {
		if (!value) return '';
		const date = new Date(value);
		return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm
	}

	let hotel: Hotel = {
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

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	if (collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	$: {
		if (!hotel.rating) {
			hotel.rating = NaN;
		}
	}

	console.log(hotel);

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		console.log(hotel);

		if (hotel.check_in && !hotel.check_out) {
			const checkInDate = new Date(hotel.check_in);
			checkInDate.setDate(checkInDate.getDate() + 1);
			hotel.check_out = checkInDate.toISOString();
		}

		if (hotel.check_in && hotel.check_out && hotel.check_in > hotel.check_out) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		if (hotel.id === '') {
			let res = await fetch('/api/hotels', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(hotel)
			});
			let data = await res.json();
			if (data.id) {
				hotel = data as Hotel;
				addToast('success', $t('adventures.adventure_created'));
				dispatch('save', hotel);
			} else {
				console.error(data);
				addToast('error', $t('adventures.adventure_create_error'));
			}
		} else {
			let res = await fetch(`/api/hotels/${hotel.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(hotel)
			});
			let data = await res.json();
			if (data.id) {
				hotel = data as Hotel;
				addToast('success', $t('adventures.adventure_updated'));
				dispatch('save', hotel);
			} else {
				addToast('error', $t('adventures.adventure_update_error'));
			}
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

				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" checked />
					<div class="collapse-title text-xl font-medium">
						{$t('adventures.location_information')}
					</div>

					<div class="collapse-content"></div>
				</div>

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
