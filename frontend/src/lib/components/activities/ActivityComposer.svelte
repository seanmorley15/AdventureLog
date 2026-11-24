<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import { apiErrorMessage } from '#lib/api/index.js';
	import { SPORT_TYPE_CHOICES } from '#lib';
	import { localTimeZone } from '#lib/dateUtils.js';
	import { addToast } from '#lib/toasts.js';
	import type { Activity, ActivityAnalysis, StravaActivity, Trail } from '#lib/types.js';
	import ActivityForm from './ActivityForm.svelte';
	import ActivityImportList from './ActivityImportList.svelte';
	import ActivitySourcePicker from './ActivitySourcePicker.svelte';
	import ActivityTrackPreview from './ActivityTrackPreview.svelte';
	import {
		applyAnalysis,
		applyProviderActivity,
		defaultActivityName,
		draftFromActivity,
		draftToFormData,
		emptyDraft,
		type FieldSources
	} from './activityForm.js';
	import AlertIcon from '~icons/mdi/alert-outline';
	import ArrowLeftIcon from '~icons/mdi/arrow-left';
	import FileIcon from '~icons/mdi/file-outline';
	import LoadingIcon from '~icons/mdi/loading';
	import SaveIcon from '~icons/mdi/content-save';
	import SwapIcon from '~icons/mdi/swap-horizontal';

	interface Props {
		/** Where a new activity goes: exactly one of a visit, a trip day, or a collection's Ideas. */
		visitId?: string | null;
		dayId?: string | null;
		collectionId?: string | null;
		/** Edit this saved activity instead of adding one. */
		activity?: Activity | null;
		/** The visit or day, used to find Strava and Endurain activities from around then. */
		dateStart?: string | null;
		dateEnd?: string | null;
		timezone?: string | null;
		trails?: Trail[];
		measurementSystem?: 'metric' | 'imperial';
		/** `external_service_id`s already saved here, so an import list can mark them. */
		importedIds?: string[];
		onSaved: (activity: Activity) => void;
		onCancel?: () => void;
	}

	let {
		visitId = null,
		dayId = null,
		collectionId = null,
		activity = null,
		dateStart = null,
		dateEnd = null,
		timezone = null,
		trails = [],
		measurementSystem = 'metric',
		importedIds = [],
		onSaved,
		onCancel
	}: Props = $props();

	const editing = $derived(activity !== null);
	const zone = $derived(timezone || localTimeZone());
	const context = $derived({ units: measurementSystem, timezone: zone });

	type Step = 'source' | 'import' | 'review';
	let step = $state<Step>(untrack(() => (activity ? 'review' : 'source')));
	let provider = $state<'strava' | 'endurain'>('strava');
	let stravaEnabled = $state(false);
	let endurainEnabled = $state(false);

	let draft = $state(
		untrack(() =>
			activity
				? draftFromActivity(activity, { units: measurementSystem, timezone: zone })
				: emptyDraft(zone)
		)
	);
	let sources = $state<FieldSources>({});
	let analysis = $state<ActivityAnalysis | null>(null);
	let file = $state<File | null>(null);

	let reading = $state(false);
	let importingId = $state<string | null>(null);
	let saving = $state(false);

	const previewGeojson = $derived(analysis?.geojson ?? (editing ? activity?.geojson : null));
	const sportLabel = (key: string) =>
		SPORT_TYPE_CHOICES.find((choice) => choice.key === key)?.label ?? key;

	function suggestName() {
		if (draft.name.trim()) return;
		draft.name = defaultActivityName(sportLabel(draft.sportType), draft.startDate, (key, values) =>
			$t(key, values ? { values } : undefined)
		);
	}

	/** Read a track file and fill the form from it. Returns whether the file was readable. */
	async function readFile(selected: File): Promise<boolean> {
		reading = true;
		try {
			const body = new FormData();
			body.append('file', selected);
			const response = await fetch('/api/activities/analyze/', { method: 'POST', body });
			const data = await response.json().catch(() => null);
			if (!response.ok) {
				addToast('error', apiErrorMessage(data, $t('activities.read_failed')));
				return false;
			}
			const result = applyAnalysis(draft, data as ActivityAnalysis, context, { keepName: editing });
			draft = result.draft;
			sources = result.sources;
			analysis = data as ActivityAnalysis;
			file = selected;
			suggestName();
			return true;
		} catch (error) {
			console.error(error);
			addToast('error', $t('activities.read_failed'));
			return false;
		} finally {
			reading = false;
		}
	}

	async function chooseFile(selected: File) {
		if (await readFile(selected)) step = 'review';
	}

	function chooseManual() {
		step = 'review';
	}

	function chooseProvider(name: 'strava' | 'endurain') {
		provider = name;
		step = 'import';
	}

	/** Fetch the activity's track from AdventureLog (which builds it), read it, then lay the provider's totals over it. */
	async function importActivity(imported: StravaActivity) {
		importingId = String(imported.id);
		try {
			const response = await fetch(imported.export_gpx);
			if (response.ok) {
				const track = new File([await response.blob()], `${provider}-${imported.id}.gpx`, {
					type: 'application/gpx+xml'
				});
				await readFile(track);
			} else {
				addToast('info', $t('activities.no_track_summary_only'));
			}
			const merged = applyProviderActivity(draft, sources, imported, context);
			draft = merged.draft;
			sources = merged.sources;
			step = 'review';
		} catch (error) {
			console.error(error);
			addToast('error', $t('activities.read_failed'));
		} finally {
			importingId = null;
		}
	}

	async function save() {
		if (!draft.name.trim()) {
			addToast('error', $t('adventures.activity_name_required'));
			return;
		}
		saving = true;
		try {
			const body = draftToFormData(draft, {
				units: measurementSystem,
				visitId,
				dayId,
				collectionId,
				file,
				clearEmpty: editing
			});
			const response = await fetch(
				editing ? `/api/activities/${activity?.id}/` : '/api/activities/',
				{
					method: editing ? 'PATCH' : 'POST',
					body
				}
			);
			const data = await response.json().catch(() => null);
			if (!response.ok) {
				addToast('error', apiErrorMessage(data, $t('adventures.activity_upload_error')));
				return;
			}
			addToast('success', $t('adventures.activity_upload_success'));
			onSaved(data as Activity);
		} catch (error) {
			console.error(error);
			addToast('error', $t('adventures.activity_upload_error'));
		} finally {
			saving = false;
		}
	}

	onMount(async () => {
		if (editing) return;
		try {
			const response = await fetch('/api/integrations');
			if (response.ok) {
				const integrations = await response.json();
				stravaEnabled = Boolean(integrations.strava?.user);
				endurainEnabled = Boolean(integrations.endurain?.exists);
			}
		} catch {
			stravaEnabled = false;
			endurainEnabled = false;
		}
	});
</script>

<div class="space-y-4">
	{#if step === 'source'}
		<ActivitySourcePicker
			{stravaEnabled}
			{endurainEnabled}
			busy={reading}
			onFile={chooseFile}
			onProvider={chooseProvider}
			onManual={chooseManual}
		/>
		{#if onCancel}
			<div class="flex justify-end">
				<button type="button" class="btn btn-ghost btn-sm" onclick={onCancel}>
					{$t('adventures.cancel')}
				</button>
			</div>
		{/if}
	{:else if step === 'import'}
		<ActivityImportList
			{provider}
			{dateStart}
			{dateEnd}
			{importedIds}
			{measurementSystem}
			{importingId}
			onImport={importActivity}
			onBack={() => (step = 'source')}
		/>
	{:else}
		<div
			class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-base-200/60 px-3 py-2"
		>
			<div class="flex min-w-0 items-center gap-2 text-sm">
				<FileIcon class="h-4 w-4 shrink-0 text-primary" />
				<span class="truncate">
					{#if file}
						{file.name}
						<span class="badge badge-ghost badge-sm ml-1 uppercase">{analysis?.format}</span>
					{:else if activity?.gpx_file}
						{$t('activities.current_track')}
					{:else}
						{$t('activities.no_track')}
					{/if}
				</span>
			</div>
			<label class="btn btn-ghost btn-sm gap-1 {reading ? 'btn-disabled' : ''}">
				{#if reading}
					<LoadingIcon class="h-4 w-4 animate-spin" />
				{:else}
					<SwapIcon class="h-4 w-4" />
				{/if}
				{file || activity?.gpx_file ? $t('activities.replace_file') : $t('activities.add_file')}
				<input
					type="file"
					class="sr-only"
					accept=".gpx,.fit,.tcx,.kml,.kmz"
					disabled={reading}
					onchange={(event) => {
						const selected = event.currentTarget.files?.[0];
						event.currentTarget.value = '';
						if (selected) void readFile(selected);
					}}
				/>
			</label>
		</div>

		{#each analysis?.warnings ?? [] as warning (warning)}
			<div class="alert alert-warning py-2 text-sm">
				<AlertIcon class="h-4 w-4 shrink-0" />
				<span>{$t(`activities.warning_${warning}`)}</span>
			</div>
		{/each}

		{#if previewGeojson}
			<ActivityTrackPreview
				geojson={previewGeojson}
				sportType={draft.sportType}
				{measurementSystem}
			/>
		{/if}

		<ActivityForm bind:draft {sources} {trails} {measurementSystem} />

		<div class="flex items-center justify-between gap-2 pt-2">
			{#if !editing}
				<button
					type="button"
					class="btn btn-ghost btn-sm gap-1"
					disabled={saving}
					onclick={() => (step = 'source')}
				>
					<ArrowLeftIcon class="h-4 w-4" />
					{$t('adventures.back')}
				</button>
			{:else}
				<span></span>
			{/if}
			<div class="flex gap-2">
				{#if onCancel}
					<button type="button" class="btn btn-ghost btn-sm" disabled={saving} onclick={onCancel}>
						{$t('adventures.cancel')}
					</button>
				{/if}
				<button
					type="button"
					class="btn btn-success btn-sm gap-2"
					disabled={saving || reading || !draft.name.trim()}
					onclick={save}
				>
					{#if saving}
						<LoadingIcon class="h-4 w-4 animate-spin" />
					{:else}
						<SaveIcon class="h-4 w-4" />
					{/if}
					{editing ? $t('activities.save_changes') : $t('adventures.upload_activity')}
				</button>
			</div>
		</div>
	{/if}
</div>
