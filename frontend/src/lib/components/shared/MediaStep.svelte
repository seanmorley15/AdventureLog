<script lang="ts">
	import type { Attachment, ContentImage, User } from '$lib/types';
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	// Icons
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import CheckIcon from '~icons/mdi/check';

	import { addToast } from '$lib/toasts';
	import ImageManagement from '../ImageManagement.svelte';
	import AttachmentManagement from '../AttachmentManagement.svelte';

	// Props
	export let images: ContentImage[] = [];
	export let attachments: Attachment[] = [];
	export let itemName: string = '';
	export let itemId: string = '';
	export let contentType: 'location' | 'lodging' | 'transportation' | '' = 'location';
	export let user: User | null = null;
	export let collaborativeMode: boolean = false;

	export let start_date: string | null = null;
	export let end_date: string | null = null;
	// export let measurementSystem: 'metric' | 'imperial' = 'metric';
	// export let user: User | null = null;

	// Component state
	let immichIntegration: boolean = false;
	let copyImmichLocally: boolean = false;
	let importInProgress: boolean = false;

	const dispatch = createEventDispatcher();

	// Navigation handlers
	function handleBack() {
		dispatch('back');
	}

	function handleClose() {
		dispatch('close');
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
			} else if (res.status !== 404) {
				addToast('error', $t('immich.integration_fetch_error'));
			}
		} catch (error) {
			console.error('Error checking integrations:', error);
		}

		// prefilled import moved into ImageManagement; no-op here
	});
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Image Management Section -->
		<ImageManagement
			bind:images
			objectId={itemId}
			{contentType}
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
			{contentType}
			on:attachmentsUpdated={handleAttachmentsUpdated}
			{start_date}
			{end_date}
			{user}
		/>

		<!-- Action Buttons -->
		<div class="flex gap-3 justify-end pt-4">
			<button class="btn btn-neutral-200 gap-2" on:click={handleBack} disabled={importInProgress}>
				<ArrowLeftIcon class="w-5 h-5" />
				{$t('adventures.back')}
			</button>

			<button class="btn btn-primary gap-2" on:click={handleClose} disabled={importInProgress}>
				<CheckIcon class="w-5 h-5" />
				{$t('adventures.done')}
			</button>
		</div>
	</div>
</div>
