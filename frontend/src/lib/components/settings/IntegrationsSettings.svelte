<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type { ImmichIntegration, User, WandererIntegration } from '$lib/types';
	import ImmichLogo from '$lib/assets/immich.svg';
	import GoogleMapsLogo from '$lib/assets/google_maps.svg';
	import StravaLogo from '$lib/assets/strava.svg';
	import WandererLogoSrc from '$lib/assets/wanderer.svg';
	import { BUILTIN_INTEGRATIONS } from './integrationCatalog';
	import MapIcon from '~icons/mdi/map';
	import BookOpenPageVariant from '~icons/mdi/book-open-page-variant';
	import WeatherSunset from '~icons/mdi/weather-sunset';
	import MapSearch from '~icons/mdi/map-search';

	export let user: User;
	export let immichIntegration: ImmichIntegration | null = null;
	export let googleMapsEnabled = false;
	export let stravaGlobalEnabled = false;
	export let stravaUserEnabled = false;
	export let wandererEnabled = false;
	export let wandererIntegration: WandererIntegration | null = null;

	let newImmichIntegration: ImmichIntegration = {
		server_url: '',
		api_key: '',
		id: '',
		copy_locally: true
	};

	let newWandererIntegration: WandererIntegration = {
		server_url: '',
		api_key: '',
		id: ''
	};

	const builtinIcons = {
		osm: MapIcon,
		wikipedia: BookOpenPageVariant,
		sunrise: WeatherSunset,
		overpass: MapSearch
	} as const;

	function handleImmichError(data: {
		code?: string;
		details?: string;
		message?: string;
		error?: string;
		server_url?: string[];
		api_key?: string[];
	}) {
		if (data.code === 'immich.connection_failed') {
			return `${$t('immich.connection_error')}: ${data.details || data.message}`;
		}
		if (data.code === 'immich.integration_exists') {
			return $t('immich.integration_already_exists');
		}
		if (data.code === 'immich.integration_not_found') {
			return $t('immich.integration_not_found');
		}
		if (data.error && data.message) {
			return data.message;
		}

		const errors: string[] = [];
		if (data.server_url) errors.push(`Server URL: ${data.server_url.join(', ')}`);
		if (data.api_key) errors.push(`API Key: ${data.api_key.join(', ')}`);
		return errors.length > 0
			? `${$t('immich.validation_error')}: ${errors.join('; ')}`
			: $t('immich.immich_error');
	}

	async function enableImmichIntegration() {
		const isUpdate = !!immichIntegration?.id;
		const url = isUpdate
			? `/api/integrations/immich/${immichIntegration?.id ?? ''}/`
			: '/api/integrations/immich/';
		const method = isUpdate ? 'PUT' : 'POST';

		try {
			const res = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(newImmichIntegration)
			});
			const data = await res.json();

			if (res.ok) {
				addToast('success', $t(isUpdate ? 'immich.immich_updated' : 'immich.immich_enabled'));
				immichIntegration = data;
				newImmichIntegration = { server_url: '', api_key: '', id: '', copy_locally: true };
			} else {
				addToast('error', handleImmichError(data));
			}
		} catch {
			addToast('error', $t('immich.network_error'));
		}
	}

	async function disableImmichIntegration() {
		if (!immichIntegration?.id) return;

		const res = await fetch(`/api/integrations/immich/${immichIntegration.id}/`, {
			method: 'DELETE'
		});
		if (res.ok) {
			addToast('success', $t('immich.immich_disabled'));
			immichIntegration = null;
		} else {
			addToast('error', $t('immich.immich_error'));
		}
	}

	async function stravaAuthorizeRedirect() {
		const res = await fetch('/api/integrations/strava/authorize/', {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			const data = await res.json();
			window.location.href = data.auth_url;
		} else {
			addToast('error', $t('strava.authorization_error'));
		}
	}

	async function stravaDisconnect() {
		const res = await fetch('/api/integrations/strava/disable/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			addToast('success', $t('strava.disconnected'));
			stravaUserEnabled = false;
		} else {
			addToast('error', $t('strava.disconnect_error'));
		}
	}

	async function wandererDisconnect() {
		const res = await fetch('/api/integrations/wanderer/disable/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			addToast('success', $t('wanderer.disconnected'));
			wandererEnabled = false;
			wandererIntegration = null;
		} else {
			addToast('error', $t('wanderer.disconnect_error'));
		}
	}

	async function enableWandererIntegration() {
		const integrationId = newWandererIntegration.id || wandererIntegration?.id;
		const isUpdate = !!integrationId;
		const url = isUpdate
			? `/api/integrations/wanderer/${integrationId}/`
			: '/api/integrations/wanderer/';
		const method = isUpdate ? 'PUT' : 'POST';

		try {
			const res = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(newWandererIntegration)
			});
			const responseData = await res.json();

			if (res.ok) {
				addToast('success', $t(isUpdate ? 'wanderer.updated' : 'wanderer.connected'));
				wandererIntegration = responseData;
				wandererEnabled = true;
				newWandererIntegration = { server_url: '', api_key: '', id: '' };
			} else {
				const message =
					responseData.error ||
					responseData.detail ||
					(Array.isArray(responseData) ? responseData.join(', ') : null) ||
					$t('wanderer.connection_error');
				addToast('error', message);
			}
		} catch {
			addToast('error', $t('wanderer.connection_error'));
		}
	}
</script>

<!-- Immich -->
<div class="p-6 bg-base-200 rounded-xl mb-4">
	<div class="flex items-center gap-4 mb-4">
		<img src={ImmichLogo} alt="Immich" class="w-8 h-8 shrink-0" />
		<div class="flex-1 min-w-0">
			<h3 class="text-xl font-bold">Immich</h3>
			<p class="text-sm text-base-content/70">{$t('immich.immich_integration_desc')}</p>
		</div>
		{#if immichIntegration}
			<div class="badge badge-success ml-auto shrink-0">{$t('settings.connected')}</div>
		{:else}
			<div class="badge badge-error ml-auto shrink-0">{$t('settings.disconnected')}</div>
		{/if}
	</div>

	{#if immichIntegration && !newImmichIntegration.id}
		<div class="flex gap-4 justify-center mb-4">
			<button
				type="button"
				class="btn btn-warning"
				on:click={() => {
					if (immichIntegration) newImmichIntegration = { ...immichIntegration, api_key: '' };
				}}
			>
				✏️ {$t('lodging.edit')}
			</button>
			<button type="button" class="btn btn-error" on:click={disableImmichIntegration}>
				❌ {$t('immich.disable')}
			</button>
		</div>
	{/if}

	{#if !immichIntegration || newImmichIntegration.id}
		<div class="space-y-4">
			<div class="form-control">
				<label class="label" for="immich-server-url">
					<span class="label-text font-medium">{$t('immich.server_url')}</span>
				</label>
				<input
					id="immich-server-url"
					type="url"
					bind:value={newImmichIntegration.server_url}
					class="input input-bordered input-primary focus:input-primary w-full"
					placeholder="https://immich.example.com/api"
				/>
				{#if newImmichIntegration.server_url && !newImmichIntegration.server_url.endsWith('api')}
					<div class="label">
						<span class="label-text-alt text-warning">{$t('immich.api_note')}</span>
					</div>
				{/if}
				{#if newImmichIntegration.server_url && (newImmichIntegration.server_url.includes('localhost') || newImmichIntegration.server_url.includes('127.0.0.1'))}
					<div class="label">
						<span class="label-text-alt text-warning">{$t('immich.localhost_note')}</span>
					</div>
				{/if}
			</div>

			<div class="form-control">
				<label class="label" for="immich-api-key">
					<span class="label-text font-medium">{$t('immich.api_key')}</span>
				</label>
				<input
					id="immich-api-key"
					type="password"
					bind:value={newImmichIntegration.api_key}
					class="input input-bordered input-primary focus:input-primary w-full"
					placeholder={$t('immich.api_key_placeholder')}
				/>
			</div>

			<div class="form-control">
				<label class="label cursor-pointer justify-start gap-4">
					<input
						type="checkbox"
						bind:checked={newImmichIntegration.copy_locally}
						class="toggle toggle-primary"
					/>
					<div>
						<span class="label-text font-medium">
							{$t('immich.copy_locally') || 'Copy Locally'}
						</span>
						<p class="text-sm text-base-content/70">
							{$t('immich.copy_locally_desc') || 'If enabled, files will be copied locally.'}
						</p>
					</div>
				</label>
			</div>

			<button type="button" on:click={enableImmichIntegration} class="btn btn-primary w-full">
				{!immichIntegration?.id
					? `🔗 ${$t('immich.enable_integration')}`
					: `💾 ${$t('immich.update_integration')}`}
			</button>
		</div>
	{/if}

	<div class="mt-4 p-4 bg-info/10 rounded-lg">
		<p class="text-sm">
			📖 {$t('immich.need_help')}
			<a
				class="link link-primary"
				href="https://adventurelog.app/docs/configuration/immich_integration.html"
				target="_blank"
				rel="noopener noreferrer"
			>
				{$t('navbar.documentation')}
			</a>
		</p>
	</div>
</div>

<!-- Google Maps -->
<div class="p-6 bg-base-200 rounded-xl mb-4">
	<div class="flex items-center gap-4 mb-4">
		<img src={GoogleMapsLogo} alt="Google Maps" class="w-8 h-8 shrink-0" />
		<div class="flex-1 min-w-0">
			<h3 class="text-xl font-bold">Google Maps</h3>
			<p class="text-sm text-base-content/70">{$t('google_maps.google_maps_integration_desc')}</p>
		</div>
		{#if googleMapsEnabled}
			<div class="badge badge-success ml-auto shrink-0">{$t('settings.connected')}</div>
		{:else}
			<div class="badge badge-error ml-auto shrink-0">{$t('settings.disconnected')}</div>
		{/if}
	</div>

	{#if user.is_staff || !googleMapsEnabled}
		<div class="mt-4 p-4 bg-info/10 rounded-lg">
			{#if user.is_staff}
				<p class="text-sm">
					📖 {$t('immich.need_help')}
					<a
						class="link link-primary"
						href="https://adventurelog.app/docs/configuration/google_maps_integration.html"
						target="_blank"
						rel="noopener noreferrer"
					>
						{$t('navbar.documentation')}
					</a>
				</p>
			{:else if !googleMapsEnabled}
				<p class="text-sm">ℹ️ {$t('google_maps.google_maps_integration_desc_no_staff')}</p>
			{/if}
		</div>
	{/if}
</div>

<!-- Strava -->
<div class="p-6 bg-base-200 rounded-xl mb-4">
	<div class="flex items-center gap-4 mb-4">
		<img src={StravaLogo} alt="Strava" class="w-8 h-8 rounded-md shrink-0" />
		<div class="flex-1 min-w-0">
			<h3 class="text-xl font-bold">Strava</h3>
			<p class="text-sm text-base-content/70">{$t('strava.strava_integration_desc')}</p>
		</div>
		{#if stravaGlobalEnabled && stravaUserEnabled}
			<div class="badge badge-success ml-auto shrink-0">{$t('settings.connected')}</div>
		{:else}
			<div class="badge badge-error ml-auto shrink-0">{$t('settings.disconnected')}</div>
		{/if}
	</div>

	{#if !stravaGlobalEnabled}
		<div class="text-center">
			<p class="text-base-content/70 mb-4">
				{$t('strava.not_enabled') || 'Strava integration is not enabled on this instance.'}
			</p>
		</div>
	{:else if !stravaUserEnabled}
		<div class="text-center">
			<button type="button" class="btn btn-primary" on:click={stravaAuthorizeRedirect}>
				🔗 {$t('strava.connect_account')}
			</button>
		</div>
	{:else}
		<div class="text-center">
			<button type="button" class="btn btn-error" on:click={stravaDisconnect}>
				❌ {$t('strava.disconnect')}
			</button>
		</div>
	{/if}

	{#if user.is_staff || !stravaGlobalEnabled}
		<div class="mt-4 p-4 bg-info/10 rounded-lg">
			{#if user.is_staff}
				<p class="text-sm">
					📖 {$t('immich.need_help')}
					<a
						class="link link-primary"
						href="https://adventurelog.app/docs/configuration/strava_integration.html"
						target="_blank"
						rel="noopener noreferrer"
					>
						{$t('navbar.documentation')}
					</a>
				</p>
			{:else if !stravaGlobalEnabled}
				<p class="text-sm">ℹ️ {$t('google_maps.google_maps_integration_desc_no_staff')}</p>
			{/if}
		</div>
	{/if}
</div>

<!-- Wanderer -->
<div class="p-6 bg-base-200 rounded-xl mb-4">
	<div class="flex items-center gap-4 mb-4">
		<img src={WandererLogoSrc} alt="Wanderer" class="w-8 h-8 shrink-0" />
		<div class="flex-1 min-w-0">
			<h3 class="text-xl font-bold">Wanderer</h3>
			<p class="text-sm text-base-content/70">{$t('wanderer.wanderer_integration_desc')}</p>
		</div>
		{#if wandererEnabled}
			<div class="badge badge-success ml-auto shrink-0">{$t('settings.connected')}</div>
		{:else}
			<div class="badge badge-error ml-auto shrink-0">{$t('settings.disconnected')}</div>
		{/if}
	</div>

	{#if wandererIntegration && !newWandererIntegration.id}
		<div class="flex gap-4 justify-center mb-4">
			<button
				type="button"
				class="btn btn-warning"
				on:click={() => {
					if (wandererIntegration) {
						newWandererIntegration = { ...wandererIntegration, api_key: '' };
					}
				}}
			>
				✏️ {$t('lodging.edit')}
			</button>
			<button type="button" class="btn btn-error" on:click={wandererDisconnect}>
				❌ {$t('strava.disconnect')}
			</button>
		</div>
	{/if}

	{#if !wandererIntegration || newWandererIntegration.id}
		<div class="space-y-4">
			<div class="form-control">
				<label class="label" for="wanderer-server-url">
					<span class="label-text font-medium">{$t('wanderer.server_url')}</span>
				</label>
				<input
					id="wanderer-server-url"
					type="url"
					class="input input-bordered input-primary focus:input-primary w-full"
					placeholder="https://wanderer.example.com"
					bind:value={newWandererIntegration.server_url}
				/>
				{#if newWandererIntegration.server_url && (newWandererIntegration.server_url.includes('localhost') || newWandererIntegration.server_url.includes('127.0.0.1'))}
					<div class="label">
						<span class="label-text-alt text-warning">{$t('wanderer.localhost_note')}</span>
					</div>
				{/if}
			</div>

			<div class="form-control">
				<label class="label" for="wanderer-api-key">
					<span class="label-text font-medium">{$t('wanderer.api_key')}</span>
				</label>
				<input
					id="wanderer-api-key"
					type="password"
					class="input input-bordered input-primary focus:input-primary w-full"
					placeholder={$t('wanderer.api_key_placeholder')}
					bind:value={newWandererIntegration.api_key}
				/>
			</div>

			<button type="button" class="btn btn-primary w-full" on:click={enableWandererIntegration}>
				{!wandererIntegration?.id
					? `🔗 ${$t('adventures.connect_to_wanderer')}`
					: `💾 ${$t('wanderer.update_integration')}`}
			</button>
		</div>
	{/if}

	<div class="mt-4 p-4 bg-info/10 rounded-lg">
		<p class="text-sm">
			📖 {$t('immich.need_help')}
			<a
				class="link link-primary"
				href="https://adventurelog.app/docs/configuration/wanderer_integration.html"
				target="_blank"
				rel="noopener noreferrer"
			>
				{$t('navbar.documentation')}
			</a>
		</p>
	</div>
</div>

<!-- Included by default -->
<div class="p-6 bg-base-200 rounded-xl mb-4">
	<div class="flex items-center gap-4 mb-4">
		<div class="p-2 bg-base-100 rounded-lg text-xl leading-none">✨</div>
		<div class="flex-1 min-w-0">
			<h3 class="text-xl font-bold">{$t('settings.integrations_hub.builtin_title')}</h3>
			<p class="text-sm text-base-content/70">
				{$t('settings.integrations_hub.builtin_desc')}
			</p>
		</div>
		<div class="badge badge-success ml-auto shrink-0">
			{$t('settings.integrations_hub.included')}
		</div>
	</div>

	<ul class="divide-y divide-base-300 rounded-lg border border-base-300 bg-base-100/60">
		{#each BUILTIN_INTEGRATIONS as integration (integration.id)}
			{@const Icon = builtinIcons[integration.icon]}
			<li class="flex items-start gap-3 p-4">
				<div class="p-1.5 text-primary shrink-0">
					<Icon class="w-5 h-5" />
				</div>
				<div class="min-w-0 flex-1">
					<p class="font-medium">{$t(integration.nameKey)}</p>
					<p class="text-sm text-base-content/70 mt-0.5">{$t(integration.descriptionKey)}</p>
				</div>
			</li>
		{/each}
	</ul>
</div>
