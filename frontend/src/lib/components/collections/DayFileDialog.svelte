<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { t } from 'svelte-i18n';
	import type {
		Activity,
		Collection,
		CollectionItineraryDay,
		ContentImage,
		Trail
	} from '$lib/types';
	import { parseImmichIntegration } from '$lib/integrations';
	import EditorDialog from '$lib/components/shared/EditorDialog.svelte';
	import TrailComposer from '$lib/components/trails/TrailComposer.svelte';
	import ActivityComposer from '$lib/components/activities/ActivityComposer.svelte';
	import ImageManagement from '$lib/components/ImageManagement.svelte';

	interface Props {
		collection: Collection;
		day: CollectionItineraryDay;
		kind: 'trail' | 'activity' | 'photos';
		onClose: () => void;
	}

	let { collection = $bindable(), day, kind, onClose }: Props = $props();

	const user = $derived(page.data?.user);
	const userIsOwner = $derived(
		Boolean(user && (user.uuid === collection.user || user.id === collection.user))
	);
	const measurementSystem = $derived(
		(user?.measurement_system as 'metric' | 'imperial' | undefined) || 'metric'
	);
	const dayTrails = $derived(
		(collection.day_trails ?? []).filter(
			(trail) =>
				trail.day === day.id ||
				(trail.day_index &&
					trail.span_end_index &&
					day.index &&
					trail.day_index <= day.index &&
					day.index <= trail.span_end_index)
		)
	);
	const laterDays = $derived(
		(collection.itinerary_days ?? [])
			.filter((entry) => (entry.index ?? 0) > (day.index ?? 0))
			.map((entry) => ({
				index: entry.index ?? 0,
				label: $t('itinerary.day_n', { values: { n: entry.index } })
			}))
	);
	const subtitle = $derived(
		[$t('itinerary.day_n', { values: { n: day.index } }), day.date].filter(Boolean).join(' · ')
	);

	let photos = $state<ContentImage[]>(
		(collection.day_images ?? []).filter(
			(image) => image.content_type === 'collectionitineraryday' && image.object_id === day.id
		)
	);
	let immichIntegration = $state(false);
	let copyImmichLocally = $state(false);

	function rememberTrail(trail: Trail) {
		collection.day_trails = [...(collection.day_trails ?? []), trail];
		onClose();
	}

	function rememberActivity(activity: Activity) {
		collection.day_activities = [...(collection.day_activities ?? []), activity];
		onClose();
	}

	function rememberPhotos(next: ContentImage[]) {
		const others = (collection.day_images ?? []).filter(
			(image) => !(image.content_type === 'collectionitineraryday' && image.object_id === day.id)
		);
		collection.day_images = [
			...others,
			...next.map((image) => ({
				...image,
				content_type: 'collectionitineraryday',
				object_id: day.id
			}))
		];
	}

	onMount(async () => {
		if (kind !== 'photos') return;
		try {
			const res = await fetch('/api/integrations');
			if (!res.ok) return;
			const data = await res.json();
			const immich = parseImmichIntegration(data.immich);
			immichIntegration = immich.enabled;
			copyImmichLocally = immich.copyLocally;
		} catch (error) {
			console.error(error);
		}
	});
</script>

<EditorDialog
	title={kind === 'trail'
		? $t('adventures.trails_management')
		: kind === 'activity'
			? $t('adventures.add_new_activity')
			: $t('adventures.images')}
	{subtitle}
	{onClose}
>
	{#if kind === 'trail'}
		<TrailComposer
			dayId={day.id}
			{userIsOwner}
			mode="both"
			dayChoices={laterDays}
			onCreated={rememberTrail}
			onCancel={onClose}
		/>
	{:else if kind === 'activity'}
		<ActivityComposer
			dayId={day.id}
			dateStart={day.date ? `${day.date}T00:00:00` : null}
			dateEnd={day.date ? `${day.date}T23:59:59` : null}
			timezone={collection.timezone}
			trails={dayTrails}
			{measurementSystem}
			onSaved={rememberActivity}
			onCancel={onClose}
		/>
	{:else}
		<ImageManagement
			bind:images={photos}
			objectId={day.id}
			contentType="collectionitineraryday"
			defaultSearchTerm={day.name || collection.name}
			{immichIntegration}
			{copyImmichLocally}
			on:imagesUpdated={(event) => rememberPhotos(event.detail)}
		/>
	{/if}
</EditorDialog>
