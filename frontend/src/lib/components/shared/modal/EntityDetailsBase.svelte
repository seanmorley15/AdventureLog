<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { t } from 'svelte-i18n';
	import {
		InfoCard,
		NameField,
		LinkField,
		PublicToggle,
		DescriptionWithGenerate,
		TagsCard,
		DetailsActionButtons
	} from '../form';
	import MapIcon from '~icons/mdi/map';
	import InfoIcon from '~icons/mdi/information';

	const dispatch = createEventDispatcher<{
		save: void;
		back: void;
	}>();

	// Common form fields (bound from parent)
	export let name: string = '';
	export let description: string = '';
	export let link: string = '';
	export let is_public: boolean = true;
	export let tags: string[] = [];

	// UI state
	export let isProcessing: boolean = false;
	export let disabled: boolean = false;
	export let showBack: boolean = true;

	// i18n keys for customization
	export let namePlaceholder: string = '';
	export let linkPlaceholder: string = '';
	export let publicLabel: string = '';
	export let publicDescription: string = '';

	// Entity name for description generation
	export let entityNameForGenerate: string = '';
	export let descriptionDisabled: boolean = false;

	function handleSave() {
		dispatch('save');
	}

	function handleBack() {
		dispatch('back');
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200/30 via-base-100 to-primary/5 p-6">
	<div class="max-w-full mx-auto space-y-6">
		<!-- Basic Information Section -->
		<InfoCard title={$t('adventures.basic_information')} icon={InfoIcon}>
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Left Column -->
				<div class="space-y-4">
					<NameField bind:value={name} placeholder={namePlaceholder} />

					<!-- Type field slot (entity-specific) -->
					<slot name="type-field" />

					<!-- Extra left fields slot (entity-specific: reservation_number, flight_number, codes) -->
					<slot name="left-extra" />
				</div>

				<!-- Right Column -->
				<div class="space-y-4">
					<LinkField bind:value={link} placeholder={linkPlaceholder} />

					<PublicToggle
						bind:checked={is_public}
						label={publicLabel}
						description={publicDescription}
					/>

					<DescriptionWithGenerate
						bind:text={description}
						entityName={entityNameForGenerate || name}
						disabled={descriptionDisabled}
					/>

					<!-- Extra right fields slot (entity-specific) -->
					<slot name="right-extra" />
				</div>
			</div>
		</InfoCard>

		<!-- Tags Section -->
		<TagsCard bind:tags />

		<!-- Location Search & Map Section -->
		<InfoCard
			title={$t('adventures.location_map')}
			icon={MapIcon}
			iconColorClass="text-secondary"
			iconBgClass="bg-secondary/10"
		>
			<slot name="map" />
		</InfoCard>

		<!-- Action Buttons -->
		<DetailsActionButtons
			{showBack}
			{disabled}
			{isProcessing}
			on:back={handleBack}
			on:save={handleSave}
		/>
	</div>
</div>
