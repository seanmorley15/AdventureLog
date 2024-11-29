<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Collection, Transportation } from '$lib/types';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	import { addToast } from '$lib/toasts';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';

	export let collection: Collection;

	import MapMarker from '~icons/mdi/map-marker';
	import Calendar from '~icons/mdi/calendar';
	import Notebook from '~icons/mdi/notebook';
	import Star from '~icons/mdi/star';
	import PlaneCar from '~icons/mdi/plane-car';
	import LinkVariant from '~icons/mdi/link-variant';
	import Airplane from '~icons/mdi/airplane';

	export let startDate: string | null = null;
	export let endDate: string | null = null;

	let fullStartDate: string = '';
	let fullEndDate: string = '';

	if (startDate && endDate) {
		fullStartDate = `${startDate}T00:00`;
		fullEndDate = `${endDate}T23:59`;
	}

	let type: string = '';

	onMount(async () => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	// if (newTransportation.date) {
	// 	newTransportation.date = newTransportation.date.slice(0, 19);
	// }

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			close();
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		const form = event.target as HTMLFormElement;
		const formData = new FormData(form);

		// make sure there is a start date if there is an end date
		if (formData.get('end_date') && !formData.get('date')) {
			addToast('error', $t('transportation.provide_start_date'));
			return;
		}

		const response = await fetch(`/api/transportations/`, {
			method: 'POST',
			body: formData
		});

		if (response.ok) {
			const result = await response.json();

			addToast('success', $t('transportation.transportation_added'));
			dispatch('add', result);
			close();
		} else {
			addToast('error', $t('transportation.error_editing_transportation'));
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">{$t('transportation.new_transportation')}</h3>
		<div
			class="modal-action items-center"
			style="display: flex; flex-direction: column; align-items: center; width: 100%;"
		>
			<form method="post" style="width: 100%;" on:submit={handleSubmit}>
				<div class="mb-2">
					<input
						type="text"
						id="collection"
						name="collection"
						hidden
						readonly
						bind:value={collection.id}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<input
						type="text"
						id="is_public"
						name="is_public"
						hidden
						readonly
						bind:value={collection.is_public}
						class="input input-bordered w-full max-w-xs mt-1"
					/>
					<div class="mb-2">
						<label for="type"
							>{$t('transportation.type')} <PlaneCar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<select
							class="select select-bordered w-full max-w-xs"
							name="type"
							id="type"
							bind:value={type}
						>
							<option disabled selected>{$t('transportation.type')}</option>
							<option value="car">{$t('transportation.modes.car')}</option>
							<option value="plane">{$t('transportation.modes.plane')}</option>
							<option value="train">{$t('transportation.modes.train')}</option>
							<option value="bus">{$t('transportation.modes.bus')}</option>
							<option value="boat">{$t('transportation.modes.boat')}</option>
							<option value="bike">{$t('transportation.modes.bike')}</option>
							<option value="walking">{$t('transportation.modes.walking')}</option>
							<option value="other">{$t('transportation.modes.other')}</option>
						</select>
					</div>

					<label for="name">{$t('adventures.name')}</label><br />
					<input
						type="text"
						name="name"
						id="name"
						class="input input-bordered w-full max-w-xs mt-1"
					/>
				</div>
				<div class="mb-2">
					<label for="date"
						>{$t('adventures.description')}
						<Notebook class="inline-block -mt-1 mb-1 w-6 h-6" /></label
					><br />
					<div class="flex">
						<input
							type="text"
							id="description"
							name="description"
							class="input input-bordered w-full max-w-xs mt-1 mb-2"
						/>
					</div>
					<div class="mb-2">
						<label for="start_date"
							>{$t('transportation.date_time')}
							<Calendar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="datetime-local"
							id="date"
							name="date"
							min={fullStartDate || ''}
							max={fullEndDate || ''}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>

					<div class="mb-2">
						<label for="end_date"
							>{$t('transportation.end_date_time')}
							<Calendar class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="datetime-local"
							id="end_date"
							name="end_date"
							min={fullStartDate || ''}
							max={fullEndDate || ''}
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>

					<div class="mb-2">
						<label for="rating"
							>{$t('adventures.rating')} <Star class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="number"
							max="5"
							min="0"
							id="rating"
							name="rating"
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="rating"
							>{$t('adventures.link')} <LinkVariant class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="url"
							id="link"
							name="link"
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>

					{#if type == 'plane'}
						<div class="mb-2">
							<label for="flight_number"
								>{$t('transportation.flight_number')}
								<Airplane class="inline-block mb-1 w-6 h-6" /></label
							><br />
							<input
								type="text"
								id="flight_number"
								name="flight_number"
								class="input input-bordered w-full max-w-xs mt-1"
							/>
						</div>
					{/if}
					<div class="mb-2">
						<label for="rating"
							>{$t('transportation.from_location')}
							<MapMarker class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="text"
							id="from_location"
							name="from_location"
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
					<div class="mb-2">
						<label for="rating"
							>{$t('transportation.to_location')}
							<MapMarker class="inline-block mb-1 w-6 h-6" /></label
						><br />
						<input
							type="text"
							id="to_location"
							name="to_location"
							class="input input-bordered w-full max-w-xs mt-1"
						/>
					</div>
				</div>

				<button type="submit" class="btn btn-primary mr-4 mt-4">{$t('transportation.edit')}</button>
				<!-- if there is a button in form, it will close the modal -->
				<button class="btn mt-4" on:click={close}>{$t('about.close')}</button>
			</form>
			<div class="flex items-center justify-center flex-wrap gap-4 mt-4"></div>
		</div>
	</div>
</dialog>
