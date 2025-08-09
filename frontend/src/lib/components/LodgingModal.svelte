<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import type { Collection, Lodging } from '$lib/types';
	import LocationDropdown from './LocationDropdown.svelte';
	import DateRangeCollapse from './DateRangeCollapse.svelte';
	import { isAllDay } from '$lib';
	import { deserialize } from '$app/forms';
	// @ts-ignore
	import { DateTime } from 'luxon';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let lodgingToEdit: Lodging | null = null;

	let imageInput: HTMLInputElement;
	let imageFiles: File[] = [];

	let modal: HTMLDialogElement;
	let lodging: Lodging = { ...initializeLodging(lodgingToEdit) };
	let fullStartDate: string = '';
	let fullEndDate: string = '';

	let lodgingTimezone: string | undefined = lodging.timezone ?? undefined;

	// Initialize hotel with values from lodgingToEdit or default values
	function initializeLodging(lodgingToEdit: Lodging | null): Lodging {
		return {
			id: lodgingToEdit?.id || '',
			user: lodgingToEdit?.user || '',
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
			timezone: lodgingToEdit?.timezone || '',
			images: lodgingToEdit?.images || []
		};
	}

	function handleImageChange(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target?.files) {
			if (!lodging.id) {
				imageFiles = Array.from(target.files);
				console.log('Images ready for deferred upload:', imageFiles);
			} else {
				imageFiles = Array.from(target.files);
				for (const file of imageFiles) {
					uploadImage(file);
				}
			}
		}
	}

	async function uploadImage(file: File) {
		let formData = new FormData();
		formData.append('image', file);
		formData.append('object_id', lodging.id);
		formData.append('content_type', 'lodging');

		let res = await fetch(`/locations?/image`, {
			method: 'POST',
			body: formData
		});
		if (res.ok) {
			let newData = deserialize(await res.text()) as { data: { id: string; image: string } };
			let newImage = {
				id: newData.data.id,
				image: newData.data.image,
				is_primary: false,
				immich_id: null
			};
			lodging.images = [...(lodging.images || []), newImage];
			addToast('success', $t('adventures.image_upload_success'));
		} else {
			addToast('error', $t('adventures.image_upload_error'));
		}
	}

	async function removeImage(id: string) {
		let res = await fetch(`/api/images/${id}/image_delete`, {
			method: 'POST'
		});
		if (res.status === 204) {
			lodging.images = lodging.images.filter((image) => image.id !== id);
			addToast('success', $t('adventures.image_removed_success'));
		} else {
			addToast('error', $t('adventures.image_removed_error'));
		}
	}

	async function makePrimaryImage(image_id: string) {
		let res = await fetch(`/api/images/${image_id}/toggle_primary`, {
			method: 'POST'
		});
		if (res.ok) {
			lodging.images = lodging.images.map((image) => {
				if (image.id === image_id) {
					image.is_primary = true;
				} else {
					image.is_primary = false;
				}
				return image;
			});
		} else {
			console.error('Error in makePrimaryImage:', res);
		}
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

		// Auto-set end date if missing but start date exists
		//  If check_out is not set, we will set it to the next day at 9:00 AM in the lodging's timezone if it is a timed event. If it is an all-day event, we will set it to the next day at UTC 00:00:00.
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

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
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
								d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
							/>
						</svg>
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{lodgingToEdit ? $t('lodging.edit_lodging') : $t('lodging.new_lodging')}
						</h1>
						<p class="text-sm text-base-content/60">
							{lodgingToEdit
								? $t('lodging.update_lodging_details')
								: $t('lodging.create_new_lodging')}
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
										bind:value={lodging.name}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('lodging.enter_lodging_name')}
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
										bind:value={lodging.type}
									>
										<option disabled selected>{$t('lodging.select_type')}</option>
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
										bind:value={lodging.rating}
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
												checked={Number.isNaN(lodging.rating)}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (lodging.rating = 1)}
												checked={lodging.rating === 1}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (lodging.rating = 2)}
												checked={lodging.rating === 2}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (lodging.rating = 3)}
												checked={lodging.rating === 3}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (lodging.rating = 4)}
												checked={lodging.rating === 4}
											/>
											<input
												type="radio"
												name="rating-2"
												class="mask mask-star-2 bg-warning"
												on:click={() => (lodging.rating = 5)}
												checked={lodging.rating === 5}
											/>
										</div>
										{#if lodging.rating}
											<button
												type="button"
												class="btn btn-error btn-sm"
												on:click={() => (lodging.rating = NaN)}
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
										bind:value={lodging.link}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('lodging.enter_link')}
									/>
								</div>

								<!-- Description Field -->
								<div class="form-control">
									<label class="label" for="description">
										<span class="label-text font-medium">{$t('adventures.description')}</span>
									</label>
									<div class="bg-base-100/80 border border-base-300 rounded-xl p-2">
										<MarkdownEditor bind:text={lodging.description} editor_height={'h-32'} />
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Lodging Information Section -->
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
										d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
									/>
								</svg>
							</div>
							{$t('adventures.lodging_information')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6 space-y-3">
						<!-- Dual Column Layout -->
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
							<!-- Left Column -->
							<div class="space-y-4">
								<!-- Reservation Number -->
								<div class="form-control">
									<label class="label" for="reservation_number">
										<span class="label-text font-medium">{$t('lodging.reservation_number')}</span>
									</label>
									<input
										type="text"
										id="reservation_number"
										name="reservation_number"
										bind:value={lodging.reservation_number}
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('lodging.enter_reservation_number')}
									/>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<!-- Price -->
								<div class="form-control">
									<label class="label" for="price">
										<span class="label-text font-medium">{$t('adventures.price')}</span>
									</label>
									<input
										type="number"
										id="price"
										name="price"
										bind:value={lodging.price}
										step="0.01"
										class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
										placeholder={$t('lodging.enter_price')}
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Date Range Section -->
				<DateRangeCollapse
					type="lodging"
					bind:utcStartDate={lodging.check_in}
					bind:utcEndDate={lodging.check_out}
					bind:selectedStartTimezone={lodgingTimezone}
					{collection}
				/>

				<!-- Location Information Section -->
				<LocationDropdown bind:item={lodging} />

				<!-- Images Section -->
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
										d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
							</div>
							{$t('adventures.images')}
						</div>
					</div>
					<div class="collapse-content bg-base-100/50 pt-4 p-6">
						<div class="form-control">
							<label class="label" for="image">
								<span class="label-text font-medium">{$t('adventures.upload_image')}</span>
							</label>
							<input
								type="file"
								id="image"
								name="image"
								accept="image/*"
								multiple
								bind:this={imageInput}
								on:change={handleImageChange}
								class="file-input file-input-bordered file-input-primary w-full bg-base-100/80 focus:bg-base-100"
							/>
						</div>
						<p class="text-sm text-base-content/60 mt-2">
							{$t('adventures.image_upload_desc')}
						</p>
						{#if imageFiles.length > 0 && !lodging.id}
							<div class="mt-4">
								<h4 class="font-semibold text-base-content mb-2">
									{$t('adventures.selected_images')}
								</h4>
								<ul class="list-disc pl-5 space-y-1">
									{#each imageFiles as file}
										<li>{file.name} ({Math.round(file.size / 1024)} KB)</li>
									{/each}
								</ul>
							</div>
						{/if}
						{#if lodging.id}
							<div class="divider my-6"></div>

							<!-- Current Images -->
							<div class="space-y-4">
								<h4 class="font-semibold text-lg">{$t('adventures.my_images')}</h4>

								{#if lodging.images && lodging.images.length > 0}
									<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
										{#each lodging.images as image}
											<div class="relative group">
												<div class="aspect-square overflow-hidden rounded-lg bg-base-300">
													<img
														src={image.image}
														alt={image.id}
														class="w-full h-full object-cover transition-transform group-hover:scale-105"
													/>
												</div>

												<!-- Image Controls -->
												<div
													class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2"
												>
													{#if !image.is_primary}
														<button
															type="button"
															class="btn btn-success btn-sm"
															on:click={() => makePrimaryImage(image.id)}
															title="Make Primary"
														>
															<svg
																class="h-4 w-4"
																fill="none"
																stroke="currentColor"
																viewBox="0 0 24 24"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	stroke-width="2"
																	d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
																></path>
															</svg>
														</button>
													{/if}

													<button
														type="button"
														class="btn btn-error btn-sm"
														on:click={() => removeImage(image.id)}
														title="Remove"
													>
														✕
													</button>
												</div>

												<!-- Primary Badge -->
												{#if image.is_primary}
													<div
														class="absolute top-2 left-2 bg-warning text-warning-content rounded-full p-1"
													>
														<svg
															class="h-4 w-4"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M5 3l14 9-14 9V3z"
															></path>
														</svg>
													</div>
												{/if}
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-center py-8">
										<div class="text-base-content/60 text-lg mb-2">
											{$t('adventures.no_images')}
										</div>
										<p class="text-sm text-base-content/40">Upload images to get started</p>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				</div>

				<!-- Form Actions -->
				<div class="flex justify-end gap-3 mt-8 pt-6 border-t border-base-300">
					<button type="button" class="btn btn-ghost" on:click={close}>
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
