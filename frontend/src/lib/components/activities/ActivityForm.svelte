<script lang="ts">
	import { t } from 'svelte-i18n';
	import { SPORT_TYPE_CHOICES } from '#lib';
	import type { ActivityValueSource, Trail } from '#lib/types.js';
	import DateInput from '#lib/components/shared/DateInput.svelte';
	import DurationInput from '#lib/components/shared/DurationInput.svelte';
	import TimezoneSelector from '#lib/components/TimezoneSelector.svelte';
	import type { ActivityDraft, FieldSources } from './activityForm.js';

	interface Props {
		draft: ActivityDraft;
		/** Where each filled value came from, by API field name. */
		sources?: FieldSources;
		trails?: Trail[];
		measurementSystem?: 'metric' | 'imperial';
	}

	let {
		draft = $bindable(),
		sources = {},
		trails = [],
		measurementSystem = 'metric'
	}: Props = $props();

	const imperial = $derived(measurementSystem === 'imperial');
	const distanceUnit = $derived(imperial ? 'mi' : 'km');
	const elevationUnit = $derived(imperial ? 'ft' : 'm');
	const speedUnit = $derived(imperial ? 'mph' : 'km/h');

	let showMore = $state(false);

	const sourceLabel = (source: ActivityValueSource) =>
		source === 'device' ? $t('activities.from_device') : $t('activities.from_file');
</script>

{#snippet label(id: string, text: string, field: string)}
	<label class="field-label flex items-center justify-between gap-2" for={id}>
		<span>{text}</span>
		{#if sources[field]}
			<span class="badge badge-ghost badge-xs font-normal">{sourceLabel(sources[field])}</span>
		{/if}
	</label>
{/snippet}

<div class="space-y-6">
	<section class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<div class="md:col-span-2">
			<label class="field-label" for="activity-name">{$t('adventures.activity_name')}</label>
			<input
				id="activity-name"
				class="input mt-1 w-full"
				placeholder={$t('adventures.activity_name_placeholder')}
				bind:value={draft.name}
				required
			/>
		</div>
		<div>
			{@render label('sport-type', $t('adventures.sport_type'), 'sport_type')}
			<select id="sport-type" class="select mt-1 w-full" bind:value={draft.sportType}>
				{#each SPORT_TYPE_CHOICES as choice (choice.key)}
					<option value={choice.key}>{choice.icon} {choice.label}</option>
				{/each}
			</select>
		</div>
		<div>
			{@render label('activity-start', $t('adventures.start_date'), 'start_date')}
			<DateInput id="activity-start" bind:value={draft.startDate} showTime size="sm" />
		</div>
		<div class={trails.length ? '' : 'md:col-span-2'}>
			<TimezoneSelector bind:selectedTimezone={draft.timezone} size="sm" />
		</div>
		{#if trails.length}
			<div>
				<label class="field-label" for="activity-trail">{$t('adventures.trail')}</label>
				<select id="activity-trail" class="select mt-1 w-full" bind:value={draft.trailId}>
					<option value="">{$t('activities.no_trail')}</option>
					{#each trails as trail (trail.id)}
						<option value={trail.id}>{trail.name}</option>
					{/each}
				</select>
			</div>
		{/if}
	</section>

	<section class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<div>
			{@render label('distance', `${$t('adventures.distance')} (${distanceUnit})`, 'distance')}
			<input
				id="distance"
				type="number"
				step="0.01"
				min="0"
				class="input mt-1 w-full"
				bind:value={draft.distance}
			/>
		</div>
		<div>
			{@render label('moving-time', $t('adventures.moving_time'), 'moving_time')}
			<DurationInput id="moving-time" bind:value={draft.movingTime} />
		</div>
		<div>
			{@render label(
				'elevation-gain',
				`${$t('adventures.elevation_gain')} (${elevationUnit})`,
				'elevation_gain'
			)}
			<input
				id="elevation-gain"
				type="number"
				min="0"
				class="input mt-1 w-full"
				bind:value={draft.elevationGain}
			/>
		</div>
		<div>
			{@render label('elapsed-time', $t('adventures.elapsed_time'), 'elapsed_time')}
			<DurationInput id="elapsed-time" bind:value={draft.elapsedTime} />
		</div>
		<div>
			{@render label(
				'elevation-loss',
				`${$t('adventures.elevation_loss')} (${elevationUnit})`,
				'elevation_loss'
			)}
			<input
				id="elevation-loss"
				type="number"
				min="0"
				class="input mt-1 w-full"
				bind:value={draft.elevationLoss}
			/>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				{@render label(
					'elev-high',
					`${$t('adventures.elevation_high')} (${elevationUnit})`,
					'elev_high'
				)}
				<input id="elev-high" type="number" class="input mt-1 w-full" bind:value={draft.elevHigh} />
			</div>
			<div>
				{@render label(
					'elev-low',
					`${$t('adventures.elevation_low')} (${elevationUnit})`,
					'elev_low'
				)}
				<input id="elev-low" type="number" class="input mt-1 w-full" bind:value={draft.elevLow} />
			</div>
		</div>
	</section>

	<section>
		<button
			type="button"
			class="btn btn-ghost btn-sm"
			aria-expanded={showMore}
			onclick={() => (showMore = !showMore)}
		>
			{showMore ? $t('adventures.hide_details') : $t('adventures.more_details')}
		</button>
		{#if showMore}
			<div class="mt-3 grid grid-cols-1 gap-4 md:grid-cols-2">
				<div>
					{@render label(
						'average-speed',
						`${$t('adventures.average_speed')} (${speedUnit})`,
						'average_speed'
					)}
					<input
						id="average-speed"
						type="number"
						step="0.1"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.averageSpeed}
					/>
				</div>
				<div>
					{@render label('max-speed', `${$t('adventures.max_speed')} (${speedUnit})`, 'max_speed')}
					<input
						id="max-speed"
						type="number"
						step="0.1"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.maxSpeed}
					/>
				</div>
				<div>
					{@render label(
						'average-hr',
						`${$t('activities.average_heart_rate')} (bpm)`,
						'average_heart_rate'
					)}
					<input
						id="average-hr"
						type="number"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.averageHeartRate}
					/>
				</div>
				<div>
					{@render label('max-hr', `${$t('activities.max_heart_rate')} (bpm)`, 'max_heart_rate')}
					<input
						id="max-hr"
						type="number"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.maxHeartRate}
					/>
				</div>
				<div>
					{@render label('cadence', $t('adventures.average_cadence'), 'average_cadence')}
					<input
						id="cadence"
						type="number"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.averageCadence}
					/>
				</div>
				<div>
					{@render label('calories', $t('adventures.calories'), 'calories')}
					<input
						id="calories"
						type="number"
						min="0"
						class="input mt-1 w-full"
						bind:value={draft.calories}
					/>
				</div>
				<div class="md:col-span-2">
					{@render label('rest-time', $t('adventures.rest_time'), 'rest_time')}
					<DurationInput id="rest-time" bind:value={draft.restTime} />
				</div>
			</div>
		{/if}
	</section>
</div>
