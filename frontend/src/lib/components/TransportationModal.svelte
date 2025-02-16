<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Collection, Transportation } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	import MarkdownEditor from './MarkdownEditor.svelte';
	import { appVersion } from '$lib/config';
	import { DefaultMarker, MapLibre } from 'svelte-maplibre';

	export let collection: Collection;
	export let transportationToEdit: Transportation | null = null;

	let constrainDates: boolean = false;

	function toLocalDatetime(value: string | null): string {
		if (!value) return '';
		const date = new Date(value);
		return date.toISOString().slice(0, 16); // Format: YYYY-MM-DDTHH:mm
	}

	let transportation: Transportation = {
		id: transportationToEdit?.id || '',
		type: transportationToEdit?.type || '',
		name: transportationToEdit?.name || '',
		description: transportationToEdit?.description || '',
		date: transportationToEdit?.date ? toLocalDatetime(transportationToEdit.date) : null,
		end_date: transportationToEdit?.end_date
			? toLocalDatetime(transportationToEdit.end_date)
			: null,
		rating: transportationToEdit?.rating || 0,
		link: transportationToEdit?.link || '',
		flight_number: transportationToEdit?.flight_number || '',
		from_location: transportationToEdit?.from_location || '',
		to_location: transportationToEdit?.to_location || '',
		user_id: transportationToEdit?.user_id || '',
		is_public: transportationToEdit?.is_public || false,
		collection: transportationToEdit?.collection || collection.id,
		created_at: transportationToEdit?.created_at || '',
		updated_at: transportationToEdit?.updated_at || '',
		origin_latitude: transportationToEdit?.origin_latitude || NaN,
		origin_longitude: transportationToEdit?.origin_longitude || NaN,
		destination_latitude: transportationToEdit?.destination_latitude || NaN,
		destination_longitude: transportationToEdit?.destination_longitude || NaN
	};

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	let starting_airport: string = '';
	let ending_airport: string = '';

	if (collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
	}

	$: {
		if (!transportation.rating) {
			transportation.rating = NaN;
		}
	}

	console.log(transportation);

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

	async function geocode(e: Event | null) {
		if (e) {
			e.preventDefault();
		}

		const fetchLocation = async (query: string) => {
			let res = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=jsonv2`, {
				headers: {
					'User-Agent': `AdventureLog / ${appVersion} `
				}
			});
			let data = await res.json();
			return data;
		};

		let startingData = null;
		let endingData = null;

		if (transportation.type == 'plane') {
			if (!starting_airport || !ending_airport) {
				alert($t('adventures.no_location'));
				return;
			}
			startingData = await fetchLocation(starting_airport + ' Airport');
			endingData = await fetchLocation(ending_airport + ' Airport');
		} else {
			if (!transportation.from_location || !transportation.to_location) {
				alert($t('adventures.no_location'));
				return;
			}
			startingData = await fetchLocation(transportation?.from_location || '');
			endingData = await fetchLocation(transportation?.to_location || '');
		}

		if (startingData.length === 0 || endingData.length === 0) {
			alert($t('adventures.no_location_found'));
			return;
		}

		if (transportation.type == 'plane') {
			transportation.from_location =
				startingData[0].name + ' (' + starting_airport.toUpperCase() + ')';
			transportation.to_location = endingData[0].name + ' (' + ending_airport.toUpperCase() + ')';
		} else {
			transportation.from_location = startingData[0].display_name;
			transportation.to_location = endingData[0].display_name;
		}
		transportation.origin_latitude = startingData[0].lat;
		transportation.origin_longitude = startingData[0].lon;
		transportation.destination_latitude = endingData[0].lat;
		transportation.destination_longitude = endingData[0].lon;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		console.log(transportation);

		// If the user has entered airport codes, but not location names, fetch the location names
		if (
			starting_airport &&
			ending_airport &&
			(!transportation.from_location || !transportation.to_location)
		) {
			transportation.from_location = starting_airport;
			transportation.to_location = ending_airport;
		}

		// Round coordinates to 6 decimal places
		if (transportation.origin_latitude) {
			transportation.origin_latitude = Math.round(transportation.origin_latitude * 1e6) / 1e6;
		}
		if (transportation.origin_longitude) {
			transportation.origin_longitude = Math.round(transportation.origin_longitude * 1e6) / 1e6;
		}
		if (transportation.destination_latitude) {
			transportation.destination_latitude =
				Math.round(transportation.destination_latitude * 1e6) / 1e6;
		}
		if (transportation.destination_longitude) {
			transportation.destination_longitude =
				Math.round(transportation.destination_longitude * 1e6) / 1e6;
		}

		if (transportation.end_date && !transportation.date) {
			transportation.date = null;
			transportation.end_date = null;
		}

		if (transportation.date && !transportation.end_date) {
			transportation.end_date = transportation.date;
		}

		if (
			transportation.date &&
			transportation.end_date &&
			transportation.date > transportation.end_date
		) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		if (transportation.type != 'plane') {
			transportation.flight_number = '';
		}

		if (transportation.id === '') {
			let res = await fetch('/api/transportations', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(transportation)
			});
			let data = await res.json();
			if (data.id) {
				transportation = data as Transportation;
				addToast('success', $t('adventures.adventure_created'));
				dispatch('save', transportation);
			} else {
				console.error(data);
				addToast('error', $t('adventures.adventure_create_error'));
			}
		} else {
			let res = await fetch(`/api/transportations/${transportation.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(transportation)
			});
			let data = await res.json();
			if (data.id) {
				transportation = data as Transportation;
				addToast('success', $t('adventures.adventure_updated'));
				dispatch('save', transportation);
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
			{transportationToEdit
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
								bind:value={transportation.name}
								class="input input-bordered w-full"
								required
							/>
						</div>
						<!-- Type selection -->
						<div>
							<label for="type">
								{$t('transportation.type')}<span class="text-red-500">*</span>
							</label>
							<div>
								<select
									class="select select-bordered w-full max-w-xs"
									name="type"
									id="type"
									bind:value={transportation.type}
								>
									<option disabled selected>{$t('transportation.type')}</option>
									<option value="car">{$t('transportation.modes.car')}</option>
									<option value="plane">{$t('transportation.modes.plane')}</option>
									<option value="train">{$t('transportation.modes.train')}</option>
									<option value="bus">{$t('transportation.modes.bus')}</option>
									<option value="boat">{$t('transportation.modes.boat')}</option>
									<option value="bike">{$t('transportation.modes.bike')}</option>
									<option value="walking">{$t('transportation.modes.walking')}</option>
									<option value="other">{$t('transportation.modes.other')}</option>
								</select>
							</div>
						</div>
						<!-- Description -->
						<div>
							<label for="description">{$t('adventures.description')}</label><br />
							<MarkdownEditor bind:text={transportation.description} editor_height={'h-32'} />
						</div>
						<!-- Rating -->
						<div>
							<label for="rating">{$t('adventures.rating')}</label><br />
							<input
								type="number"
								min="0"
								max="5"
								hidden
								bind:value={transportation.rating}
								id="rating"
								name="rating"
								class="input input-bordered w-full max-w-xs mt-1"
							/>
							<div class="rating -ml-3 mt-1">
								<input
									type="radio"
									name="rating-2"
									class="rating-hidden"
									checked={Number.isNaN(transportation.rating)}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (transportation.rating = 1)}
									checked={transportation.rating === 1}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (transportation.rating = 2)}
									checked={transportation.rating === 2}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (transportation.rating = 3)}
									checked={transportation.rating === 3}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (transportation.rating = 4)}
									checked={transportation.rating === 4}
								/>
								<input
									type="radio"
									name="rating-2"
									class="mask mask-star-2 bg-orange-400"
									on:click={() => (transportation.rating = 5)}
									checked={transportation.rating === 5}
								/>
								{#if transportation.rating}
									<button
										type="button"
										class="btn btn-sm btn-error ml-2"
										on:click={() => (transportation.rating = NaN)}
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
								bind:value={transportation.link}
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
									bind:value={transportation.date}
									min={constrainDates ? fullStartDate : ''}
									max={constrainDates ? fullEndDate : ''}
									class="input input-bordered w-full max-w-xs mt-1"
								/>
							</div>
						</div>
						<!-- End Date -->
						{#if transportation.date}
							<div>
								<label for="end_date">
									{$t('adventures.end_date')}
								</label>
								<div>
									<input
										type="datetime-local"
										id="end_date"
										name="end_date"
										min={constrainDates ? transportation.date : ''}
										max={constrainDates ? fullEndDate : ''}
										bind:value={transportation.end_date}
										class="input input-bordered w-full max-w-xs mt-1"
									/>
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Flight Information -->

				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" checked />
					<div class="collapse-title text-xl font-medium">
						{#if transportation?.type == 'plane'}
							{$t('adventures.flight_information')}
						{:else}
							{$t('adventures.location_information')}
						{/if}
					</div>

					<div class="collapse-content">
						{#if transportation?.type == 'plane'}
							<!-- Flight Number -->
							<div class="mb-4">
								<label for="flight_number" class="label">
									<span class="label-text">{$t('transportation.flight_number')}</span>
								</label>
								<input
									type="text"
									id="flight_number"
									name="flight_number"
									bind:value={transportation.flight_number}
									class="input input-bordered w-full"
								/>
							</div>

							<!-- Starting Airport -->
							{#if !transportation.from_location || !transportation.to_location}
								<div class="mb-4">
									<label for="starting_airport" class="label">
										<span class="label-text">{$t('adventures.starting_airport')}</span>
									</label>
									<input
										type="text"
										id="starting_airport"
										bind:value={starting_airport}
										name="starting_airport"
										class="input input-bordered w-full"
										placeholder="Enter starting airport code (e.g., JFK)"
									/>
									<label for="ending_airport" class="label">
										<span class="label-text">{$t('adventures.ending_airport')}</span>
									</label>
									<input
										type="text"
										id="ending_airport"
										bind:value={ending_airport}
										name="ending_airport"
										class="input input-bordered w-full"
										placeholder="Enter ending airport code (e.g., LAX)"
									/>
									<button type="button" class="btn btn-primary mt-2" on:click={geocode}>
										Fetch Location Information
									</button>
								</div>
							{/if}

							{#if transportation.from_location && transportation.to_location}
								<!-- From Location -->
								<div class="mb-4">
									<label for="from_location" class="label">
										<span class="label-text">{$t('transportation.from_location')}</span>
									</label>
									<input
										type="text"
										id="from_location"
										name="from_location"
										bind:value={transportation.from_location}
										class="input input-bordered w-full"
									/>
								</div>
								<!-- To Location -->
								<div class="mb-4">
									<label for="to_location" class="label">
										<span class="label-text">{$t('transportation.to_location')}</span>
									</label>
									<input
										type="text"
										id="to_location"
										name="to_location"
										bind:value={transportation.to_location}
										class="input input-bordered w-full"
									/>
								</div>
							{/if}
						{:else}
							<!-- From Location -->
							<div class="mb-4">
								<label for="from_location" class="label">
									<span class="label-text">{$t('transportation.from_location')}</span>
								</label>
								<input
									type="text"
									id="from_location"
									name="from_location"
									bind:value={transportation.from_location}
									class="input input-bordered w-full"
								/>
							</div>
							<!-- To Location -->
							<div class="mb-4">
								<label for="to_location" class="label">
									<span class="label-text">{$t('transportation.to_location')}</span>
								</label>
								<input
									type="text"
									id="to_location"
									name="to_location"
									bind:value={transportation.to_location}
									class="input input-bordered w-full"
								/>
							</div>
							<button type="button" class="btn btn-primary mt-2" on:click={geocode}>
								Fetch Location Information
							</button>
						{/if}
						<div class="mt-4">
							<MapLibre
								style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
								class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full rounded-lg"
								standardControls
							>
								<!-- MapEvents gives you access to map events even from other components inside the map,
where you might not have access to the top-level `MapLibre` component. In this case
it would also work to just use on:click on the MapLibre component itself. -->
								<!-- @ts-ignore -->

								{#if transportation.origin_latitude && transportation.origin_longitude}
									<DefaultMarker
										lngLat={[transportation.origin_longitude, transportation.origin_latitude]}
									/>
								{/if}
								{#if transportation.destination_latitude && transportation.destination_longitude}
									<DefaultMarker
										lngLat={[
											transportation.destination_longitude,
											transportation.destination_latitude
										]}
									/>
								{/if}
							</MapLibre>
							<!-- button to clear to and from location -->
						</div>
						{#if transportation.from_location || transportation.to_location}
							<button
								type="button"
								class="btn btn-error btn-sm mt-2"
								on:click={() => {
									transportation.from_location = '';
									transportation.to_location = '';
									starting_airport = '';
									ending_airport = '';
									transportation.origin_latitude = NaN;
									transportation.origin_longitude = NaN;
									transportation.destination_latitude = NaN;
									transportation.destination_longitude = NaN;
								}}
							>
								{$t('adventures.clear_location')}
							</button>
						{/if}
					</div>
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
