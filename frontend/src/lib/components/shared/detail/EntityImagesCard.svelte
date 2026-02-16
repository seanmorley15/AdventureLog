<script lang="ts">
	import { t } from 'svelte-i18n';
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let images: { image: string; is_primary?: boolean; user_username?: string }[] = [];
	export let title: string = $t('adventures.images') || 'Images';
	export let icon: string = '🖼️';
	export let columns: number = 2; // 2 for sidebar, 3 for main content
	export let showPrimaryBadge: boolean = true;
	export let showUserBadge: boolean = true;

	function openImageModal(index: number) {
		dispatch('openImage', index);
	}

	$: gridClass = columns === 2
		? 'grid-cols-2'
		: columns === 3
			? 'grid-cols-2 sm:grid-cols-3'
			: 'grid-cols-2';
</script>

{#if images && images.length > 0}
	<div class="card bg-base-200 shadow-xl">
		<div class="card-body">
			<h3 class="card-title text-lg mb-4">{icon} {title}</h3>
			<div class="grid {gridClass} gap-2">
				{#each images as image, index}
					<div class="relative group">
						<button
							class="aspect-square rounded-lg overflow-hidden hover:opacity-80 transition-opacity w-full"
							on:click={() => openImageModal(index)}
						>
							<img
								src={image.image}
								alt={`Image ${index + 1}`}
								class="w-full h-full object-cover"
							/>
						</button>
						{#if showPrimaryBadge && image.is_primary}
							<div class="absolute top-1 right-1">
								<span class="badge badge-primary badge-xs">{$t('settings.primary')}</span>
							</div>
						{/if}
						{#if showUserBadge && image.user_username}
							<a href="/profile/{image.user_username}" class="absolute bottom-1 left-1">
								<span class="badge badge-neutral badge-xs opacity-80 hover:badge-primary transition-colors">{image.user_username}</span>
							</a>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
