<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { Adventure, Attachment, Category, Collection } from '$lib/types';
	import { addToast } from '$lib/toasts';
	import { deserialize } from '$app/forms';
	import { t } from 'svelte-i18n';
	export let collection: Collection | null = null;

	let fullStartDate: string = '';
	let fullEndDate: string = '';
	let fullStartDateOnly: string = '';
	let fullEndDateOnly: string = '';
	let allDay: boolean = true;

	// Set full start and end dates from collection
	if (collection && collection.start_date && collection.end_date) {
		fullStartDate = `${collection.start_date}T00:00`;
		fullEndDate = `${collection.end_date}T23:59`;
		fullStartDateOnly = collection.start_date;
		fullEndDateOnly = collection.end_date;
	}

	const dispatch = createEventDispatcher();

	let images: { id: string; image: string; is_primary: boolean }[] = [];
	let warningMessage: string = '';
	let constrainDates: boolean = false;

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

	import ActivityComplete from './ActivityComplete.svelte';
	import CategoryDropdown from './CategoryDropdown.svelte';
	import { findFirstValue, isAllDay } from '$lib';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import ImmichSelect from './ImmichSelect.svelte';
	import Star from '~icons/mdi/star';
	import Crown from '~icons/mdi/crown';
	import AttachmentCard from './AttachmentCard.svelte';
	import LocationDropdown from './LocationDropdown.svelte';
	import DateRangeCollapse from './DateRangeCollapse.svelte';
	let modal: HTMLDialogElement;

	let wikiError: string = '';

	let adventure: Adventure = {
		id: '',
		name: '',
		visits: [],
		link: null,
		description: null,
		activity_types: [],
		rating: NaN,
		is_public: false,
		latitude: NaN,
		longitude: NaN,
		location: null,
		images: [],
		user_id: null,
		collection: collection?.id || null,
		category: {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user_id: ''
		},
		attachments: []
	};

	export let adventureToEdit: Adventure | null = null;

	adventure = {
		id: adventureToEdit?.id || '',
		name: adventureToEdit?.name || '',
		link: adventureToEdit?.link || null,
		description: adventureToEdit?.description || null,
		activity_types: adventureToEdit?.activity_types || [],
		rating: adventureToEdit?.rating || NaN,
		is_public: adventureToEdit?.is_public || false,
		latitude: adventureToEdit?.latitude || NaN,
		longitude: adventureToEdit?.longitude || NaN,
		location: adventureToEdit?.location || null,
		images: adventureToEdit?.images || [],
		user_id: adventureToEdit?.user_id || null,
		collection: adventureToEdit?.collection || collection?.id || null,
		visits: adventureToEdit?.visits || [],
		is_visited: adventureToEdit?.is_visited || false,
		category: adventureToEdit?.category || {
			id: '',
			name: '',
			display_name: '',
			icon: '',
			user_id: ''
		},

		attachments: adventureToEdit?.attachments || []
	};

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		modal.showModal();
		let categoryFetch = await fetch('/api/categories/categories');
		if (categoryFetch.ok) {
			categories = await categoryFetch.json();
		} else {
			addToast('error', $t('adventures.category_fetch_error'));
		}
		// Check for Immich Integration
		let res = await fetch('/api/integrations');
		if (!res.ok) {
			addToast('error', $t('immich.integration_fetch_error'));
		} else {
			let data = await res.json();
			if (data.immich) {
				immichIntegration = true;
			}
		}
	});

	let url: string = '';
	let imageError: string = '';
	let wikiImageError: string = '';
	let triggerMarkVisted: boolean = false;

	images = adventure.images || [];
	$: {
		if (!adventure.rating) {
			adventure.rating = NaN;
		}
	}

	function deleteAttachment(event: CustomEvent<string>) {
		adventure.attachments = adventure.attachments.filter(
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
				adventure.attachments = adventure.attachments.map((attachment) => {
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
		formData.append('adventure', adventure.id);
		formData.append('name', attachmentName);

		try {
			const res = await fetch('/adventures?/attachment', {
				method: 'POST',
				body: formData
			});

			if (res.ok) {
				const newData = deserialize(await res.text()) as { data: Attachment };
				adventure.attachments = [...adventure.attachments, newData.data];
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

	let imageSearch: string = adventure.name || '';

	async function removeImage(id: string) {
		let res = await fetch(`/api/images/${id}/image_delete`, {
			method: 'POST'
		});
		if (res.status === 204) {
			images = images.filter((image) => image.id !== id);
			adventure.images = images;
			addToast('success', $t('adventures.image_removed_success'));
		} else {
			addToast('error', $t('adventures.image_removed_error'));
		}
	}

	let isDetails: boolean = true;

	function saveAndClose() {
		dispatch('save', adventure);
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
			adventure.images = images;
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
		formData.append('adventure', adventure.id);

		let res = await fetch(`/adventures?/image`, {
			method: 'POST',
			body: formData
		});
		if (res.ok) {
			let newData = deserialize(await res.text()) as { data: { id: string; image: string } };
			let newImage = { id: newData.data.id, image: newData.data.image, is_primary: false };
			images = [...images, newImage];
			adventure.images = images;
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
			formData.append('adventure', adventure.id);

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
			formData.append('adventure', adventure.id);
			let res2 = await fetch(`/adventures?/image`, {
				method: 'POST',
				body: formData
			});
			if (res2.ok) {
				let newData = deserialize(await res2.text()) as { data: { id: string; image: string } };
				let newImage = { id: newData.data.id, image: newData.data.image, is_primary: false };
				images = [...images, newImage];
				adventure.images = images;
				addToast('success', $t('adventures.image_upload_success'));
			} else {
				addToast('error', $t('adventures.image_upload_error'));
				wikiImageError = $t('adventures.wiki_image_error');
			}
		}
	}

	let new_start_date: string = '';
	let new_end_date: string = '';
	let new_notes: string = '';

	// Function to add a new visit.
	function addNewVisit() {
		// If an end date isn’t provided, assume it’s the same as start.
		if (new_start_date && !new_end_date) {
			new_end_date = new_start_date;
		}
		if (new_start_date > new_end_date) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}
		if (new_end_date && !new_start_date) {
			addToast('error', $t('adventures.no_start_date'));
			return;
		}
		// Convert input to UTC if not already.
		if (new_start_date && !new_start_date.includes('Z')) {
			new_start_date = new Date(new_start_date).toISOString();
		}
		if (new_end_date && !new_end_date.includes('Z')) {
			new_end_date = new Date(new_end_date).toISOString();
		}

		// If the visit is all day, force the times to midnight.
		if (allDay) {
			new_start_date = new_start_date.split('T')[0] + 'T00:00:00.000Z';
			new_end_date = new_end_date.split('T')[0] + 'T00:00:00.000Z';
		}

		adventure.visits = [
			...adventure.visits,
			{
				start_date: new_start_date,
				end_date: new_end_date,
				notes: new_notes,
				id: '' // or generate an id as needed
			}
		];

		// Clear the input fields.
		new_start_date = '';
		new_end_date = '';
		new_notes = '';
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
		let res = await fetch(`/api/generate/desc/?name=${adventure.name}`);
		let data = await res.json();
		if (data.extract?.length > 0) {
			adventure.description = data.extract;
			wikiError = '';
		} else {
			wikiError = $t('adventures.no_description_found');
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		triggerMarkVisted = true;

		// if category icon is empty, set it to the default icon
		if (adventure.category?.icon == '' || adventure.category?.icon == null) {
			if (adventure.category) {
				adventure.category.icon = '🌍';
			}
		}

		if (adventure.id === '') {
			if (adventure.category?.display_name == '') {
				if (categories.some((category) => category.name === 'general')) {
					adventure.category = categories.find(
						(category) => category.name === 'general'
					) as Category;
				} else {
					adventure.category = {
						id: '',
						name: 'general',
						display_name: 'General',
						icon: '🌍',
						user_id: ''
					};
				}
			}

			let res = await fetch('/api/adventures', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(adventure)
			});
			let data = await res.json();
			if (data.id) {
				adventure = data as Adventure;
				isDetails = false;
				warningMessage = '';
				addToast('success', $t('adventures.adventure_created'));
			} else {
				warningMessage = findFirstValue(data) as string;
				console.error(data);
				addToast('error', $t('adventures.adventure_create_error'));
			}
		} else {
			let res = await fetch(`/api/adventures/${adventure.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(adventure)
			});
			let data = await res.json();
			if (data.id) {
				adventure = data as Adventure;
				isDetails = false;
				warningMessage = '';
				addToast('success', $t('adventures.adventure_updated'));
			} else {
				warningMessage = Object.values(data)[0] as string;
				addToast('error', $t('adventures.adventure_update_error'));
			}
		}
		imageSearch = adventure.name;
	}
</script>

<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div class="modal-box w-11/12 max-w-3xl" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-2xl">
			{adventureToEdit ? $t('adventures.edit_adventure') : $t('adventures.new_adventure')}
		</h3>
		{#if adventure.id === '' || isDetails}
			<div class="modal-action items-center">
				<form method="post" style="width: 100%;" on:submit={handleSubmit}>
					<!-- Grid layout for form fields -->
					<!-- <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3"> -->
					<div class="collapse collapse-plus bg-base-200 mb-4">
						<input type="checkbox" checked />
						<div class="collapse-title text-xl font-medium">
							{$t('adventures.basic_information')}
						</div>
						<div class="collapse-content">
							<div>
								<label for="name">{$t('adventures.name')}<span class="text-red-500">*</span></label
								><br />
								<input
									type="text"
									id="name"
									name="name"
									bind:value={adventure.name}
									class="input input-bordered w-full"
									required
								/>
							</div>
							<div>
								<label for="link"
									>{$t('adventures.category')}<span class="text-red-500">*</span></label
								><br />

								<CategoryDropdown bind:categories bind:selected_category={adventure.category} />
							</div>
							<div>
								<label for="rating">{$t('adventures.rating')}</label><br />
								<input
									type="number"
									min="0"
									max="5"
									hidden
									bind:value={adventure.rating}
									id="rating"
									name="rating"
									class="input input-bordered w-full max-w-xs mt-1"
								/>
								<div class="rating -ml-3 mt-1">
									<input
										type="radio"
										name="rating-2"
										class="rating-hidden"
										checked={Number.isNaN(adventure.rating)}
									/>
									<input
										type="radio"
										name="rating-2"
										class="mask mask-star-2 bg-orange-400"
										on:click={() => (adventure.rating = 1)}
										checked={adventure.rating === 1}
									/>
									<input
										type="radio"
										name="rating-2"
										class="mask mask-star-2 bg-orange-400"
										on:click={() => (adventure.rating = 2)}
										checked={adventure.rating === 2}
									/>
									<input
										type="radio"
										name="rating-2"
										class="mask mask-star-2 bg-orange-400"
										on:click={() => (adventure.rating = 3)}
										checked={adventure.rating === 3}
									/>
									<input
										type="radio"
										name="rating-2"
										class="mask mask-star-2 bg-orange-400"
										on:click={() => (adventure.rating = 4)}
										checked={adventure.rating === 4}
									/>
									<input
										type="radio"
										name="rating-2"
										class="mask mask-star-2 bg-orange-400"
										on:click={() => (adventure.rating = 5)}
										checked={adventure.rating === 5}
									/>
									{#if adventure.rating}
										<button
											type="button"
											class="btn btn-sm btn-error ml-2"
											on:click={() => (adventure.rating = NaN)}
										>
											{$t('adventures.remove')}
										</button>
									{/if}
								</div>
							</div>
							<div>
								<div>
									<label for="link">{$t('adventures.link')}</label><br />
									<input
										type="text"
										id="link"
										name="link"
										bind:value={adventure.link}
										class="input input-bordered w-full"
									/>
								</div>
							</div>
							<div>
								<label for="description">{$t('adventures.description')}</label><br />
								<MarkdownEditor bind:text={adventure.description} />
								<div class="mt-2">
									<div class="tooltip tooltip-right" data-tip={$t('adventures.wiki_desc')}>
										<button type="button" class="btn btn-neutral mt-2" on:click={generateDesc}
											>{$t('adventures.generate_desc')}</button
										>
									</div>
									<p class="text-red-500">{wikiError}</p>
								</div>
							</div>
							{#if !collection?.id}
								<div>
									<div class="form-control flex items-start mt-1">
										<label class="label cursor-pointer flex items-start space-x-2">
											<span class="label-text">{$t('adventures.public_adventure')}</span>
											<input
												type="checkbox"
												class="toggle toggle-primary"
												id="is_public"
												name="is_public"
												bind:checked={adventure.is_public}
											/>
										</label>
									</div>
								</div>
							{/if}
						</div>
					</div>

					<LocationDropdown bind:item={adventure} bind:triggerMarkVisted {initialLatLng} />

					<div class="collapse collapse-plus bg-base-200 mb-4 overflow-visible">
						<input type="checkbox" />
						<div class="collapse-title text-xl font-medium">
							{$t('adventures.tags')} ({adventure.activity_types?.length || 0})
						</div>
						<div class="collapse-content">
							<input
								type="text"
								id="activity_types"
								name="activity_types"
								hidden
								bind:value={adventure.activity_types}
								class="input input-bordered w-full"
							/>
							<ActivityComplete bind:activities={adventure.activity_types} />
						</div>
					</div>

					<DateRangeCollapse type="adventure" {collection} bind:visits={adventure.visits} />

					<div>
						<div class="mt-4">
							{#if warningMessage != ''}
								<div role="alert" class="alert alert-warning mb-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="h-6 w-6 shrink-0 stroke-current"
										fill="none"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
										/>
									</svg>
									<span>{$t('adventures.warning')}: {warningMessage}</span>
								</div>
							{/if}
							<div class="flex flex-row gap-2">
								<button type="submit" class="btn btn-primary">{$t('adventures.save_next')}</button>
								<button type="button" class="btn" on:click={close}>{$t('about.close')}</button>
							</div>
						</div>
					</div>
				</form>
			</div>
		{:else}
			<div class="modal-action items-center">
				<div class="collapse collapse-plus bg-base-200 mb-4">
					<input type="checkbox" />
					<div class="collapse-title text-xl font-medium">
						{$t('adventures.attachments')} ({adventure.attachments?.length || 0})
					</div>
					<div class="collapse-content">
						<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
							{#each adventure.attachments as attachment}
								<AttachmentCard
									{attachment}
									on:delete={deleteAttachment}
									allowEdit
									on:edit={(e) => (attachmentToEdit = e.detail)}
								/>
							{/each}
						</div>
						<div class="flex gap-2 m-4">
							<input
								type="file"
								id="fileInput"
								class="file-input file-input-bordered w-full max-w-xs"
								accept={allowedFileTypes.join(',')}
								on:change={handleFileChange}
							/>

							<input
								type="text"
								class="input input-bordered w-full"
								placeholder={$t('adventures.attachment_name')}
								bind:value={attachmentName}
							/>
							<button class="btn btn-neutral" on:click={uploadAttachment}>
								{$t('adventures.upload')}
							</button>
						</div>

						{#if attachmentToEdit}
							<form
								on:submit={(e) => {
									e.preventDefault();
									editAttachment();
								}}
							>
								<div class="flex gap-2 m-4">
									<input
										type="text"
										class="input input-bordered w-full"
										placeholder={$t('adventures.attachment_name')}
										bind:value={attachmentToEdit.name}
									/>
									<button type="submit" class="btn btn-neutral">{$t('transportation.edit')}</button>
								</div>
							</form>
						{/if}
					</div>
				</div>
			</div>
			<div class="collapse collapse-plus bg-base-200 mb-4">
				<input type="checkbox" checked />
				<div class="collapse-title text-xl font-medium">
					{$t('adventures.images')} ({adventure.images?.length || 0})
				</div>
				<div class="collapse-content">
					<label for="image" class="block font-medium mb-2">
						{$t('adventures.image')}
					</label>
					<form class="flex flex-col items-start gap-2">
						<input
							type="file"
							name="image"
							class="file-input file-input-bordered w-full max-w-sm"
							bind:this={fileInput}
							accept="image/*"
							id="image"
							multiple
							on:change={handleMultipleFiles}
						/>
						<input type="hidden" name="adventure" value={adventure.id} id="adventure" />
					</form>

					<div class="mb-4">
						<label for="url" class="block font-medium mb-2">
							{$t('adventures.url')}
						</label>
						<div class="flex gap-2">
							<input
								type="text"
								id="url"
								name="url"
								bind:value={url}
								class="input input-bordered flex-1"
								placeholder="Enter image URL"
							/>
							<button class="btn btn-neutral" type="button" on:click={fetchImage}>
								{$t('adventures.fetch_image')}
							</button>
						</div>
					</div>

					<div class="mb-4">
						<label for="name" class="block font-medium mb-2">
							{$t('adventures.wikipedia')}
						</label>
						<div class="flex gap-2">
							<input
								type="text"
								id="name"
								name="name"
								bind:value={imageSearch}
								class="input input-bordered flex-1"
								placeholder="Search Wikipedia for images"
							/>
							<button class="btn btn-neutral" type="button" on:click={fetchWikiImage}>
								{$t('adventures.fetch_image')}
							</button>
						</div>
						{#if wikiImageError}
							<p class="text-red-500">{$t('adventures.wiki_image_error')}</p>
						{/if}
					</div>

					{#if immichIntegration}
						<ImmichSelect
							{adventure}
							on:fetchImage={(e) => {
								url = e.detail;
								fetchImage();
							}}
						/>
					{/if}

					<div class="divider"></div>

					{#if images.length > 0}
						<h1 class="font-semibold text-xl mb-4">{$t('adventures.my_images')}</h1>
						<div class="flex flex-wrap gap-4">
							{#each images as image}
								<div class="relative h-32 w-32">
									<button
										type="button"
										class="absolute top-1 right-1 btn btn-error btn-xs z-10"
										on:click={() => removeImage(image.id)}
									>
										✕
									</button>
									{#if !image.is_primary}
										<button
											type="button"
											class="absolute top-1 left-1 btn btn-success btn-xs z-10"
											on:click={() => makePrimaryImage(image.id)}
										>
											<Star class="h-4 w-4" />
										</button>
									{:else}
										<!-- crown icon -->

										<div class="absolute top-1 left-1 bg-warning text-white rounded-full p-1 z-10">
											<Crown class="h-4 w-4" />
										</div>
									{/if}
									<img
										src={image.image}
										alt={image.id}
										class="w-full h-full object-cover rounded-md shadow-md"
									/>
								</div>
							{/each}
						</div>
					{:else}
						<h1 class="font-semibold text-xl text-gray-500">{$t('adventures.no_images')}</h1>
					{/if}
				</div>
			</div>
			<div class="mt-4">
				<button type="button" class="btn btn-primary w-full max-w-sm" on:click={saveAndClose}>
					{$t('about.close')}
				</button>
			</div>
		{/if}

		{#if adventure.is_public && adventure.id}
			<div class="bg-neutral p-4 mt-2 rounded-md shadow-sm text-neutral-content">
				<p class=" font-semibold">{$t('adventures.share_adventure')}</p>
				<div class="flex items-center justify-between">
					<p class="text-card-foreground font-mono">
						{window.location.origin}/adventures/{adventure.id}
					</p>
					<button
						type="button"
						on:click={() => {
							navigator.clipboard.writeText(`${window.location.origin}/adventures/${adventure.id}`);
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
