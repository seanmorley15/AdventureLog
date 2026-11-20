<script lang="ts">
	import { t } from 'svelte-i18n';
	import {
		formatDistance,
		formatDuration,
		formatElevation,
		formatSpeed,
		type MeasurementSystem
	} from './format.js';
	import type { ActivityRecord, ProfileStatsData } from './types.js';

	import Run from '~icons/mdi/run';
	import Walk from '~icons/mdi/walk';
	import Bike from '~icons/mdi/bike';
	import Snowflake from '~icons/mdi/snowflake';
	import WaterOutline from '~icons/mdi/water-outline';
	import Dumbbell from '~icons/mdi/dumbbell';
	import Tennis from '~icons/mdi/tennis';
	import Hills from '~icons/mdi/image-filter-hdr';
	import Soccer from '~icons/mdi/soccer';
	import Dots from '~icons/mdi/dots-horizontal';
	import Route from '~icons/mdi/map-marker-distance';
	import Timer from '~icons/mdi/timer-outline';
	import Mountain from '~icons/mdi/trending-up';
	import Fire from '~icons/mdi/fire';
	import ChevronDown from '~icons/mdi/chevron-down';

	interface Props {
		stats: ProfileStatsData;
		system: MeasurementSystem;
	}

	let { stats, system }: Props = $props();

	// Full class names, so Tailwind can see them: classes built from a color name are not generated.
	const categories: Record<string, { icon: any; tone: string }> = {
		running: { icon: Run, tone: 'bg-error/10 text-error' },
		walking_hiking: { icon: Walk, tone: 'bg-success/10 text-success' },
		cycling: { icon: Bike, tone: 'bg-info/10 text-info' },
		winter_sports: { icon: Snowflake, tone: 'bg-primary/10 text-primary' },
		water_sports: { icon: WaterOutline, tone: 'bg-accent/10 text-accent' },
		fitness_gym: { icon: Dumbbell, tone: 'bg-warning/10 text-warning' },
		racket_sports: { icon: Tennis, tone: 'bg-secondary/10 text-secondary' },
		climbing_adventure: { icon: Hills, tone: 'bg-orange-500/10 text-orange-500' },
		team_sports: { icon: Soccer, tone: 'bg-green-500/10 text-green-500' },
		other_sports: { icon: Dots, tone: 'bg-purple-500/10 text-purple-500' }
	};

	const overall = $derived(stats.activities_overall);
	const byCategory = $derived(
		Object.entries(stats.activities_by_category ?? {}).sort((a, b) => b[1].count - a[1].count)
	);
	let open = $state<Record<string, boolean>>({});

	const summary = $derived([
		{
			icon: Run,
			label: $t('adventures.total_activities'),
			value: overall.total_count.toLocaleString()
		},
		{
			icon: Route,
			label: $t('adventures.total_distance'),
			value: formatDistance(overall.total_distance, system)
		},
		{
			icon: Timer,
			label: $t('adventures.moving_time'),
			value: formatDuration(overall.total_moving_time)
		},
		{
			icon: Mountain,
			label: $t('adventures.elevation_gain'),
			value: formatElevation(overall.total_elevation_gain, system)
		},
		...(overall.total_calories > 0
			? [
					{
						icon: Fire,
						label: $t('adventures.calories'),
						value: Math.round(overall.total_calories).toLocaleString()
					}
				]
			: [])
	]);

	function categoryLabel(key: string): string {
		return $t(`profile.cat_${key}`);
	}

	function sportLabel(sport: string): string {
		return sport.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ');
	}
</script>

{#snippet record(label: string, value: string, rec: ActivityRecord | null | undefined)}
	<div class="rounded-lg border border-base-300/60 bg-base-200/40 p-3">
		<div class="text-xs uppercase tracking-wide text-base-content/60">{label}</div>
		<div class="text-lg font-semibold">{value}</div>
		{#if rec?.location_id}
			<a href={`/locations/${rec.location_id}`} class="link link-hover text-xs text-primary">
				{$t('profile.best_at')}
				{rec.location_name}
			</a>
		{/if}
	</div>
{/snippet}

<div class="space-y-6">
	<div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
		{#each summary as item}
			<div class="flex items-center gap-3 rounded-box border border-base-300/60 bg-base-100 p-4">
				<div class="rounded-lg bg-primary/10 p-2 text-primary"><item.icon class="h-5 w-5" /></div>
				<div class="min-w-0">
					<div class="truncate text-lg font-bold leading-tight">{item.value}</div>
					<div class="truncate text-xs text-base-content/60">{item.label}</div>
				</div>
			</div>
		{/each}
	</div>

	<div class="space-y-3">
		{#each byCategory as [key, data] (key)}
			{@const meta = categories[key] ?? categories.other_sports}
			<div class="rounded-box border border-base-300/60 bg-base-100">
				<button
					class="flex w-full items-center gap-4 p-4 text-left"
					aria-expanded={!!open[key]}
					onclick={() => (open[key] = !open[key])}
				>
					<div class="rounded-lg p-2.5 {meta.tone}"><meta.icon class="h-6 w-6" /></div>
					<div class="min-w-0 flex-1">
						<div class="font-semibold">{categoryLabel(key)}</div>
						<div class="text-sm text-base-content/60">
							{data.count.toLocaleString()}
							{$t('adventures.activities_text')}
						</div>
					</div>
					<div class="text-right">
						<div class="font-bold">{formatDistance(data.total_distance, system)}</div>
						<div class="text-xs text-base-content/60">
							{$t('profile.elevation_gain_label', {
								values: { value: formatElevation(data.total_elevation_gain, system) }
							})}
						</div>
					</div>
					<ChevronDown
						class="h-5 w-5 shrink-0 text-base-content/50 transition-transform {open[key]
							? 'rotate-180'
							: ''}"
					/>
				</button>

				{#if open[key]}
					<div class="space-y-4 border-t border-base-300/60 p-4">
						<div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
							{@render record($t('profile.time'), formatDuration(data.total_moving_time), null)}
							{@render record($t('profile.avg_speed'), formatSpeed(data.avg_speed, system), null)}
							{@render record(
								$t('profile.max_speed'),
								formatSpeed(data.max_speed, system),
								data.record_holders?.max_speed
							)}
							{@render record(
								$t('profile.avg_distance'),
								formatDistance(data.avg_distance, system),
								null
							)}
							{@render record(
								$t('adventures.total_distance'),
								formatDistance(data.max_distance, system),
								data.record_holders?.max_distance
							)}
							{@render record(
								$t('adventures.elevation_gain'),
								formatElevation(data.max_elevation_gain, system),
								data.record_holders?.max_elevation_gain
							)}
							{#if data.total_calories > 0}
								{@render record(
									$t('adventures.calories'),
									Math.round(data.total_calories).toLocaleString(),
									data.record_holders?.max_calories
								)}
							{/if}
						</div>

						{#if Object.keys(data.sports).length > 1}
							<div>
								<div class="mb-2 text-xs uppercase tracking-wide text-base-content/60">
									{$t('profile.sports')}
								</div>
								<div class="flex flex-wrap gap-2">
									{#each Object.entries(data.sports) as [sport, s]}
										<span class="badge badge-outline gap-1.5 py-3">
											<span class="capitalize">{sportLabel(sport)}</span>
											<span class="text-base-content/60">
												{s.count} · {formatDistance(s.total_distance, system)}
											</span>
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>
