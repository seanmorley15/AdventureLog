<script lang="ts">
	import type { Attachment, ContentImage, Trail, WandererTrail } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	// Icons
	import SaveIcon from '~icons/mdi/content-save';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import TrashIcon from '~icons/mdi/delete';
	import EditIcon from '~icons/mdi/pencil';
	import CheckIcon from '~icons/mdi/check';
	import CloseIcon from '~icons/mdi/close';
	import Star from '~icons/mdi/star';
	import SwapHorizontalVariantIcon from '~icons/mdi/swap-horizontal-variant';
	import LinkIcon from '~icons/mdi/link';
	import PlusIcon from '~icons/mdi/plus';
	import MapPin from '~icons/mdi/map-marker';
	import Clock from '~icons/mdi/clock';
	import TrendingUp from '~icons/mdi/trending-up';
	import Calendar from '~icons/mdi/calendar';
	import Users from '~icons/mdi/account-supervisor';
	import Camera from '~icons/mdi/camera';

	import { addToast } from '$lib/toasts';
	import ImageManagement from '../ImageManagement.svelte';
	import AttachmentManagement from '../AttachmentManagement.svelte';
	import WandererCard from '../cards/WandererCard.svelte';

	// Props
	export let images: ContentImage[] = [];
	export let attachments: Attachment[] = [];
	export let itemName: string = '';
	export let trails: Trail[] = [];
	export let itemId: string = '';
	export let measurementSystem: 'metric' | 'imperial' = 'metric';
	export let userIsOwner: boolean = false;
	export let collaborativeMode: boolean = false;

	// Component state
	let immichIntegration: boolean = false;
	let copyImmichLocally: boolean = false;
	let importInProgress: boolean = false;

	// Trail state
	let trailName: string = '';
	let trailLink: string = '';
	let trailWandererId: string = '';
	let trailError: string = '';
	let isTrailLoading: boolean = false;
	let trailToEdit: Trail | null = null;
	let editingTrailName: string = '';
	let editingTrailLink: string = '';
	let editingTrailWandererId: string = '';
	let showAddTrailForm: boolean = false;
	let showWandererForm: boolean = false;
	let isWandererEnabled: boolean = false;
	let searchQuery: string = '';
	let isSearching: boolean = false;

	let wandererFetchedTrails: WandererTrail[] = [];

	const dispatch = createEventDispatcher();

	function updateTrailsList(newTrail: Trail) {
		trails = [...trails, newTrail];
	}

	async function createTrail() {
		isTrailLoading = true;

		// if wanderer ID is provided, use it and remove link
		if (trailWandererId.trim()) {
			trailLink = '';
		} else if (!trailLink.trim()) {
			trailError = $t('adventures.trail_link_required');
			isTrailLoading = false;
			return;
		}

		const trailData = {
			name: trailName.trim(),
			location: itemId,
			link: trailLink.trim() || null,
			wanderer_id: trailWandererId.trim() || null
		};

		try {
			const res = await fetch('/api/trails/', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(trailData)
			});

			if (res.ok) {
				const newTrail = await res.json();
				updateTrailsList(newTrail);
				addToast('success', $t('adventures.trail_created_successfully'));
				resetTrailForm();
			} else {
				const errorData = await res.json();
				throw new Error(errorData.message || 'Failed to create trail');
			}
		} catch (error) {
			console.error('Trail creation error:', error);
			trailError = error instanceof Error ? error.message : 'Failed to create trail';
			addToast('error', $t('adventures.trail_creation_failed'));
		} finally {
			isTrailLoading = false;
		}
	}

	function resetTrailForm() {
		trailName = '';
		trailLink = '';
		trailError = '';
		showAddTrailForm = false;
	}

	function startEditingTrail(trail: Trail) {
		trailToEdit = trail;
		editingTrailName = trail.name;
		editingTrailLink = trail.link || '';
		editingTrailWandererId = trail.wanderer_id || '';
	}

	function getDistance(meters: number) {
		// Convert meters to miles based measurement system
		if (measurementSystem === 'imperial') {
			return `${(meters * 0.000621371).toFixed(2)} mi`;
		} else {
			return `${(meters / 1000).toFixed(2)} km`;
		}
	}

	function getElevation(meters: number) {
		// Convert meters to feet based measurement system
		if (measurementSystem === 'imperial') {
			return `${(meters * 3.28084).toFixed(1)} ft`;
		} else {
			return `${meters.toFixed(1)} m`;
		}
	}

	function getDuration(minutes: number) {
		const hours = Math.floor(minutes / 60);
		const mins = minutes % 60;
		if (hours > 0) {
			return `${hours}h ${mins}m`;
		}
		return `${mins}m`;
	}

	function formatDate(dateString: string | number | Date) {
		return new Date(dateString).toLocaleDateString();
	}

	async function fetchWandererTrails(filter = '') {
		isSearching = true;
		try {
			const url = new URL('/api/integrations/wanderer/trails', window.location.origin);
			if (filter) {
				url.searchParams.append('filter', filter);
			}

			let res = await fetch(url, {
				method: 'GET'
			});

			if (res.ok) {
				let itemsResponse = await res.json();
				wandererFetchedTrails = itemsResponse.items || [];
			} else {
				const errorData = await res.json();
				addToast('error', errorData.message || $t('adventures.trail_fetch_failed'));
			}
		} catch (error) {
			addToast('error', $t('adventures.trail_fetch_failed'));
		} finally {
			isSearching = false;
		}
	}

	// Updated function to show wanderer form
	async function doShowWandererForm() {
		showWandererForm = true;
		showAddTrailForm = false;
		await fetchWandererTrails(); // Initial load without filter
	}

	// Function to handle search
	async function handleSearch() {
		if (!searchQuery.trim()) {
			// If search is empty, fetch all trails
			await fetchWandererTrails();
			return;
		}

		// Create filter string for name search (case-insensitive)
		const filter = `name~"${searchQuery}"`;
		await fetchWandererTrails(filter);
	}

	// Debounced search function (optional - for real-time search)
	let searchTimeout: string | number | NodeJS.Timeout | undefined;
	function debouncedSearch() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(handleSearch, 300); // 300ms delay
	}

	// Function to clear search
	async function clearSearch() {
		searchQuery = '';
		await fetchWandererTrails();
	}

	async function linkWandererTrail(event: CustomEvent<WandererTrail>) {
		const trail = event.detail;
		let trailId = trail.id;
		trailName = trail.name;
		trailLink = '';
		trailWandererId = trailId;
		trailError = '';
		createTrail();
	}

	function cancelEditingTrail() {
		trailToEdit = null;
		editingTrailName = '';
		editingTrailLink = '';
	}

	function validateEditTrailForm(): boolean {
		if (!editingTrailName.trim()) {
			return false;
		}

		const hasLink = editingTrailLink.trim() !== '';
		const hasWandererId = editingTrailWandererId.trim() !== '';

		if (hasLink && hasWandererId) {
			return false;
		}

		if (!hasLink && !hasWandererId) {
			return false;
		}

		return true;
	}

	async function saveTrailEdit() {
		if (!trailToEdit || !validateEditTrailForm()) return;

		const trailData = {
			name: editingTrailName.trim(),
			link: editingTrailLink.trim() || null,
			wanderer_id: editingTrailWandererId.trim() || null
		};

		try {
			const res = await fetch(`/api/trails/${trailToEdit.id}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(trailData)
			});

			if (res.ok) {
				const updatedTrail = await res.json();
				trails = trails.map((trail) => (trail.id === trailToEdit!.id ? updatedTrail : trail));
				addToast('success', $t('adventures.trail_updated_successfully'));
				cancelEditingTrail();
			} else {
				throw new Error('Failed to update trail');
			}
		} catch (error) {
			console.error('Error updating trail:', error);
			addToast('error', $t('adventures.trail_update_failed'));
		}
	}

	async function removeTrail(trailId: string) {
		try {
			const res = await fetch(`/api/trails/${trailId}`, {
				method: 'DELETE'
			});

			if (res.status === 204) {
				trails = trails.filter((trail) => trail.id !== trailId);
				addToast('success', $t('adventures.trail_removed_successfully'));
			} else {
				throw new Error('Failed to remove trail');
			}
		} catch (error) {
			console.error('Error removing trail:', error);
			addToast('error', $t('adventures.trail_removal_failed'));
		}
	}

	// Navigation handlers
	function handleBack() {
		dispatch('back');
	}

	function handleNext() {
		dispatch('next');
	}

	function handleImagesUpdated(event: CustomEvent<ContentImage[]>) {
		images = event.detail;
	}

	function handleAttachmentsUpdated(event: CustomEvent<Attachment[]>) {
		attachments = event.detail;
	}

	// Lifecycle
	onMount(async () => {
		try {
			const res = await fetch('/api/integrations');

			if (res.ok) {
				const data = await res.json();

				// Check Immich integration
				if (data.immich) {
					immichIntegration = true;
					// For copyImmichLocally, we might need to fetch specific details if needed
					// or set a default value since it's not in the new response structure
					copyImmichLocally = false;
				}

				// Check Wanderer integration
				if (data.wanderer && data.wanderer.exists && !data.wanderer.expired) {
					isWandererEnabled = true;
				}
			} else if (res.status !== 404) {
				addToast('error', $t('immich.integration_fetch_error'));
			}
		} catch (error) {
			console.error('Error checking integrations:', error);
		}
	});
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Image Management Section -->
		<ImageManagement
			bind:images
			objectId={itemId}
			contentType="location"
			defaultSearchTerm={itemName}
			{immichIntegration}
			{copyImmichLocally}
			{collaborativeMode}
			on:imagesUpdated={handleImagesUpdated}
			bind:importInProgress
		/>

		<!-- Attachment Management Section -->
		<AttachmentManagement
			bind:attachments
			{itemId}
			contentType="location"
			on:attachmentsUpdated={handleAttachmentsUpdated}
		/>

		<!-- Trails Management -->
		<div class="card bg-base-100 border border-base-300 shadow-lg">
			<div class="card-body p-6">
				<div class="flex items-center justify-between mb-6">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-accent/10 rounded-lg">
							<SwapHorizontalVariantIcon class="w-5 h-5 text-accent" />
						</div>
						<h2 class="text-xl font-bold">{$t('adventures.trails_management')}</h2>
					</div>
					<div class="flex items-center gap-2">
						<button
							class="btn btn-accent btn-sm gap-2"
							on:click={() => {
								showAddTrailForm = !showAddTrailForm;
								if (showAddTrailForm) showWandererForm = false;
							}}
						>
							<PlusIcon class="w-4 h-4" />
							{$t('adventures.add_trail')}
						</button>
						{#if userIsOwner}
							<button
								class="btn btn-accent btn-sm gap-2"
								on:click={() => {
									doShowWandererForm();
								}}
							>
								<PlusIcon class="w-4 h-4" />
								{$t('adventures.add_wanderer_trail')}
							</button>
						{/if}
					</div>
				</div>

				<div class="text-sm text-base-content/60 mb-4">
					{$t('adventures.trails_management_description')}
				</div>

				<!-- Add Trail Form -->
				{#if showAddTrailForm}
					<div class="bg-accent/5 p-4 rounded-lg border border-accent/20 mb-6">
						<h4 class="font-medium mb-3 text-accent">{$t('adventures.add_new_trail')}</h4>
						<div class="grid gap-3">
							<input
								type="text"
								bind:value={trailName}
								class="input input-bordered"
								placeholder="Trail name"
								disabled={isTrailLoading}
							/>
							<input
								type="url"
								bind:value={trailLink}
								class="input input-bordered"
								placeholder={$t('adventures.external_link') + ' (AllTrails, Trailforks, etc.)'}
								disabled={isTrailLoading}
							/>
							{#if trailError}
								<div class="alert alert-error py-2">
									<span class="text-sm">{trailError}</span>
								</div>
							{/if}
							<div class="flex gap-2 justify-end">
								<button
									class="btn btn-ghost btn-sm"
									disabled={isTrailLoading}
									on:click={resetTrailForm}
								>
									{$t('adventures.cancel')}
								</button>
								<button
									class="btn btn-accent btn-sm"
									class:loading={isTrailLoading}
									disabled={isTrailLoading || !trailName.trim() || !trailLink.trim()}
									on:click={createTrail}
								>
									{$t('adventures.create_trail')}
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Wanderer Trails Form -->
				{#if showWandererForm}
					<div class="bg-accent/5 p-4 rounded-lg border border-accent/20 mb-6">
						<h4 class="font-medium mb-3 text-accent">{$t('adventures.add_wanderer_trail')}</h4>
						<div class="grid gap-3">
							{#if isWandererEnabled}
								<p class="text-sm text-base-content/60 mb-2">
									{$t('adventures.select_wanderer_trail')}:
								</p>

								<!-- Search Box -->
								<div class="relative">
									<input
										type="text"
										placeholder={$t('adventures.search_trails_placeholder') + '...'}
										class="input input-bordered w-full pr-20"
										bind:value={searchQuery}
										on:input={debouncedSearch}
										on:keydown={(e) => e.key === 'Enter' && handleSearch()}
									/>
									<div class="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
										{#if searchQuery}
											<button
												class="btn btn-ghost btn-xs btn-circle"
												on:click={clearSearch}
												disabled={isSearching}
												title="Clear search"
											>
												✕
											</button>
										{/if}
										<button
											class="btn btn-accent btn-xs"
											class:loading={isSearching}
											on:click={handleSearch}
											disabled={isSearching}
											title="Search"
										>
											{#if !isSearching}🔍{/if}
										</button>
									</div>
								</div>

								<!-- Search Status -->
								{#if searchQuery && !isSearching}
									<p class="text-xs text-base-content/50">
										{wandererFetchedTrails.length}
										{$t('adventures.trails_found_for')}{searchQuery}
									</p>
								{/if}

								<!-- Trail Cards -->
								<div class="max-h-96 overflow-y-auto">
									{#if isSearching}
										<div class="flex justify-center py-8">
											<span class="loading loading-spinner loading-md"></span>
										</div>
									{:else if wandererFetchedTrails.length === 0}
										<div class="text-center py-8 text-base-content/60">
											{#if searchQuery}
												{$t('adventures.no_trails_found_matching')} "{searchQuery}"
											{:else}
												{$t('adventures.no_trails_available')}
											{/if}
										</div>
									{:else}
										<div class="space-y-3">
											{#each wandererFetchedTrails as trail (trail.id)}
												<WandererCard {trail} on:link={linkWandererTrail} />
											{/each}
										</div>
									{/if}
								</div>
							{:else}
								<p class="text-sm text-base-content/60">
									{$t('adventures.wanderer_integration_error')}
								</p>
							{/if}

							<div class="flex gap-2 justify-end">
								<button
									class="btn btn-accent btn-sm"
									on:click={() => {
										showWandererForm = false;
										showAddTrailForm = false;
										searchQuery = ''; // Clear search when closing
									}}
								>
									{$t('about.close')}
								</button>
							</div>
						</div>
					</div>
				{/if}

				<!-- Trails Gallery -->
				{#if trails.length > 0}
					<div class="divider">Current Trails</div>
					<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
						{#each trails as trail (trail.id)}
							<div class="relative group">
								{#if trailToEdit?.id === trail.id}
									<!-- Edit Mode -->
									<div class="bg-warning/10 p-4 rounded-lg border border-warning/30">
										<div class="flex items-center gap-2 mb-3">
											<EditIcon class="w-4 h-4 text-warning" />
											<span class="text-sm font-medium text-warning">Editing Trail</span>
										</div>
										<div class="grid gap-3">
											<input
												type="text"
												bind:value={editingTrailName}
												class="input input-bordered input-sm"
												placeholder={$t('adventures.trail_name')}
											/>
											<input
												type="url"
												bind:value={editingTrailLink}
												class="input input-bordered input-sm"
												placeholder={$t('adventures.external_link')}
												disabled={editingTrailWandererId.trim() !== ''}
											/>
										</div>
										<div class="flex gap-2 mt-3">
											<button
												class="btn btn-success btn-xs flex-1"
												disabled={!validateEditTrailForm()}
												on:click={saveTrailEdit}
											>
												<CheckIcon class="w-3 h-3" />
												{$t('notes.save')}
											</button>
											<button class="btn btn-ghost btn-xs flex-1" on:click={cancelEditingTrail}>
												<CloseIcon class="w-3 h-3" />
												{$t('adventures.cancel')}
											</button>
										</div>
									</div>
								{:else}
									<!-- Normal Display -->
									<div
										class="bg-base-50 p-4 rounded-lg border border-base-200 hover:border-base-300 transition-colors"
									>
										<!-- Header -->
										<div class="flex items-center gap-3 mb-3">
											<div class="p-2 bg-accent/10 rounded">
												{#if trail.wanderer_id}
													<Star class="w-4 h-4 text-accent" />
												{:else}
													<LinkIcon class="w-4 h-4 text-accent" />
												{/if}
											</div>
											<div class="flex-1 min-w-0">
												<div class="font-medium truncate">{trail.name}</div>
												<div class="text-xs text-accent/70 mt-1">
													{trail.provider || 'External'}
												</div>
											</div>
										</div>

										<!-- Wanderer Trail Enhanced Data -->
										{#if trail.wanderer_data}
											<div class="mb-4 space-y-3">
												<!-- Trail Stats -->
												<div class="grid grid-cols-2 gap-3">
													<div class="flex items-center gap-2 text-sm">
														<MapPin class="w-3 h-3 text-base-content/60" />
														<span class="text-base-content/80">
															{getDistance(trail.wanderer_data.distance)}
														</span>
													</div>
													{#if trail.wanderer_data.duration > 0}
														<div class="flex items-center gap-2 text-sm">
															<Clock class="w-3 h-3 text-base-content/60" />
															<span class="text-base-content/80">
																{getDuration(trail.wanderer_data.duration)}
															</span>
														</div>
													{/if}
													{#if trail.wanderer_data.elevation_gain > 0}
														<div class="flex items-center gap-2 text-sm">
															<TrendingUp class="w-3 h-3 text-base-content/60" />
															<span class="text-base-content/80">
																{getElevation(trail.wanderer_data.elevation_gain)} gain
															</span>
														</div>
													{/if}
													<div class="flex items-center gap-2 text-sm">
														<Calendar class="w-3 h-3 text-base-content/60" />
														<span class="text-base-content/80">
															{formatDate(trail.wanderer_data.date)}
														</span>
													</div>
												</div>

												<!-- Difficulty Badge -->
												{#if trail.wanderer_data.difficulty}
													<div class="flex items-center gap-2">
														<span
															class="badge badge-sm"
															class:badge-success={trail.wanderer_data.difficulty === 'easy'}
															class:badge-warning={trail.wanderer_data.difficulty === 'moderate'}
															class:badge-error={trail.wanderer_data.difficulty === 'hard'}
														>
															{trail.wanderer_data.difficulty}
														</span>
														{#if trail.wanderer_data.like_count > 0}
															<div class="flex items-center gap-1 text-xs text-base-content/60">
																<Users class="w-3 h-3" />
																{trail.wanderer_data.like_count} likes
															</div>
														{/if}
													</div>
												{/if}

												<!-- Description -->
												{#if trail.wanderer_data.description}
													<div class="text-sm text-base-content/70 leading-relaxed">
														{@html trail.wanderer_data.description}
													</div>
												{/if}

												<!-- Location -->
												{#if trail.wanderer_data.location}
													<div class="text-xs text-base-content/60 flex items-center gap-1">
														<MapPin class="w-3 h-3" />
														{trail.wanderer_data.location}
													</div>
												{/if}

												<!-- Photos indicator -->
												{#if trail.wanderer_data.photos && trail.wanderer_data.photos.length > 0}
													<div class="flex items-center gap-1 text-xs text-base-content/60">
														<Camera class="w-3 h-3" />
														{trail.wanderer_data.photos.length} photo{trail.wanderer_data.photos
															.length > 1
															? 's'
															: ''}
													</div>
												{/if}
											</div>
										{/if}

										<!-- External Link -->
										{#if trail.link}
											<a
												href={trail.link}
												target="_blank"
												rel="noopener noreferrer"
												class="text-xs text-accent hover:text-accent-focus mb-3 break-all block underline"
											>
												{trail.link}
											</a>
										{:else if !trail.wanderer_id}
											<div class="text-xs text-base-content/40 mb-3 italic">
												{$t('adventures.no_external_link')}
											</div>
										{/if}

										<!-- Trail Controls -->
										<div class="flex gap-2 justify-end">
											{#if !trail.wanderer_id}
												<button
													type="button"
													class="btn btn-warning btn-xs btn-square tooltip tooltip-top"
													data-tip="Edit Trail"
													on:click={() => startEditingTrail(trail)}
												>
													<EditIcon class="w-3 h-3" />
												</button>
											{/if}
											<button
												type="button"
												class="btn btn-error btn-xs btn-square tooltip tooltip-top"
												data-tip="Remove Trail"
												on:click={() => removeTrail(trail.id)}
											>
												<TrashIcon class="w-3 h-3" />
											</button>
										</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="bg-base-200/50 rounded-lg p-8 text-center">
						<div class="text-base-content/60 mb-2">{$t('adventures.no_trails_added')}</div>
						<div class="text-sm text-base-content/40">
							{$t('adventures.add_first_trail')}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack} disabled={importInProgress}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>

			<button class="btn btn-primary gap-2" on:click={handleNext} disabled={importInProgress}>
				<SaveIcon class="w-5 h-5" />
				{$t('adventures.continue')}
			</button>
		</div>
	</div>
</div>
