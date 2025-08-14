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
	import ImageDropdown from './ImageDropdown.svelte';
	import AttachmentDropdown from './AttachmentDropdown.svelte';

	const dispatch = createEventDispatcher();

	export let collection: Collection;
	export let lodgingToEdit: Lodging | null = null;

	let imageDropdownRef: any;
	let attachmentDropdownRef: any;

	// when this is true the image and attachment sections will create their upload requests
	let isImagesUploading: boolean = false;
	let isAttachmentsUploading: boolean = false;

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
			images: lodgingToEdit?.images || [],
			attachments: lodgingToEdit?.attachments || []
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

		try {
			// Create or update lodging first
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

				// Now handle image uploads if there are any pending
				if (imageDropdownRef?.hasImagesToUpload()) {
					isImagesUploading = true;

					// Wait for image upload to complete
					await waitForUploadComplete();
				}

				// Similarly handle attachments if needed
				if (attachmentDropdownRef?.hasAttachmentsToUpload()) {
					isAttachmentsUploading = true;

					// Wait for attachment upload to complete
					await waitForAttachmentUploadComplete();
				}

				dispatch('save', lodging);
			} else {
				const errorMessage =
					lodging.id === ''
						? 'adventures.adventure_create_error'
						: 'adventures.adventure_update_error';
				addToast('error', $t(errorMessage));
			}
		} catch (error) {
			console.error('Error saving lodging:', error);
			addToast('error', $t('adventures.lodging_save_error'));
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
										<option disabled selected>{$t('transportation.select_type')}</option>
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
										placeholder={$t('transportation.enter_link')}
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
				<ImageDropdown
					bind:this={imageDropdownRef}
					bind:object={lodging}
					objectType="lodging"
					bind:isImagesUploading
				/>

				<!-- Attachments Section -->
				<AttachmentDropdown
					bind:this={attachmentDropdownRef}
					bind:object={lodging}
					objectType="lodging"
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
