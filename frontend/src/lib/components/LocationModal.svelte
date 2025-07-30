<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Location, Attachment, Category, Collection, User } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { deserialize } from '$app/forms';
	import { t } from 'svelte-i18n';
	export let collection: Collection | null = null;
	export let user: User | null = null;

	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let fullStartDateOnly: string = '';
	let fullEndDateOnly: string = '';

	// Set full start and end dates from collection
	if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
		fullStartDateOnly = collection.start_date;
		fullEndDateOnly = collection.end_date;
	}

	const dispatch = createEventDispatcher();

	let images: { id: string; image: string; is_primary: boolean; immich_id: string | null }[] = [];
	let warningMessage: string = '';

	let categories: Category[] = [];

	const allowedFileTypes = [
		'.pdf',
		'.doc',
		'.docx',
		'.xls',
		'.xlsx',
		'.ppt',
		'.pptx',
		'.txt',
		'.png',
		'.jpg',
		'.jpeg',
		'.gif',
		'.webp',
		'.mp4',
		'.mov',
		'.avi',
		'.mkv',
		'.mp3',
		'.wav',
		'.flac',
		'.ogg',
		'.m4a',
		'.wma',
		'.aac',
		'.opus',
		'.zip',
		'.rar',
		'.7z',
		'.tar',
		'.gz',
		'.bz2',
		'.xz',
		'.zst',
		'.lz4',
		'.lzma',
		'.lzo',
		'.z',
		'.tar.gz',
		'.tar.bz2',
		'.tar.xz',
		'.tar.zst',
		'.tar.lz4',
		'.tar.lzma',
		'.tar.lzo',
		'.tar.z',
		'.gpx',
		'.md'
	];

	export let initialLatLng: { lat: number; lng: number } | null = null; // Used to pass the location from the map selection to the modal

	let fileInput: HTMLInputElement;
	let immichIntegration: boolean = false;
	let copyImmichLocally: boolean = false;

	import ActivityComplete from './TagComplete.svelte';
	import CategoryDropdown from './CategoryDropdown.svelte';
	import { findFirstValue, isAllDay } from '$lib';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import ImmichSelect from './ImmichSelect.svelte';
	import Star from '~icons/mdi/star';
	import Crown from '~icons/mdi/crown';
	import AttachmentCard from './AttachmentCard.svelte';
	import LocationDropdown from './LocationDropdown.svelte';
	import DateRangeCollapse from './DateRangeCollapse.svelte';
	import UserCard from './UserCard.svelte';
	let modal: HTMLDialogElement;

	let wikiError: string = '';

	let location: Location = {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		tags: [],
		rating: NaN,
		is_public: false,
		latitude: NaN,
		longitude: NaN,
		location: null,
		images: [],
		user: null,
		category: {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user: ''
		},
		attachments: []
	};

	export let locationToEdit: Location | null = null;

	location = {
		id: locationToEdit?.id || '',
		name: locationToEdit?.name || '',
		link: locationToEdit?.link || null,
		description: locationToEdit?.description || null,
		tags: locationToEdit?.tags || [],
		rating: locationToEdit?.rating || NaN,
		is_public: locationToEdit?.is_public || false,
		latitude: locationToEdit?.latitude || NaN,
		longitude: locationToEdit?.longitude || NaN,
		location: locationToEdit?.location || null,
		images: locationToEdit?.images || [],
		user: locationToEdit?.user || null,
		visits: locationToEdit?.visits || [],
		is_visited: locationToEdit?.is_visited || false,
		category: locationToEdit?.category || {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user: ''
		},

		attachments: locationToEdit?.attachments || []
	};

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		modal.showModal();
		let categoryFetch = await fetch('/api/categories');
		if (categoryFetch.ok) {
			categories = await categoryFetch.json();
		} else {
			addToast('error', $t('adventures.category_fetch_error'));
		}
		// Check for Immich Integration
		let res = await fetch('/api/integrations/immich/');
		// If the response is not ok, we assume Immich integration is not available
		if (!res.ok && res.status !== 404) {
			addToast('error', $t('immich.integration_fetch_error'));
		} else {
			let data = await res.json();
			if (data.error) {
				immichIntegration = false;
			} else if (data.id) {
				immichIntegration = true;
				copyImmichLocally = data.copy_locally || false;
			} else {
				immichIntegration = false;
			}
		}
	});

	let url: string = '';
	let imageError: string = '';
	let wikiImageError: string = '';
	let triggerMarkVisted: boolean = false;

	let isLoading: boolean = false;

	images = location.images || [];
	$: {
		if (!location.rating) {
			location.rating = NaN;
		}
	}

	function deleteAttachment(event: CustomEvent<string>) {
		location.attachments = location.attachments.filter(
			(attachment) => attachment.id !== event.detail
		);
	}

	let attachmentName: string = '';
	let attachmentToEdit: Attachment | null = null;

	async function editAttachment() {
		if (attachmentToEdit) {
			let res = await fetch(`/api/attachments/${attachmentToEdit.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ name: attachmentToEdit.name })
			});
			if (res.ok) {
				let newAttachment = (await res.json()) as Attachment;
				location.attachments = location.attachments.map((attachment) => {
					if (attachment.id === newAttachment.id) {
						return newAttachment;
					}
					return attachment;
				});
				attachmentToEdit = null;
				addToast('success', $t('adventures.attachment_update_success'));
			} else {
				addToast('error', $t('adventures.attachment_update_error'));
			}
		}
	}

	let selectedFile: File | null = null;

	function handleFileChange(event: Event) {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length) {
			selectedFile = input.files[0];
		}
	}

	async function uploadAttachment(event: Event) {
		event.preventDefault();

		if (!selectedFile) {
			console.error('No files selected');
			return;
		}

		const file = selectedFile;

		const formData = new FormData();
		formData.append('file', file);
		formData.append('location', location.id);
		formData.append('name', attachmentName);

		try {
			const res = await fetch('/locations?/attachment', {
				method: 'POST',
				body: formData
			});

			if (res.ok) {
				const newData = deserialize(await res.text()) as { data: Attachment };
				location.attachments = [...location.attachments, newData.data];
				addToast('success', $t('adventures.attachment_upload_success'));
				attachmentName = '';
			} else {
				addToast('error', $t('adventures.attachment_upload_error'));
			}
		} catch (err) {
			console.error(err);
			addToast('error', $t('adventures.attachment_upload_error'));
		} finally {
			// Reset the file input for a new upload
			if (fileInput) {
				fileInput.value = '';
			}
		}
	}

	let imageSearch: string = location.name || '';

	async function removeImage(id: string) {
		let res = await fetch(`/api/images/${id}/image_delete`, {
			method: 'POST'
		});
		if (res.status === 204) {
			images = images.filter((image) => image.id !== id);
			location.images = images;
			addToast('success', $t('adventures.image_removed_success'));
		} else {
			addToast('error', $t('adventures.image_removed_error'));
		}
	}

	let isDetails: boolean = true;

	function saveAndClose() {
		dispatch('save', location);
		close();
	}

	async function makePrimaryImage(image_id: string) {
		let res = await fetch(`/api/images/${image_id}/toggle_primary`, {
			method: 'POST'
		});
		if (res.ok) {
			images = images.map((image) => {
				if (image.id === image_id) {
					image.is_primary = true;
				} else {
					image.is_primary = false;
				}
				return image;
			});
			location.images = images;
		} else {
			console.error('Error in makePrimaryImage:', res);
		}
	}

	async function handleMultipleFiles(event: Event) {
		const files = (event.target as HTMLInputElement).files;
		if (files) {
			for (const file of files) {
				await uploadImage(file);
			}
		}
	}

	async function uploadImage(file: File) {
		let formData = new FormData();
		formData.append('image', file);
		formData.append('object_id', location.id);
		formData.append('content_type', 'location');

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
			images = [...images, newImage];
			location.images = images;
			addToast('success', $t('adventures.image_upload_success'));
		} else {
			addToast('error', $t('adventures.image_upload_error'));
		}
	}

	async function fetchImage() {
		try {
			let res = await fetch(url);
			let data = await res.blob();
			if (!data) {
				imageError = $t('adventures.no_image_url');
				return;
			}
			let file = new File([data], 'image.jpg', { type: 'image/jpeg' });
			let formData = new FormData();
			formData.append('image', file);
			formData.append('adventure', location.id);

			await uploadImage(file);
			url = '';
		} catch (e) {
			imageError = $t('adventures.image_fetch_failed');
		}
	}

	async function fetchWikiImage() {
		let res = await fetch(`/api/generate/img/?name=${imageSearch}`);
		let data = await res.json();
		if (!res.ok) {
			wikiImageError = $t('adventures.image_fetch_failed');
			return;
		}
		if (data.source) {
			let imageUrl = data.source;
			let res = await fetch(imageUrl);
			let blob = await res.blob();
			let file = new File([blob], `${imageSearch}.jpg`, { type: 'image/jpeg' });
			wikiImageError = '';
			let formData = new FormData();
			formData.append('image', file);
			formData.append('location', location.id);
			let res2 = await fetch(`/locations?/image`, {
				method: 'POST',
				body: formData
			});
			if (res2.ok) {
				let newData = deserialize(await res2.text()) as { data: { id: string; image: string } };
				let newImage = {
					id: newData.data.id,
					image: newData.data.image,
					is_primary: false,
					immich_id: null
				};
				images = [...images, newImage];
				location.images = images;
				addToast('success', $t('adventures.image_upload_success'));
			} else {
				addToast('error', $t('adventures.image_upload_error'));
				wikiImageError = $t('adventures.wiki_image_error');
			}
		}
	}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function generateDesc() {
		let res = await fetch(`/api/generate/desc/?name=${location.name}`);
		let data = await res.json();
		if (data.extract?.length > 0) {
			location.description = data.extract;
			wikiError = '';
		} else {
			wikiError = $t('adventures.no_description_found');
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		triggerMarkVisted = true;
		isLoading = true;

		// if category icon is empty, set it to the default icon
		if (location.category?.icon == '' || location.category?.icon == null) {
			if (location.category) {
				location.category.icon = '🌍';
			}
		}

		if (location.id === '') {
			if (location.category?.display_name == '') {
				if (categories.some((category) => category.name === 'general')) {
					location.category = categories.find(
						(category) => category.name === 'general'
					) as Category;
				} else {
					location.category = {
						id: '',
						name: 'general',
						display_name: 'General',
						icon: '🌍',
						user: ''
					};
				}
			}

			// add this collection to the adventure
			if (collection && collection.id) {
				location.collections = [collection.id];
			}

			let res = await fetch('/api/locations', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(location)
			});
			let data = await res.json();
			if (data.id) {
				location = data as Location;
				isDetails = false;
				warningMessage = '';
				addToast('success', $t('adventures.location_created'));
			} else {
				warningMessage = findFirstValue(data) as string;
				console.error(data);
				addToast('error', $t('adventures.location_create_error'));
			}
		} else {
			let res = await fetch(`/api/locations/${location.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(location)
			});
			let data = await res.json();
			if (data.id) {
				location = data as Location;
				isDetails = false;
				warningMessage = '';
				addToast('success', $t('adventures.location_updated'));
			} else {
				warningMessage = Object.values(data)[0] as string;
				addToast('error', $t('adventures.location_update_error'));
			}
		}
		imageSearch = location.name;
		isLoading = false;
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
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
								d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{locationToEdit ? $t('adventures.edit_location') : $t('adventures.new_location')}
						</h1>
						<p class="text-sm text-base-content/60">
							{locationToEdit
								? $t('adventures.update_location_details')
								: $t('adventures.create_new_location')}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				{#if !location.id}
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
				{:else}
					<button class="btn btn-ghost btn-square" on:click={saveAndClose}>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
		</div>

		{#if location.id === '' || isDetails}
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
											bind:value={location.name}
											class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
											placeholder={$t('adventures.enter_location_name')}
											required
										/>
									</div>

									<!-- Category Field -->
									<div class="form-control">
										<label class="label" for="category">
											<span class="label-text font-medium"
												>{$t('adventures.category')}<span class="text-error ml-1">*</span></span
											>
										</label>
										{#if (user && user.uuid == location.user?.uuid) || !locationToEdit}
											<CategoryDropdown
												bind:categories
												bind:selected_category={location.category}
											/>
										{:else}
											<div
												class="flex items-center gap-3 p-4 bg-base-100/80 border border-base-300 rounded-xl"
											>
												{#if location.category?.icon}
													<span class="text-2xl flex-shrink-0">{location.category.icon}</span>
												{/if}
												<span class="text-base font-medium text-base-content">
													{location.category?.display_name || location.category?.name}
												</span>
											</div>
										{/if}
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
											bind:value={location.rating}
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
													checked={Number.isNaN(location.rating)}
												/>
												<input
													type="radio"
													name="rating-2"
													class="mask mask-star-2 bg-warning"
													on:click={() => (location.rating = 1)}
													checked={location.rating === 1}
												/>
												<input
													type="radio"
													name="rating-2"
													class="mask mask-star-2 bg-warning"
													on:click={() => (location.rating = 2)}
													checked={location.rating === 2}
												/>
												<input
													type="radio"
													name="rating-2"
													class="mask mask-star-2 bg-warning"
													on:click={() => (location.rating = 3)}
													checked={location.rating === 3}
												/>
												<input
													type="radio"
													name="rating-2"
													class="mask mask-star-2 bg-warning"
													on:click={() => (location.rating = 4)}
													checked={location.rating === 4}
												/>
												<input
													type="radio"
													name="rating-2"
													class="mask mask-star-2 bg-warning"
													on:click={() => (location.rating = 5)}
													checked={location.rating === 5}
												/>
											</div>
											{#if location.rating}
												<button
													type="button"
													class="btn btn-sm btn-error btn-outline gap-2"
													on:click={() => (location.rating = NaN)}
												>
													<svg
														class="w-4 h-4"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
														/>
													</svg>
													{$t('adventures.remove')}
												</button>
											{/if}
										</div>
									</div>

									<!-- Public Toggle -->
									{#if !locationToEdit || (locationToEdit.collections && locationToEdit.collections.length === 0)}
										<div class="form-control">
											<label class="label cursor-pointer justify-start gap-4" for="is_public">
												<input
													type="checkbox"
													class="toggle toggle-primary"
													id="is_public"
													name="is_public"
													bind:checked={location.is_public}
												/>
												<div>
													<span class="label-text font-medium"
														>{$t('adventures.public_location')}</span
													>
													<p class="text-sm text-base-content/60">
														{$t('adventures.public_location_desc')}
													</p>
												</div>
											</label>
										</div>
									{/if}
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
											bind:value={location.link}
											class="input input-bordered w-full bg-base-100/80 focus:bg-base-100"
											placeholder="https://example.com"
										/>
									</div>

									<!-- Description Field -->
									<div class="form-control">
										<label class="label" for="description">
											<span class="label-text font-medium">{$t('adventures.description')}</span>
										</label>
										<div class="bg-base-100/80 border border-base-300 rounded-xl p-4">
											<MarkdownEditor bind:text={location.description} />
										</div>
										<div class="flex items-center gap-4 mt-4">
											<div
												class="tooltip tooltip-right"
												data-tip={$t('adventures.wiki_location_desc')}
											>
												<button type="button" class="btn btn-neutral gap-2" on:click={generateDesc}>
													<svg
														class="w-4 h-4"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M13 10V3L4 14h7v7l9-11h-7z"
														/>
													</svg>
													{$t('adventures.generate_desc')}
												</button>
											</div>
											{#if wikiError}
												<div class="alert alert-error alert-sm">
													<svg
														class="w-4 h-4"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
														/>
													</svg>
													<span class="text-sm">{wikiError}</span>
												</div>
											{/if}
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Location Section -->
					<div class="mb-6">
						<LocationDropdown bind:item={location} bind:triggerMarkVisted {initialLatLng} />
					</div>

					<!-- Tags Section -->
					<div
						class="collapse collapse-plus bg-base-200/50 border border-base-300/50 mb-6 rounded-2xl overflow-hidden"
					>
						<input type="checkbox" />
						<div
							class="collapse-title text-xl font-semibold bg-gradient-to-r from-secondary/10 to-secondary/5"
						>
							<div class="flex items-center gap-3">
								<div class="p-2 bg-secondary/10 rounded-lg">
									<svg
										class="w-5 h-5 text-secondary"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z"
										/>
									</svg>
								</div>
								{$t('adventures.tags')} ({location.tags?.length || 0})
							</div>
						</div>
						<div class="collapse-content bg-base-100/50 p-6">
							<input
								type="text"
								id="tags"
								name="tags"
								hidden
								bind:value={location.tags}
								class="input input-bordered w-full"
							/>
							<ActivityComplete bind:tags={location.tags} />
						</div>
					</div>

					<!-- Date Range Section -->
					<div class="mb-6">
						<DateRangeCollapse type="adventure" {collection} bind:visits={location.visits} />
					</div>

					<!-- Warning Messages -->
					{#if warningMessage != ''}
						<div class="alert alert-warning mb-6">
							<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
								/>
							</svg>
							<div>
								<h3 class="font-bold">{$t('adventures.warning')}</h3>
								<div class="text-sm">{warningMessage}</div>
							</div>
						</div>
					{/if}
					<div
						class="bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6"
					>
						<button type="submit" class="btn btn-primary gap-2">
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M5 13l4 4L19 7"
								/>
							</svg>
							{$t('adventures.save_next')}
						</button>
						<button type="button" class="btn btn-ghost gap-2" on:click={close}>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
							{$t('about.close')}
						</button>
					</div>
				</form>
			</div>
		{:else}
			<!-- Attachments Section -->
			<div class="card bg-base-200 mb-6">
				<div class="card-body">
					<div class="flex items-center justify-between mb-4">
						<h3 class="card-title text-lg">
							{$t('adventures.attachments')}
							<div class="badge badge-neutral">{location.attachments?.length || 0}</div>
						</h3>
					</div>

					<!-- Existing Attachments Grid -->
					{#if location.attachments?.length > 0}
						<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6">
							{#each location.attachments as attachment}
								<AttachmentCard
									{attachment}
									on:delete={deleteAttachment}
									allowEdit
									on:edit={(e) => (attachmentToEdit = e.detail)}
								/>
							{/each}
						</div>
					{/if}

					<!-- Upload New Attachment -->
					<div class="bg-base-100 p-4 rounded-lg border border-base-300">
						<h4 class="font-medium mb-3">{$t('adventures.upload_attachment')}</h4>
						<div class="flex flex-col sm:flex-row gap-3">
							<input
								type="file"
								id="fileInput"
								class="file-input file-input-bordered flex-1"
								accept={allowedFileTypes.join(',')}
								on:change={handleFileChange}
							/>
							<input
								type="text"
								class="input input-bordered flex-1"
								placeholder={$t('adventures.attachment_name')}
								bind:value={attachmentName}
							/>
							<button class="btn btn-primary btn-sm sm:btn-md" on:click={uploadAttachment}>
								{$t('adventures.upload')}
							</button>
						</div>
					</div>

					<!-- Edit Attachment Form -->
					{#if attachmentToEdit}
						<div class="bg-warning/10 p-4 rounded-lg border border-warning/20 mt-4">
							<h4 class="font-medium mb-3 text-warning">
								{$t('transportation.edit')}
								{$t('adventures.attachment_name')}
							</h4>
							<form
								on:submit={(e) => {
									e.preventDefault();
									editAttachment();
								}}
								class="flex flex-col sm:flex-row gap-3"
							>
								<input
									type="text"
									class="input input-bordered flex-1"
									placeholder={$t('adventures.attachment_name')}
									bind:value={attachmentToEdit.name}
								/>
								<button type="submit" class="btn btn-warning btn-sm sm:btn-md">
									{$t('transportation.edit')}
								</button>
							</form>
						</div>
					{/if}

					<!-- GPX Tip -->
					<div class="alert alert-info mt-4">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="stroke-current h-6 w-6 shrink-0"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span class="text-sm">{$t('adventures.gpx_tip')}</span>
					</div>
				</div>
			</div>

			<!-- Images Section -->
			<div class="card bg-base-200 mb-6">
				<div class="card-body">
					<div class="flex items-center justify-between mb-4">
						<h3 class="card-title text-lg">
							{$t('adventures.images')}
							<div class="badge badge-neutral">{location.images?.length || 0}</div>
						</h3>
					</div>

					<!-- Image Upload Methods -->
					<div class="grid gap-4 lg:grid-cols-2">
						<!-- File Upload -->
						<div class="bg-base-100 p-4 rounded-lg border border-base-300">
							<h4 class="font-medium mb-3">{$t('adventures.upload_from_device')}</h4>
							<form class="space-y-3">
								<input
									type="file"
									name="image"
									class="file-input file-input-bordered w-full"
									bind:this={fileInput}
									accept="image/*"
									id="image"
									multiple
									on:change={handleMultipleFiles}
								/>
								<input type="hidden" name="adventure" value={location.id} id="adventure" />
							</form>
						</div>

						<!-- URL Upload -->
						<div class="bg-base-100 p-4 rounded-lg border border-base-300">
							<h4 class="font-medium mb-3">{$t('adventures.upload_from_url')}</h4>
							<div class="flex gap-2">
								<input
									type="text"
									id="url"
									name="url"
									bind:value={url}
									class="input input-bordered flex-1"
									placeholder="Enter image URL"
								/>
								<button class="btn btn-primary btn-sm" type="button" on:click={fetchImage}>
									{$t('adventures.fetch_image')}
								</button>
							</div>
						</div>

						<!-- Wikipedia Search -->
						<div class="bg-base-100 p-4 rounded-lg border border-base-300">
							<h4 class="font-medium mb-3">{$t('adventures.wikipedia')}</h4>
							<div class="flex gap-2">
								<input
									type="text"
									id="name"
									name="name"
									bind:value={imageSearch}
									class="input input-bordered flex-1"
									placeholder="Search Wikipedia for images"
								/>
								<button class="btn btn-primary btn-sm" type="button" on:click={fetchWikiImage}>
									{$t('adventures.fetch_image')}
								</button>
							</div>
							{#if wikiImageError}
								<div class="alert alert-error mt-2">
									<span class="text-sm">{$t('adventures.wiki_image_error')}</span>
								</div>
							{/if}
						</div>

						<!-- Immich Integration -->
						{#if immichIntegration}
							<div class="bg-base-100 p-4 rounded-lg border border-base-300">
								<h4 class="font-medium mb-3">Immich Integration</h4>
								<ImmichSelect
									{location}
									on:fetchImage={(e) => {
										url = e.detail;
										fetchImage();
									}}
									{copyImmichLocally}
									on:remoteImmichSaved={(e) => {
										const newImage = {
											id: e.detail.id,
											image: e.detail.image,
											is_primary: e.detail.is_primary,
											immich_id: e.detail.immich_id
										};
										images = [...images, newImage];
										location.images = images;
										addToast('success', $t('adventures.image_upload_success'));
									}}
								/>
							</div>
						{/if}
					</div>

					<div class="divider my-6"></div>

					<!-- Current Images -->
					<div class="space-y-4">
						<h4 class="font-semibold text-lg">{$t('adventures.my_images')}</h4>

						{#if images.length > 0}
							<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
								{#each images as image}
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
													<Star class="h-4 w-4" />
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
												<Crown class="h-4 w-4" />
											</div>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<div class="text-center py-8">
								<div class="text-base-content/60 text-lg mb-2">{$t('adventures.no_images')}</div>
								<p class="text-sm text-base-content/40">Upload images to get started</p>
							</div>
						{/if}
					</div>
				</div>
			</div>
			<div class="mt-4">
				<button type="button" class="btn btn-primary w-full max-w-sm" on:click={saveAndClose}>
					{$t('about.close')}
				</button>
			</div>
		{/if}

		{#if location.is_public && location.id}
			<div class="bg-neutral p-4 mt-2 rounded-md shadow-sm text-neutral-content">
				<p class=" font-semibold">{$t('adventures.share_location')}</p>
				<div class="flex items-center justify-between">
					<p class="text-card-foreground font-mono">
						{window.location.origin}/locations/{location.id}
					</p>
					<button
						type="button"
						on:click={() => {
							navigator.clipboard.writeText(`${window.location.origin}/locations/${location.id}`);
						}}
						class="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 h-10 px-4 py-2"
					>
						{$t('adventures.copy_link')}
					</button>
				</div>
			</div>
		{/if}
	</div>
</dialog>
