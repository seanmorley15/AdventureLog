<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import MarkdownEditor from './MarkdownEditor.svelte';
	import { addToast } from '$lib/toasts';
	import { copyToClipboard } from '$lib/index';
	import type { Collection, ContentImage, SlimCollection } from '$lib/types';

	// Icons
	import CollectionIcon from '~icons/mdi/folder-multiple';
	import InfoIcon from '~icons/mdi/information';
	import CalendarIcon from '~icons/mdi/calendar';
	import LinkIcon from '~icons/mdi/link';
	import SaveIcon from '~icons/mdi/content-save';
	import CloseIcon from '~icons/mdi/close';
	import ImageIcon from '~icons/mdi/image-multiple';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	export let collectionToEdit: Collection | null = null;

	let collection: Collection = {
		id: collectionToEdit?.id || '',
		name: collectionToEdit?.name || '',
		description: collectionToEdit?.description || '',
		start_date: collectionToEdit?.start_date || null,
		end_date: collectionToEdit?.end_date || null,
		user: collectionToEdit?.user || '',
		is_public: collectionToEdit?.is_public || false,
		locations: collectionToEdit?.locations || [],
		link: collectionToEdit?.link || '',
		shared_with: collectionToEdit?.shared_with || [],
		itinerary: collectionToEdit?.itinerary || [],
		status: collectionToEdit?.status || 'folder',
		days_until_start: collectionToEdit?.days_until_start ?? null,
		primary_image: collectionToEdit?.primary_image ?? null,
		primary_image_id: collectionToEdit?.primary_image_id ?? null,
		itinerary_days: []
	};

	let availableImages: ContentImage[] = [];
	let coverImageId: string | null = collection.primary_image?.id || null;

	function setImagesFromCollection(col: Collection) {
		const seen = new Map<string, ContentImage>();
		(col.locations || []).forEach((loc) => {
			(loc.images || []).forEach((img) => {
				if (!seen.has(img.id)) {
					seen.set(img.id, img);
				}
			});
		});

		const deduped = Array.from(seen.values());
		deduped.sort((a, b) => {
			if (coverImageId && a.id === coverImageId) return -1;
			if (coverImageId && b.id === coverImageId) return 1;
			if (a.is_primary && !b.is_primary) return -1;
			if (!a.is_primary && b.is_primary) return 1;
			return a.id.localeCompare(b.id);
		});

		availableImages = deduped;
	}

	function selectCover(imageId: string | null) {
		coverImageId = imageId;
		collection.primary_image_id = imageId;
		setImagesFromCollection(collection);
	}

	function toSlimCollection(col: Collection): SlimCollection {
		return {
			id: col.id,
			user: col.user,
			name: col.name,
			description: col.description,
			is_public: col.is_public,
			start_date: col.start_date,
			end_date: col.end_date,
			is_archived: col.is_archived ?? false,
			link: col.link ?? null,
			created_at: col.created_at ?? '',
			updated_at: col.updated_at ?? '',
			location_images: (col.locations || []).flatMap((loc) => loc.images || []),
			location_count: (col.locations || []).length,
			shared_with: col.shared_with || [],
			status: col.status ?? 'folder',
			days_until_start: col.days_until_start ?? null,
			primary_image: col.primary_image ?? null
		};
	}

	async function loadCollectionDetails() {
		if (!collectionToEdit?.id) {
			setImagesFromCollection(collection);
			return;
		}

		try {
			const res = await fetch(`/api/collections/${collectionToEdit.id}?nested=true`);
			if (res.ok) {
				const data = (await res.json()) as Collection;
				collection = { ...collection, ...data };
				coverImageId = data.primary_image?.id ?? coverImageId;
				collection.primary_image_id = coverImageId;
				setImagesFromCollection(collection);
				return;
			}
		} catch (err) {
			console.error(err);
		}

		setImagesFromCollection(collection);
	}

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		await loadCollectionDetails();
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

		if (collection.start_date && !collection.end_date) {
			collection.end_date = collection.start_date;
		}

		if (
			collection.start_date &&
			collection.end_date &&
			collection.start_date > collection.end_date
		) {
			addToast('error', $t('adventures.start_before_end_error'));
			return;
		}

		if (!collection.start_date && collection.end_date) {
			collection.start_date = collection.end_date;
		}

		if (!collection.start_date && !collection.end_date) {
			collection.start_date = null;
			collection.end_date = null;
		}

		const payload: any = {
			name: collection.name,
			description: collection.description,
			start_date: collection.start_date,
			end_date: collection.end_date,
			is_public: collection.is_public,
			link: collection.link,
			primary_image_id: coverImageId
		};

		// Clean up link: empty/whitespace → null, invalid URL → null
		if (!payload.link || !payload.link.trim()) {
			payload.link = null;
		} else {
			try {
				new URL(payload.link);
			} catch {
				payload.link = null;
			}
		}

		if (collection.id === '') {
			let res = await fetch('/api/collections', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				coverImageId = collection.primary_image?.id ?? null;
				collection.primary_image_id = coverImageId;
				setImagesFromCollection(collection);
				addToast('success', $t('collection.collection_created'));
				dispatch('save', toSlimCollection(collection));
			} else {
				console.error(data);
				// Extract field-level errors from Django response
				const fieldErrors = Object.entries(data)
					.filter(([_, v]) => Array.isArray(v))
					.map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
					.join('; ');
				addToast('error', fieldErrors || $t('collection.error_creating_collection'));
			}
		} else {
			let res = await fetch(`/api/collections/${collection.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			let data = await res.json();
			if (data.id) {
				collection = data as Collection;
				coverImageId = collection.primary_image?.id ?? null;
				collection.primary_image_id = coverImageId;
				setImagesFromCollection(collection);
				addToast('success', $t('collection.collection_edit_success'));
				dispatch('save', toSlimCollection(collection));
			} else {
				// Extract field-level errors from Django response
				const fieldErrors = Object.entries(data)
					.filter(([_, v]) => Array.isArray(v))
					.map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
					.join('; ');
				addToast('error', fieldErrors || $t('collection.error_editing_collection'));
			}
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="modal-box w-11/12 max-w-6xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl max-h-[85vh] flex flex-col"
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
						<CollectionIcon class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{collectionToEdit
								? $t('adventures.edit_collection')
								: $t('collection.new_collection')}
						</h1>
						<p class="text-sm text-base-content/60">
							{collectionToEdit
								? $t('collection.update_collection_details')
								: $t('collection.create_new_collection')}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<CloseIcon class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="p-6 overflow-auto max-h-[70vh]">
			<form method="post" on:submit={handleSubmit} class="space-y-6">
				<!-- Basic Information Section -->
				<div class="card bg-base-100 border border-base-300 shadow-lg">
					<div class="card-body p-6">
						<div class="flex items-center gap-3 mb-6">
							<div class="p-2 bg-primary/10 rounded-lg">
								<InfoIcon class="w-5 h-5 text-primary" />
							</div>
							<h2 class="text-xl font-bold">{$t('adventures.basic_information')}</h2>
						</div>

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
										bind:value={collection.name}
										class="input input-bordered w-full"
										placeholder={$t('collection.enter_collection_name')}
										required
									/>
								</div>

								<!-- Description Field -->
								<div class="form-control">
									<label class="label" for="description">
										<span class="label-text font-medium">{$t('adventures.description')}</span>
									</label>
									<MarkdownEditor bind:text={collection.description} editor_height={'h-32'} />
								</div>

								<!-- Link Field -->
								<div class="form-control">
									<label class="label" for="link">
										<span class="label-text font-medium flex items-center gap-2">
											<LinkIcon class="w-4 h-4" />
											{$t('adventures.link')}
										</span>
									</label>
									<input
										type="text"
										id="link"
										name="link"
										bind:value={collection.link}
										class="input input-bordered w-full"
										placeholder="https://example.com"
									/>
								</div>
							</div>

							<!-- Right Column -->
							<div class="space-y-4">
								<!-- Start Date -->
								<div class="form-control">
									<label class="label" for="start_date">
										<span class="label-text font-medium flex items-center gap-2">
											<CalendarIcon class="w-4 h-4" />
											{$t('adventures.start_date')}
										</span>
									</label>
									<input
										type="date"
										id="start_date"
										name="start_date"
										bind:value={collection.start_date}
										class="input input-bordered w-full"
									/>
								</div>

								<!-- End Date -->
								<div class="form-control">
									<label class="label" for="end_date">
										<span class="label-text font-medium flex items-center gap-2">
											<CalendarIcon class="w-4 h-4" />
											{$t('adventures.end_date')}
										</span>
									</label>
									<input
										type="date"
										id="end_date"
										name="end_date"
										bind:value={collection.end_date}
										class="input input-bordered w-full"
									/>
								</div>

								<!-- Public Toggle -->
								<div class="form-control">
									<label class="label cursor-pointer justify-start gap-3">
										<input
											type="checkbox"
											class="toggle toggle-primary"
											id="is_public"
											name="is_public"
											bind:checked={collection.is_public}
										/>
										<span class="label-text font-medium">{$t('collection.public_collection')}</span>
									</label>
									<div class="pl-12">
										<span class="text-sm text-base-content/60"
											>{$t('collection.public_collection_description')}</span
										>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Date Warning Alert -->
				{#if !collection.start_date && !collection.end_date}
					<div role="alert" class="alert alert-info shadow-lg">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							class="h-6 w-6 shrink-0 stroke-current"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
							></path>
						</svg>
						<span>{$t('adventures.collection_no_start_end_date')}</span>
					</div>
				{:else if collection.id && collectionToEdit?.start_date && collectionToEdit?.end_date && (collection.start_date !== collectionToEdit.start_date || collection.end_date !== collectionToEdit.end_date)}
					<div role="alert" class="alert alert-warning shadow-lg">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="stroke-current shrink-0 h-6 w-6"
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
						<div>
							<div class="font-bold">{$t('collection.changing_date_title')}</div>
							<div class="text-sm">
								{$t('collection.changing_date_warning')}
							</div>
						</div>
					</div>
				{/if}

				<!-- Cover Image Selection -->
				{#if collection.id}
					<div class="card bg-base-100 border border-base-300 shadow-lg">
						<div class="card-body p-6 space-y-4">
							<div class="flex items-center gap-3">
								<div class="p-2 bg-primary/10 rounded-lg">
									<ImageIcon class="w-5 h-5 text-primary" />
								</div>
								<div>
									<h3 class="text-lg font-semibold">
										{$t('collection.cover_image') ?? 'Cover image'}
									</h3>
									<p class="text-sm text-base-content/60">
										{$t('collection.cover_image_hint') ??
											'Choose a cover from images in this collection.'}
									</p>
								</div>
							</div>

							{#if availableImages.length === 0}
								<div class="alert alert-info shadow-sm">
									<span>
										{$t('collection.no_images_available') ??
											'No images available from linked locations yet.'}
									</span>
								</div>
							{:else}
								<div class="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
									{#each availableImages as image (image.id)}
										<button
											type="button"
											class="relative group rounded-xl overflow-hidden border border-base-300 bg-base-200/30 hover:border-primary transition shadow-sm {coverImageId ===
											image.id
												? 'ring-2 ring-primary ring-offset-2 ring-offset-base-100'
												: ''}"
											on:click={() => selectCover(image.id)}
											aria-pressed={coverImageId === image.id}
										>
											<img
												src={image.image}
												alt="Cover candidate"
												class="w-full h-32 object-cover"
											/>
											<div
												class="absolute inset-0 bg-gradient-to-t from-base-300/60 to-transparent opacity-0 group-hover:opacity-100 transition"
											/>
											{#if coverImageId === image.id}
												<div class="absolute top-2 left-2 badge badge-primary gap-2 shadow">
													{$t('collection.cover') ?? 'Cover'}
												</div>
											{:else if image.is_primary}
												<div class="absolute top-2 left-2 badge badge-ghost shadow">
													{$t('collection.location_primary') ?? 'Location cover'}
												</div>
											{/if}
											<div
												class="absolute bottom-2 right-2 btn btn-xs btn-ghost bg-base-100/90 shadow"
											>
												{coverImageId === image.id
													? ($t('collection.cover') ?? 'Cover')
													: ($t('collection.set_cover') ?? 'Set cover')}
											</div>
										</button>
									{/each}
								</div>
								<div class="flex justify-end">
									<button
										type="button"
										class="btn btn-ghost btn-sm"
										on:click={() => selectCover(null)}
									>
										<CloseIcon class="w-4 h-4" />
										<span>{$t('collection.clear_cover') ?? 'Clear cover'}</span>
									</button>
								</div>
							{/if}
						</div>
					</div>
				{/if}

				<!-- Share Link Section (only if public and has ID) -->
				{#if collection.is_public && collection.id}
					<div class="card bg-base-100 border border-base-300 shadow-lg">
						<div class="card-body p-6">
							<h3 class="font-semibold text-lg mb-3">{$t('adventures.share_collection')}</h3>
							<div class="flex items-center gap-3">
								<input
									type="text"
									value="{window.location.origin}/collections/{collection.id}"
									readonly
									class="input input-bordered flex-1 font-mono text-sm"
								/>
								<button
									type="button"
									on:click={async () => {
										try {
											await copyToClipboard(
												`${window.location.origin}/collections/${collection.id}`
											);
											addToast('success', $t('adventures.link_copied'));
										} catch {
											addToast('error', $t('adventures.copy_failed') || 'Copy failed');
										}
									}}
									class="btn btn-primary gap-2"
								>
									<LinkIcon class="w-4 h-4" />
									{$t('adventures.copy_link')}
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Action Buttons -->
				<div class="flex gap-3 justify-end pt-4">
					<button type="button" class="btn btn-neutral gap-2" on:click={close}>
						<CloseIcon class="w-5 h-5" />
						{$t('about.close')}
					</button>
					<button type="submit" class="btn btn-primary gap-2">
						<SaveIcon class="w-5 h-5" />
						{$t('notes.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</dialog>
