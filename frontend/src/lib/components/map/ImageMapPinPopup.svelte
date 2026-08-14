<!-- @migration-task Error while migrating Svelte code: migrating this component would require adding a `$props` rune but there's already a variable named props.
     Rename the variable and try again or migrate by hand. -->
<script lang="ts">
	import { t } from 'svelte-i18n';
	import CameraIcon from '~icons/mdi/camera';
	import type { ImagePinProperties } from '$lib/map/imagePins';
	import { getImagePinParentTypeKey } from '$lib/map/imagePins';

	export let props: ImagePinProperties;
	export let visible = false;

	$: title = props.parentName || $t('images.map_pin_title');
	$: parentTypeLabel = $t(getImagePinParentTypeKey(props.parentType));
</script>

<div
	class="absolute bottom-full left-1/2 z-[9999] mb-2 w-max max-w-[min(18rem,calc(100vw-2rem))] -translate-x-1/2 pointer-events-none opacity-0 transition-all duration-200 group-hover:opacity-100 group-focus-within:opacity-100"
	class:opacity-100={visible}
	role="tooltip"
	aria-label={title}
>
	<div
		class="card card-compact overflow-hidden border border-base-300 bg-base-100 shadow-xl ring-1 ring-base-content/5"
	>
		<figure class="relative aspect-[4/3] bg-base-200">
			<img src={props.imageUrl} alt="" class="h-full w-full object-cover" loading="lazy" />
			<div
				class="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-black/45 to-transparent"
			></div>
			<div class="absolute bottom-2 left-2">
				<span class="badge badge-sm border-0 bg-black/55 text-white gap-1">
					<CameraIcon class="h-3.5 w-3.5" aria-hidden="true" />
					{$t('map.photos')}
				</span>
			</div>
		</figure>

		<div class="card-body gap-2.5 p-3">
			<div class="min-w-0 space-y-2">
				<h3 class="text-sm font-semibold leading-tight text-base-content truncate">{title}</h3>
				<div class="flex flex-wrap items-center gap-1.5">
					<span class="badge badge-error badge-sm badge-outline">{parentTypeLabel}</span>
					{#if props.isPrimary}
						<span class="badge badge-primary badge-sm">Primary</span>
					{/if}
				</div>
			</div>
		</div>
	</div>
</div>
