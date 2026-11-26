<script lang="ts">
	import { t } from 'svelte-i18n';
	import FileUploadIcon from '~icons/mdi/file-upload-outline';
	import PencilIcon from '~icons/mdi/pencil-outline';
	import LoadingIcon from '~icons/mdi/loading';

	interface Props {
		stravaEnabled?: boolean;
		endurainEnabled?: boolean;
		/** A file is being read. */
		busy?: boolean;
		onFile: (file: File) => void;
		onProvider: (provider: 'strava' | 'endurain') => void;
		onManual: () => void;
	}

	let {
		stravaEnabled = false,
		endurainEnabled = false,
		busy = false,
		onFile,
		onProvider,
		onManual
	}: Props = $props();

	/** What the server reads. Keep in step with `SUPPORTED_EXTENSIONS` in the backend. */
	const ACCEPT = '.gpx,.fit,.tcx,.kml,.kmz';

	let dragging = $state(false);

	function pick(files: FileList | null | undefined) {
		const file = files?.[0];
		if (file && !busy) onFile(file);
	}
</script>

<div class="space-y-4">
	<label
		class="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-10 text-center transition-colors focus-within:ring-2 focus-within:ring-primary {dragging
			? 'border-primary bg-primary/10'
			: 'border-base-300 bg-base-200/40 hover:border-primary/60 hover:bg-base-200'} {busy
			? 'pointer-events-none opacity-70'
			: ''}"
		ondragover={(event) => {
			event.preventDefault();
			dragging = true;
		}}
		ondragleave={() => (dragging = false)}
		ondrop={(event) => {
			event.preventDefault();
			dragging = false;
			pick(event.dataTransfer?.files);
		}}
	>
		{#if busy}
			<LoadingIcon class="h-10 w-10 animate-spin text-primary" />
			<span class="font-semibold">{$t('activities.reading_file')}</span>
		{:else}
			<FileUploadIcon class="h-10 w-10 text-primary" />
			<span class="text-lg font-semibold">{$t('activities.drop_file')}</span>
			<span class="text-sm text-base-content/70">{$t('activities.drop_file_hint')}</span>
			<span class="mt-1 flex flex-wrap justify-center gap-1">
				{#each ['GPX', 'FIT', 'TCX', 'KML', 'KMZ'] as format (format)}
					<span class="badge badge-outline badge-sm">{format}</span>
				{/each}
			</span>
		{/if}
		<input
			type="file"
			class="sr-only"
			accept={ACCEPT}
			disabled={busy}
			onchange={(event) => {
				pick(event.currentTarget.files);
				event.currentTarget.value = '';
			}}
		/>
	</label>

	{#if stravaEnabled || endurainEnabled}
		<div class="divider my-2 text-xs text-base-content/60">{$t('activities.or_import_from')}</div>
		<div class="flex flex-wrap justify-center gap-2">
			{#if stravaEnabled}
				<button type="button" class="btn btn-outline btn-sm" onclick={() => onProvider('strava')}>
					Strava
				</button>
			{/if}
			{#if endurainEnabled}
				<button type="button" class="btn btn-outline btn-sm" onclick={() => onProvider('endurain')}>
					Endurain
				</button>
			{/if}
		</div>
	{/if}

	<div class="text-center">
		<button type="button" class="btn btn-ghost btn-sm gap-2" disabled={busy} onclick={onManual}>
			<PencilIcon class="h-4 w-4" />
			{$t('activities.enter_manually')}
		</button>
	</div>
</div>
