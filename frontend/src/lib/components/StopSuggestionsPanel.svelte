<script lang="ts">
	import { t } from 'svelte-i18n';
	import MagnifyIcon from '~icons/mdi/magnify';
	import CloseCircle from '~icons/mdi/close-circle';
	import Wheelchair from '~icons/mdi/wheelchair-accessibility';
	import ClockOutline from '~icons/mdi/clock-outline';
	import CurrencyUsd from '~icons/mdi/currency-usd';
	import FoodFork from '~icons/mdi/food-fork-drink';
	import PlusCircle from '~icons/mdi/plus-circle';
	import { createEventDispatcher } from 'svelte';
	import type { Location } from '$lib/types';

	// Isolated component (P5b) — never mutates `stop` or `collectionId` directly.
	// Adding a suggestion persists a SNAPSHOT (name/lat/lon), not a live
	// reference to the OSM id, per the blueprint's I1-adjacent restriction.
	export let stop: Location;
	export let collectionId: string;

	type Suggestion = {
		id: string;
		name: string;
		latitude: number | null;
		longitude: number | null;
		address?: string | null;
		primary_type?: string | null;
		cuisine?: string | null;
		wheelchair?: string | null;
		fee?: string | null;
		opening_hours?: string[] | string | null;
		description?: string | null;
		justification: string;
		travel_seconds: number | null;
	};

	let category: 'food' | 'tourism' | 'lodging' = 'food';
	let restrictions = '';
	let loading = false;
	let error: string | null = null;
	let suggestions: Suggestion[] = [];
	let addingId: string | null = null;
	let addedIds = new Set<string>();

	const dispatch = createEventDispatcher();

	function formatTravelTime(seconds: number | null) {
		if (seconds === null || seconds === undefined) return null;
		const minutes = Math.round(seconds / 60);
		return minutes < 1 ? '<1 min' : `${minutes} min`;
	}

	function formatOpeningHours(hours: Suggestion['opening_hours']) {
		if (!hours) return null;
		return Array.isArray(hours) ? hours.join(', ') : hours;
	}

	async function fetchSuggestions() {
		if (!stop?.id) return;

		loading = true;
		error = null;
		suggestions = [];

		try {
			const response = await fetch('/api/places/suggest/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ stop: stop.id, category, restrictions })
			});

			const data = await response.json();

			if (!response.ok) {
				throw new Error(data.error || 'Falha ao buscar sugestões.');
			}

			suggestions = data.suggestions || [];
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erro ao buscar sugestões.';
		} finally {
			loading = false;
		}
	}

	async function addAsStop(suggestion: Suggestion) {
		if (suggestion.latitude === null || suggestion.longitude === null) return;

		addingId = suggestion.id;
		try {
			const response = await fetch('/api/locations/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					// Snapshot only — name/lat/lon copied at add-time. No reference
					// back to the OSM id is stored anywhere in the itinerary.
					name: suggestion.name,
					latitude: suggestion.latitude,
					longitude: suggestion.longitude,
					collections: [collectionId]
				})
			});

			if (!response.ok) {
				throw new Error('Falha ao adicionar parada.');
			}

			const created = await response.json();
			addedIds = new Set([...addedIds, suggestion.id]);
			dispatch('added', created);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Erro ao adicionar parada.';
		} finally {
			addingId = null;
		}
	}
</script>

<div class="card bg-base-200 shadow-xl">
	<div class="card-body">
		<h3 class="card-title text-lg">
			<MagnifyIcon class="w-5 h-5" />
			{$t('recomendations.discover_places') || 'Sugestões perto desta parada'}
		</h3>

		<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
			<div class="form-control">
				<label class="label" for="suggestions-category">
					<span class="label-text">{$t('adventures.category') || 'Categoria'}</span>
				</label>
				<select id="suggestions-category" class="select select-bordered select-sm" bind:value={category}>
					<option value="food">🍴 Comida</option>
					<option value="tourism">🏛️ Turismo</option>
					<option value="lodging">🏨 Hospedagem</option>
				</select>
			</div>

			<div class="form-control md:col-span-2">
				<label class="label" for="suggestions-restrictions">
					<span class="label-text">Restrições (dieta, acessibilidade, orçamento...)</span>
				</label>
				<input
					id="suggestions-restrictions"
					type="text"
					class="input input-bordered input-sm w-full"
					placeholder="ex.: vegetariano, acessível para cadeira de rodas"
					bind:value={restrictions}
					on:keydown={(e) => e.key === 'Enter' && fetchSuggestions()}
				/>
			</div>
		</div>

		<button class="btn btn-primary btn-sm mt-3 w-fit" on:click={fetchSuggestions} disabled={loading}>
			{#if loading}
				<span class="loading loading-spinner loading-xs"></span>
				Buscando...
			{:else}
				<MagnifyIcon class="w-4 h-4" />
				Sugerir lugares
			{/if}
		</button>

		{#if error}
			<div class="alert alert-error alert-sm mt-3">
				<CloseCircle class="w-5 h-5" />
				<span>{error}</span>
			</div>
		{/if}

		{#if !loading && !error && suggestions.length === 0}
			<p class="text-sm opacity-70 mt-3">
				Nenhuma sugestão ainda — clique em "Sugerir lugares" pra buscar candidatos reais do
				OpenStreetMap perto desta parada.
			</p>
		{/if}

		<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
			{#each suggestions as suggestion (suggestion.id)}
				<div class="card bg-base-100 shadow">
					<div class="card-body p-4">
						<h4 class="font-bold">{suggestion.name}</h4>

						{#if suggestion.address}
							<p class="text-xs opacity-70">{suggestion.address}</p>
						{/if}

						<p class="text-sm mt-1 italic opacity-90">"{suggestion.justification}"</p>

						<div class="flex gap-2 flex-wrap mt-2">
							{#if suggestion.cuisine}
								<div class="badge badge-outline badge-sm">
									<FoodFork class="w-3 h-3 mr-1" />
									{suggestion.cuisine}
								</div>
							{/if}
							{#if suggestion.wheelchair === 'yes'}
								<div class="badge badge-outline badge-sm">
									<Wheelchair class="w-3 h-3 mr-1" />
									acessível
								</div>
							{/if}
							{#if suggestion.fee === 'no'}
								<div class="badge badge-outline badge-sm">
									<CurrencyUsd class="w-3 h-3 mr-1" />
									grátis
								</div>
							{/if}
							{#if formatOpeningHours(suggestion.opening_hours)}
								<div class="badge badge-ghost badge-sm">
									<ClockOutline class="w-3 h-3 mr-1" />
									{formatOpeningHours(suggestion.opening_hours)}
								</div>
							{/if}
							{#if formatTravelTime(suggestion.travel_seconds)}
								<div class="badge badge-primary badge-outline badge-sm">
									🚗 {formatTravelTime(suggestion.travel_seconds)}
								</div>
							{/if}
						</div>

						<div class="card-actions justify-end mt-3">
							<button
								class="btn btn-sm btn-outline"
								disabled={addingId === suggestion.id || addedIds.has(suggestion.id)}
								on:click={() => addAsStop(suggestion)}
							>
								{#if addingId === suggestion.id}
									<span class="loading loading-spinner loading-xs"></span>
								{:else if addedIds.has(suggestion.id)}
									✓ Adicionado
								{:else}
									<PlusCircle class="w-4 h-4" />
									Adicionar como parada
								{/if}
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>
