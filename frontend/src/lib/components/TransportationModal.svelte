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
	import DateRangeCollapse from './DateRangeCollapse.svelte';
	import { getBasemapUrl } from '$lib';

	import ImageDropdown from './ImageDropdown.svelte';
	import AttachmentDropdown from './AttachmentDropdown.svelte';

	export let collection: Collection;
	export let transportationToEdit: Transportation | null = null;

	let imageDropdownRef: any;
	let attachmentDropdownRef: any;

	// when this is true the image and attachment sections will create their upload requests
	let isImagesUploading: boolean = false;
	let isAttachmentsUploading: boolean = false;

	// Initialize transportation object
	let transportation: Transportation = {
		id: transportationToEdit?.id || '',
		type: transportationToEdit?.type || '',
		name: transportationToEdit?.name || '',
		description: transportationToEdit?.description || '',
		date: transportationToEdit?.date || null,
		end_date: transportationToEdit?.end_date || null,
		rating: transportationToEdit?.rating || 0,
		link: transportationToEdit?.link || '',
		flight_number: transportationToEdit?.flight_number || '',
		from_location: transportationToEdit?.from_location || '',
		to_location: transportationToEdit?.to_location || '',
		user: transportationToEdit?.user || '',
		is_public: transportationToEdit?.is_public || false,
		collection: transportationToEdit?.collection || collection.id,
		created_at: transportationToEdit?.created_at || '',
		updated_at: transportationToEdit?.updated_at || '',
		origin_latitude: transportationToEdit?.origin_latitude || NaN,
		origin_longitude: transportationToEdit?.origin_longitude || NaN,
		destination_latitude: transportationToEdit?.destination_latitude || NaN,
		destination_longitude: transportationToEdit?.destination_longitude || NaN,
		start_timezone: transportationToEdit?.start_timezone || '',
		end_timezone: transportationToEdit?.end_timezone || '',
		distance: null,
		images: transportationToEdit?.images || [],
		attachments: transportationToEdit?.attachments || []
	};

	let startTimezone: string | undefined = transportation.start_timezone ?? undefined;
	let endTimezone: string | undefined = transportation.end_timezone ?? undefined;

	// Later, you should manually sync these back to `transportation` if needed
	$: transportation.start_timezone = startTimezone ?? '';
	$: transportation.end_timezone = endTimezone ?? '';

	let starting_airport: string = '';
	let ending_airport: string = '';

	$: {
		if (!transportation.rating) {
			transportation.rating = NaN;
		}
	}

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
		// Geocoding logic unchanged
		if (e) {
			e.preventDefault();
		}

		const fetchLocation = async (query: string) => {
			let res = await fetch(`/api/reverse-geocode/search/?query=${query}`, {
				headers: {
					'User-Agent': `AdventureLog / ${appVersion} `
				}
			});
			console.log(query);
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

		if (transportation.date && !transportation.end_date) {
			transportation.end_date = transportation.date;
		}

		if (!transportation.type) {
			transportation.type = 'other';
		}

		// Use the stored UTC dates for submission
		const submissionData = {
			...transportation
		};

		if (transportation.type != 'plane') {
			submissionData.flight_number = '';
		}

		if (submissionData.id === '') {
			let res = await fetch('/api/transportations', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(submissionData)
			});
			let data = await res.json();
			if (data.id) {
				transportation = data as Transportation;

				addToast('success', $t('adventures.location_created'));
				// Handle image uploads after transportation is created

				// Now handle image uploads if there are any pending
				if (imageDropdownRef?.hasImagesToUpload()) {
					console.log('Triggering image upload...');
					isImagesUploading = true;

					// Wait for image upload to complete
					await waitForUploadComplete();
				}

				// Similarly handle attachments if needed
				if (attachmentDropdownRef?.hasAttachmentsToUpload()) {
					console.log('Triggering attachment upload...');
					isAttachmentsUploading = true;

					// Wait for attachment upload to complete
					await waitForAttachmentUploadComplete();
				}

				dispatch('save', transportation);
			} else {
				console.error(data);
				addToast('error', $t('adventures.location_create_error'));
			}
		} else {
			let res = await fetch(`/api/transportations/${transportation.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(submissionData)
			});
			let data = await res.json();
			if (data.id) {
				transportation = data as Transportation;

				addToast('success', $t('adventures.location_updated'));
				dispatch('save', transportation);
			} else {
				addToast('error', $t('adventures.location_update_error'));
			}
		}
	}

	// Helper function to wait for image upload completion
	async function waitForUploadComplete(): Promise<void> {
		return new Promise((resolve) => {
			const checkUpload = () => {
				if (!isImagesUploading) {
					resolve();
				} else {
					setTimeout(checkUpload, 100);
				}
			};
			checkUpload();
		});
	}

	// Helper function to wait for attachment upload completion
	async function waitForAttachmentUploadComplete(): Promise<void> {
		return new Promise((resolve) => {
			const checkUpload = () => {
				if (!isAttachmentsUploading) {
					resolve();
				} else {
					setTimeout(checkUpload, 100);
				}
			};
			checkUpload();
		});
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section - Following adventurelog pattern -->
		<div
			class="top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<svg class="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 9l3 3m0 0l-3 3m3-3H8m13 0a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{transportationToEdit
								? $t('transportation.edit_transportation')
								: $t('transportation.new_transportation')}
						</h1>
						<p class="text-sm text-base-content/60">
							{transportationToEdit
								? $t('transportation.update_transportation_details')
								: $t('transportation.create_new_transportation')}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			<form method="post" style="width: 100%;" on:submit={handleSubmit}>
				<!-- Basic Information Section -->
				<div
					class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
				>
					<input type="checkbox" checked />
					<div
						class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
					>
						<div class="flex items-center gap-3">
							<div class="p-2 bg-primary/10 rounded-lg">
								<svg
									class="w-5 h-5 text-primary"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
									/>
								</svg>
							</div>
							{$t('adventures.basic_information')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-3">
						<!-- Dual Column Layout for Large Screens -->
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Name Field -->
								<div class="form-control">
									<label class="label" for="name">
										<span class="label-text font-medium"
											>{$t('adventures.name')}<span class="text-error ml-1">*</span></span
										>
									</label>
									<input
										type="text"
										id="name"
										name="name"
										bind:value={transportation.name}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('transportation.enter_transportation_name')}
										required
									/>
								</div>

								<!-- Type Selection -->
								<div class="form-control">
									<label class="label" for="type">
										<span class="label-text font-medium"
											>{$t('transportation.type')}<span class="text-error ml-1">*</span></span
										>
									</label>
									<select
										class="select select-bordered w-full bg-base-100/80 focus:bg-base-100"
										name="type"
										id="type"
										bind:value={transportation.type}
									>
										<option disabled selected>{$t('transportation.select_type')}</option>
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

								<!-- Rating Field -->
								<div class="form-control">
									<label class="label" for="rating">
										<span class="label-text font-medium">{$t('adventures.rating')}</span>
									</label>
									<input
										type="number"
										min="0"
										max="5"
										hidden
										bind:value={transportation.rating}
										id="rating"
										name="rating"
										class="input input-bordered w-full max-w-xs"
									/>
									<div
										class="flex items-center gap-4 p-4 bg-base-100/80 border border-base-300 rounded-xl"
									>
										<div class="rating">
											<input
												type="radio"
												name="rating-2"
												class="rating-hidden"
												checked={Number.isNaN(transportation.rating)}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (transportation.rating = 1)}
												checked={transportation.rating === 1}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (transportation.rating = 2)}
												checked={transportation.rating === 2}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (transportation.rating = 3)}
												checked={transportation.rating === 3}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (transportation.rating = 4)}
												checked={transportation.rating === 4}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (transportation.rating = 5)}
												checked={transportation.rating === 5}
											/>
										</div>
										{#if transportation.rating}
											<button
												type="button"
												class="btn btn-error btn-sm"
												on:click={() => (transportation.rating = NaN)}
											>
												{$t('adventures.remove')}
											</button>
										{/if}
									</div>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<!-- Link Field -->
								<div class="form-control">
									<label class="label" for="link">
										<span class="label-text font-medium">{$t('adventures.link')}</span>
									</label>
									<input
										type="url"
										id="link"
										name="link"
										bind:value={transportation.link}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('transportation.enter_link')}
									/>
								</div>

								<!-- Description Field -->
								<div class="form-control">
									<label class="label" for="description">
										<span class="label-text font-medium">{$t('adventures.description')}</span>
									</label>
									<div class="bg-base-100/80 border border-base-300 rounded-xl p-2">
										<MarkdownEditor bind:text={transportation.description} editor_height={'h-32'} />
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Date Range Section -->

				<DateRangeCollapse
					type="transportation"
					bind:utcStartDate={transportation.date}
					bind:utcEndDate={transportation.end_date}
					bind:selectedStartTimezone={startTimezone}
					bind:selectedEndTimezone={endTimezone}
					{collection}
				/>

				<!-- Location/Flight Information Section -->
				<div
					class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
				>
					<input type="checkbox" checked />
					<div
						class="collapse-title text-xl font-semibold bg-gradient-to-r from-primary/10 to-primary/5"
					>
						<div class="flex items-center gap-3">
							<div class="p-2 bg-primary/10 rounded-lg">
								<svg
									class="w-5 h-5 text-primary"
									fill="none"
									stroke="currentColor"
									viewBox="0 0 24 24"
								>
									{#if transportation?.type == 'plane'}
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
										/>
									{:else}
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
										/>
									{/if}
								</svg>
							</div>
							{#if transportation?.type == 'plane'}
								{$t('adventures.flight_information')}
							{:else}
								{$t('adventures.location_information')}
							{/if}
						</div>
					</div>

					<div class="collapse-content bg-base-100/50 pt-4 p-6">
						{#if transportation?.type == 'plane'}
							<!-- Flight-specific fields -->
							<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
								<!-- Flight Number -->
								<div class="form-control">
									<label class="label" for="flight_number">
										<span class="label-text font-medium">{$t('transportation.flight_number')}</span>
									</label>
									<input
										type="text"
										id="flight_number"
										name="flight_number"
										bind:value={transportation.flight_number}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('transportation.enter_flight_number')}
									/>
								</div>
							</div>

							<!-- Airport Fields (if locations not set) -->
							{#if !transportation.from_location || !transportation.to_location}
								<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
									<div class="form-control">
										<label class="label" for="starting_airport">
											<span class="label-text font-medium">{$t('adventures.starting_airport')}</span
											>
										</label>
										<input
											type="text"
											id="starting_airport"
											bind:value={starting_airport}
											name="starting_airport"
											class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
											placeholder={$t('transportation.starting_airport_desc')}
										/>
									</div>

									<div class="form-control">
										<label class="label" for="ending_airport">
											<span class="label-text font-medium">{$t('adventures.ending_airport')}</span>
										</label>
										<input
											type="text"
											id="ending_airport"
											bind:value={ending_airport}
											name="ending_airport"
											class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
											placeholder={$t('transportation.ending_airport_desc')}
										/>
									</div>
								</div>

								<div class="flex justify-start mb-6">
									<button type="button" class="btn btn-primary gap-2" on:click={geocode}>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
											/>
										</svg>
										{$t('transportation.fetch_location_information')}
									</button>
								</div>
							{/if}
						{/if}

						<!-- Location Fields (for all types or when flight locations are set) -->
						{#if transportation?.type != 'plane' || (transportation.from_location && transportation.to_location)}
							<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
								<!-- From Location -->
								<div class="form-control">
									<label class="label" for="from_location">
										<span class="label-text font-medium">{$t('transportation.from_location')}</span>
									</label>
									<input
										type="text"
										id="from_location"
										name="from_location"
										bind:value={transportation.from_location}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('transportation.enter_from_location')}
									/>
								</div>

								<!-- To Location -->
								<div class="form-control">
									<label class="label" for="to_location">
										<span class="label-text font-medium">{$t('transportation.to_location')}</span>
									</label>
									<input
										type="text"
										id="to_location"
										name="to_location"
										bind:value={transportation.to_location}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('transportation.enter_to_location')}
									/>
								</div>
							</div>

							{#if transportation?.type != 'plane'}
								<div class="flex justify-start mb-6">
									<button type="button" class="btn btn-primary gap-2" on:click={geocode}>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
											/>
										</svg>
										{$t('transportation.fetch_location_information')}
									</button>
								</div>
							{/if}
						{/if}

						<!-- Map Section -->
						<div class="bg-base-100/80 border border-base-300 rounded-xl p-4 mb-6">
							<div class="mb-4">
								<h4 class="font-semibold text-base-content flex items-center gap-2">
									<svg
										class="w-5 h-5 text-primary"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m0 0L9 7"
										/>
									</svg>
									{$t('adventures.route_map')}
								</h4>
							</div>
							<MapLibre
								style={getBasemapUrl()}
								class="relative aspect-[9/16] max-h-[70vh] w-full sm:aspect-video sm:max-h-full rounded-lg"
								standardControls
							>
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
						</div>

						<!-- Clear Location Button -->
						{#if transportation.from_location || transportation.to_location}
							<div class="flex justify-start">
								<button
									type="button"
									class="btn btn-error btn-sm gap-2"
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
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
										/>
									</svg>
									{$t('adventures.clear_location')}
								</button>
							</div>
						{/if}
					</div>
				</div>

				<!-- Images Section -->
				<ImageDropdown
					bind:this={imageDropdownRef}
					bind:object={transportation}
					objectType="transportation"
					bind:isImagesUploading
				/>

				<!-- Attachments Section -->
				<AttachmentDropdown
					bind:this={attachmentDropdownRef}
					bind:object={transportation}
					objectType="transportation"
					bind:isAttachmentsUploading
				/>

				<!-- Form Actions -->
				<div class="flex justify-end gap-3 mt-8 pt-6 border-t border-base-300">
					<button type="button" class="btn btn-neutral-200" on:click={close}>
						{$t('about.close')}
					</button>
					<button type="submit" class="btn btn-primary gap-2">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
							/>
						</svg>
						{$t('notes.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
