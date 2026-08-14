<script lang="ts">
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type {
		EndurainIntegration,
		ImmichIntegration,
		User,
		WandererIntegration
	} from '$lib/types';
	import ImmichLogo from '$lib/assets/immich.svg';
	import GoogleMapsLogo from '$lib/assets/google_maps.svg';
	import StravaLogo from '$lib/assets/strava.svg';
	import WandererLogoSrc from '$lib/assets/wanderer.svg';
	import EndurainLogo from '$lib/assets/endurain.png';
	import { BUILTIN_INTEGRATIONS } from './integrationCatalog';
	import MapIcon from '~icons/mdi/map';
	import BookOpenPageVariant from '~icons/mdi/book-open-page-variant';
	import WeatherSunset from '~icons/mdi/weather-sunset';
	import MapSearch from '~icons/mdi/map-search';
	import LinkVariant from '~icons/mdi/link-variant';
	import ServerIcon from '~icons/mdi/server';
	import Sparkles from '~icons/mdi/sparkles';

	interface Props {
		user: User;
		immichIntegration?: ImmichIntegration | null;
		googleMapsEnabled?: boolean;
		stravaGlobalEnabled?: boolean;
		stravaUserEnabled?: boolean;
		wandererEnabled?: boolean;
		wandererIntegration?: WandererIntegration | null;
		endurainEnabled?: boolean;
		endurainIntegration?: EndurainIntegration | null;
	}

	let {
		user,
		immichIntegration = $bindable(null),
		googleMapsEnabled = $bindable(false),
		stravaGlobalEnabled = $bindable(false),
		stravaUserEnabled = $bindable(false),
		wandererEnabled = $bindable(false),
		wandererIntegration = $bindable(null),
		endurainEnabled = $bindable(false),
		endurainIntegration = $bindable(null)
	}: Props = $props();

	let endurainServerUrl = $state('');
	let endurainUsername = $state('');
	let endurainPassword = $state('');
	let endurainMfaCode = $state('');
	let endurainMfaRequired = $state(false);
	let endurainMfaUsername = '';
	let endurainMfaServerUrl = '';
	let endurainMfaToken = '';
	let endurainConnecting = $state(false);
	let endurainAuthStep = $state(false);

	let newImmichIntegration: ImmichIntegration = $state({
		server_url: '',
		api_key: '',
		id: '',
		copy_locally: true
	});

	let newWandererIntegration: WandererIntegration = $state({
		server_url: '',
		api_key: '',
		id: ''
	});

	const builtinIcons = {
		osm: MapIcon,
		wikipedia: BookOpenPageVariant,
		sunrise: WeatherSunset,
		overpass: MapSearch
	} as const;

	function cancelImmichEdit() {
		newImmichIntegration = { server_url: '', api_key: '', id: '', copy_locally: true };
	}

	function cancelWandererEdit() {
		newWandererIntegration = { server_url: '', api_key: '', id: '' };
	}

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

	function resetEndurainForm() {
		endurainServerUrl = '';
		endurainUsername = '';
		endurainPassword = '';
		endurainMfaCode = '';
		endurainMfaRequired = false;
		endurainMfaUsername = '';
		endurainMfaServerUrl = '';
		endurainMfaToken = '';
		endurainAuthStep = false;
	}

	function confirmEndurainServerUrl() {
		if (!endurainServerUrl.trim()) {
			addToast('error', $t('endurain.server_url_required'));
			return;
		}
		try {
			new URL(endurainServerUrl.trim());
		} catch {
			addToast('error', $t('endurain.server_url_required'));
			return;
		}
		endurainAuthStep = true;
	}

	function backToEndurainUrlStep() {
		endurainAuthStep = false;
		endurainMfaRequired = false;
		endurainMfaCode = '';
		endurainMfaToken = '';
		endurainUsername = '';
		endurainPassword = '';
	}

	async function connectEndurainPassword() {
		if (!endurainServerUrl || !endurainUsername || !endurainPassword) {
			addToast('error', $t('endurain.credentials_required'));
			return;
		}
		endurainConnecting = true;
		try {
			const res = await fetch('/api/integrations/endurain/connect/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					server_url: endurainServerUrl.trim(),
					username: endurainUsername,
					password: endurainPassword
				})
			});
			const data = await res.json();
			if (res.status === 202 && data.mfa_required) {
				endurainMfaRequired = true;
				endurainMfaUsername = data.username || endurainUsername;
				endurainMfaServerUrl = data.server_url || endurainServerUrl.trim();
				endurainMfaToken = data.mfa_token || '';
				addToast('info', $t('endurain.mfa_required'));
				return;
			}
			if (res.ok) {
				addToast('success', $t('endurain.connected'));
				endurainIntegration = data;
				endurainEnabled = true;
				resetEndurainForm();
				endurainServerUrl = data.server_url || '';
			} else {
				addToast('error', data.message || data.detail || $t('endurain.connection_error'));
			}
		} catch {
			addToast('error', $t('endurain.connection_error'));
		} finally {
			endurainConnecting = false;
		}
	}

	async function verifyEndurainMfa() {
		if (!endurainMfaCode) {
			addToast('error', $t('endurain.mfa_code_required'));
			return;
		}
		if (!endurainMfaToken) {
			addToast('error', $t('endurain.connection_error'));
			return;
		}
		endurainConnecting = true;
		try {
			const res = await fetch('/api/integrations/endurain/mfa/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					mfa_token: endurainMfaToken,
					mfa_code: endurainMfaCode
				})
			});
			const data = await res.json();
			if (res.ok) {
				addToast('success', $t('endurain.connected'));
				endurainIntegration = data;
				endurainEnabled = true;
				resetEndurainForm();
			} else {
				addToast('error', data.message || data.detail || $t('endurain.connection_error'));
			}
		} catch {
			addToast('error', $t('endurain.connection_error'));
		} finally {
			endurainConnecting = false;
		}
	}

	async function endurainDisconnect() {
		const res = await fetch('/api/integrations/endurain/disable/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			addToast('success', $t('endurain.disconnected'));
			endurainEnabled = false;
			endurainIntegration = null;
			resetEndurainForm();
		} else {
			addToast('error', $t('endurain.disconnect_error'));
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

<div class="space-y-8">
	<!-- Your integrations -->
	<section class="bg-base-100 rounded-2xl shadow-xl p-8">
		<div class="flex items-center gap-4 mb-6">
			<div class="p-3 bg-primary/10 rounded-xl text-primary">
				<LinkVariant class="w-6 h-6" />
			</div>
			<div>
				<h2 class="text-2xl font-bold">{$t('settings.integrations_hub.personal_title')}</h2>
				<p class="text-base-content/70">{$t('settings.integrations_hub.personal_desc')}</p>
			</div>
		</div>

		<div class="space-y-4">
			<!-- Immich -->
			<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
				<div class="flex items-start gap-4">
					<img
						src={ImmichLogo}
						alt="Immich"
						class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
					/>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<h3 class="text-lg font-semibold">Immich</h3>
							{#if immichIntegration}
								<span class="badge badge-success badge-sm shrink-0">{$t('settings.connected')}</span
								>
							{:else}
								<span class="badge badge-error badge-outline badge-sm shrink-0">
									{$t('settings.disconnected')}
								</span>
							{/if}
						</div>
						<p class="text-sm text-base-content/70 mt-1">{$t('immich.immich_integration_desc')}</p>
						<a
							class="inline-block text-sm link link-primary mt-1"
							href="https://adventurelog.app/docs/configuration/immich_integration.html"
							target="_blank"
							rel="noopener noreferrer"
						>
							{$t('settings.integrations_hub.learn_more')}
						</a>
					</div>
				</div>

				{#if immichIntegration && !newImmichIntegration.id}
					<div class="mt-4 space-y-3">
						<p class="text-sm text-base-content/70 truncate" title={immichIntegration.server_url}>
							{immichIntegration.server_url}
						</p>
						<div class="flex flex-wrap gap-2">
							<button
								type="button"
								class="btn btn-sm btn-outline"
								onclick={() => {
									if (immichIntegration)
										newImmichIntegration = { ...immichIntegration, api_key: '' };
								}}
							>
								{$t('settings.integrations_hub.edit')}
							</button>
							<button
								type="button"
								class="btn btn-sm btn-error btn-outline"
								onclick={disableImmichIntegration}
							>
								{$t('settings.integrations_hub.disconnect')}
							</button>
						</div>
					</div>
				{/if}

				{#if !immichIntegration || newImmichIntegration.id}
					<div class="mt-4 space-y-4">
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
							<label class="label cursor-pointer justify-start gap-3 items-start py-0">
								<input
									type="checkbox"
									bind:checked={newImmichIntegration.copy_locally}
									class="toggle toggle-primary mt-1"
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

						<div class="flex flex-wrap items-center gap-2">
							<button
								type="button"
								onclick={enableImmichIntegration}
								class="btn btn-primary w-full sm:w-auto"
							>
								{!immichIntegration?.id
									? $t('settings.integrations_hub.connect')
									: $t('settings.integrations_hub.update')}
							</button>
							{#if newImmichIntegration.id}
								<button
									type="button"
									class="btn btn-ghost w-full sm:w-auto"
									onclick={cancelImmichEdit}
								>
									{$t('settings.integrations_hub.cancel')}
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Wanderer -->
			<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
				<div class="flex items-start gap-4">
					<img
						src={WandererLogoSrc}
						alt="Wanderer"
						class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
					/>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<h3 class="text-lg font-semibold">Wanderer</h3>
							{#if wandererEnabled}
								<span class="badge badge-success badge-sm shrink-0">{$t('settings.connected')}</span
								>
							{:else}
								<span class="badge badge-error badge-outline badge-sm shrink-0">
									{$t('settings.disconnected')}
								</span>
							{/if}
						</div>
						<p class="text-sm text-base-content/70 mt-1">
							{$t('wanderer.wanderer_integration_desc')}
						</p>
						<a
							class="inline-block text-sm link link-primary mt-1"
							href="https://adventurelog.app/docs/configuration/wanderer_integration.html"
							target="_blank"
							rel="noopener noreferrer"
						>
							{$t('settings.integrations_hub.learn_more')}
						</a>
					</div>
				</div>

				{#if wandererIntegration && !newWandererIntegration.id}
					<div class="mt-4 space-y-3">
						<p class="text-sm text-base-content/70 truncate" title={wandererIntegration.server_url}>
							{wandererIntegration.server_url}
						</p>
						<div class="flex flex-wrap gap-2">
							<button
								type="button"
								class="btn btn-sm btn-outline"
								onclick={() => {
									if (wandererIntegration) {
										newWandererIntegration = { ...wandererIntegration, api_key: '' };
									}
								}}
							>
								{$t('settings.integrations_hub.edit')}
							</button>
							<button
								type="button"
								class="btn btn-sm btn-error btn-outline"
								onclick={wandererDisconnect}
							>
								{$t('settings.integrations_hub.disconnect')}
							</button>
						</div>
					</div>
				{/if}

				{#if !wandererIntegration || newWandererIntegration.id}
					<div class="mt-4 space-y-4">
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

						<div class="flex flex-wrap items-center gap-2">
							<button
								type="button"
								class="btn btn-primary w-full sm:w-auto"
								onclick={enableWandererIntegration}
							>
								{!wandererIntegration?.id
									? $t('settings.integrations_hub.connect')
									: $t('settings.integrations_hub.update')}
							</button>
							{#if newWandererIntegration.id}
								<button
									type="button"
									class="btn btn-ghost w-full sm:w-auto"
									onclick={cancelWandererEdit}
								>
									{$t('settings.integrations_hub.cancel')}
								</button>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Endurain -->
			<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
				<div class="flex items-start gap-4">
					<img
						src={EndurainLogo}
						alt="Endurain"
						class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
					/>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<h3 class="text-lg font-semibold">Endurain</h3>
							{#if endurainEnabled}
								<span class="badge badge-success badge-sm shrink-0">{$t('settings.connected')}</span
								>
							{:else}
								<span class="badge badge-error badge-outline badge-sm shrink-0">
									{$t('settings.disconnected')}
								</span>
							{/if}
						</div>
						<p class="text-sm text-base-content/70 mt-1">
							{$t('endurain.endurain_integration_desc')}
						</p>
						<a
							class="inline-block text-sm link link-primary mt-1"
							href="https://adventurelog.app/docs/configuration/endurain_integration.html"
							target="_blank"
							rel="noopener noreferrer"
						>
							{$t('settings.integrations_hub.learn_more')}
						</a>
					</div>
				</div>

				{#if endurainIntegration}
					<div class="mt-4 space-y-3">
						<div class="text-sm text-base-content/80 space-y-1">
							<p>
								{$t('endurain.connected_as', {
									values: { username: endurainIntegration.username || '—' }
								})}
							</p>
							<p class="truncate text-base-content/70" title={endurainIntegration.server_url}>
								{endurainIntegration.server_url}
							</p>
						</div>
						<button
							type="button"
							class="btn btn-sm btn-error btn-outline"
							onclick={endurainDisconnect}
						>
							{$t('settings.integrations_hub.disconnect')}
						</button>
					</div>
				{:else}
					<div class="mt-4 space-y-4">
						<div class="form-control">
							<label class="label" for="endurain-server-url">
								<span class="label-text font-medium">{$t('endurain.server_url')}</span>
							</label>
							<input
								id="endurain-server-url"
								type="url"
								class="input input-bordered input-primary focus:input-primary w-full"
								placeholder="https://endurain.example.com"
								bind:value={endurainServerUrl}
								disabled={endurainAuthStep}
							/>
							{#if endurainServerUrl && (endurainServerUrl.includes('localhost') || endurainServerUrl.includes('127.0.0.1'))}
								<div class="label">
									<span class="label-text-alt text-warning">{$t('endurain.localhost_note')}</span>
								</div>
							{/if}
						</div>

						{#if !endurainAuthStep}
							<button
								type="button"
								class="btn btn-primary w-full sm:w-auto"
								onclick={confirmEndurainServerUrl}
								disabled={!endurainServerUrl.trim() || endurainConnecting}
							>
								{$t('endurain.continue')}
							</button>
						{:else}
							<button
								type="button"
								class="btn btn-ghost btn-sm"
								onclick={backToEndurainUrlStep}
								disabled={endurainConnecting}
							>
								{$t('endurain.change_server')}
							</button>

							{#if endurainMfaRequired}
								<div class="form-control">
									<label class="label" for="endurain-mfa-code">
										<span class="label-text font-medium">{$t('endurain.mfa_code')}</span>
									</label>
									<input
										id="endurain-mfa-code"
										type="text"
										class="input input-bordered input-primary w-full"
										placeholder="123456"
										bind:value={endurainMfaCode}
									/>
								</div>
								<button
									type="button"
									class="btn btn-primary w-full sm:w-auto"
									onclick={verifyEndurainMfa}
									disabled={endurainConnecting}
								>
									{$t('endurain.verify_mfa')}
								</button>
							{:else}
								<div class="bg-base-100 rounded-lg p-4 border border-base-300 space-y-4">
									<div class="form-control">
										<label class="label" for="endurain-username">
											<span class="label-text font-medium">{$t('endurain.username')}</span>
										</label>
										<input
											id="endurain-username"
											type="text"
											class="input input-bordered input-primary w-full"
											bind:value={endurainUsername}
										/>
									</div>
									<div class="form-control">
										<label class="label" for="endurain-password">
											<span class="label-text font-medium">{$t('endurain.password')}</span>
										</label>
										<input
											id="endurain-password"
											type="password"
											class="input input-bordered input-primary w-full"
											bind:value={endurainPassword}
										/>
									</div>
									<button
										type="button"
										class="btn btn-primary w-full sm:w-auto"
										onclick={connectEndurainPassword}
										disabled={endurainConnecting}
									>
										{$t('settings.integrations_hub.connect')}
									</button>
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			</div>

			<!-- Strava (personal, when instance-enabled) -->
			{#if stravaGlobalEnabled}
				<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
					<div class="flex items-start gap-4">
						<img
							src={StravaLogo}
							alt="Strava"
							class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
						/>
						<div class="min-w-0 flex-1">
							<div class="flex items-start justify-between gap-3">
								<h3 class="text-lg font-semibold">Strava</h3>
								{#if stravaUserEnabled}
									<span class="badge badge-success badge-sm shrink-0"
										>{$t('settings.connected')}</span
									>
								{:else}
									<span class="badge badge-error badge-outline badge-sm shrink-0">
										{$t('settings.disconnected')}
									</span>
								{/if}
							</div>
							<p class="text-sm text-base-content/70 mt-1">
								{$t('strava.strava_integration_desc')}
							</p>
							<a
								class="inline-block text-sm link link-primary mt-1"
								href="https://adventurelog.app/docs/configuration/strava_integration.html"
								target="_blank"
								rel="noopener noreferrer"
							>
								{$t('settings.integrations_hub.learn_more')}
							</a>
						</div>
					</div>

					<div class="mt-4">
						{#if !stravaUserEnabled}
							<button
								type="button"
								class="btn btn-primary w-full sm:w-auto"
								onclick={stravaAuthorizeRedirect}
							>
								{$t('settings.integrations_hub.connect')}
							</button>
						{:else}
							<button
								type="button"
								class="btn btn-sm btn-error btn-outline"
								onclick={stravaDisconnect}
							>
								{$t('settings.integrations_hub.disconnect')}
							</button>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</section>

	<!-- Instance services -->
	<section class="bg-base-100 rounded-2xl shadow-xl p-8">
		<div class="flex items-center gap-4 mb-6">
			<div class="p-3 bg-accent/10 rounded-xl text-accent">
				<ServerIcon class="w-6 h-6" />
			</div>
			<div>
				<h2 class="text-2xl font-bold">{$t('settings.integrations_hub.instance_title')}</h2>
				<p class="text-base-content/70">{$t('settings.integrations_hub.instance_desc')}</p>
			</div>
		</div>

		<div class="space-y-4">
			<!-- Google Maps -->
			<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
				<div class="flex items-start gap-4">
					<img
						src={GoogleMapsLogo}
						alt="Google Maps"
						class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
					/>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<h3 class="text-lg font-semibold">Google Maps</h3>
							{#if googleMapsEnabled}
								<span class="badge badge-success badge-sm shrink-0">{$t('settings.enabled')}</span>
							{:else}
								<span class="badge badge-warning badge-sm shrink-0">{$t('settings.disabled')}</span>
							{/if}
						</div>
						<p class="text-sm text-base-content/70 mt-1">
							{$t('google_maps.google_maps_integration_desc')}
						</p>
						{#if googleMapsEnabled}
							<a
								class="inline-block text-sm link link-primary mt-1"
								href="https://adventurelog.app/docs/configuration/google_maps_integration.html"
								target="_blank"
								rel="noopener noreferrer"
							>
								{$t('settings.integrations_hub.learn_more')}
							</a>
						{/if}
					</div>
				</div>

				<div class="mt-4">
					{#if googleMapsEnabled}
						<p class="text-sm text-base-content/70">
							{$t('settings.integrations_hub.google_maps_active_hint')}
						</p>
					{:else if user.is_staff}
						<p class="text-sm text-base-content/70">
							{$t('immich.need_help')}
							<a
								class="link link-primary"
								href="https://adventurelog.app/docs/configuration/google_maps_integration.html"
								target="_blank"
								rel="noopener noreferrer"
							>
								{$t('navbar.documentation')}
							</a>
						</p>
					{:else}
						<p class="text-sm text-base-content/70">
							{$t('google_maps.google_maps_integration_desc_no_staff')}
						</p>
					{/if}
				</div>
			</div>

			<!-- Strava (instance, when not globally enabled) -->
			{#if !stravaGlobalEnabled}
				<div class="rounded-xl border border-base-300 bg-base-200/60 p-5">
					<div class="flex items-start gap-4">
						<img
							src={StravaLogo}
							alt="Strava"
							class="w-10 h-10 shrink-0 rounded-lg object-contain bg-base-100 p-1.5"
						/>
						<div class="min-w-0 flex-1">
							<div class="flex items-start justify-between gap-3">
								<h3 class="text-lg font-semibold">Strava</h3>
								<span class="badge badge-warning badge-sm shrink-0">{$t('settings.disabled')}</span>
							</div>
							<p class="text-sm text-base-content/70 mt-1">
								{$t('strava.strava_integration_desc')}
							</p>
						</div>
					</div>

					<div class="mt-4 space-y-2">
						<p class="text-sm text-base-content/70">{$t('strava.not_enabled')}</p>
						{#if user.is_staff}
							<p class="text-sm text-base-content/70">
								{$t('immich.need_help')}
								<a
									class="link link-primary"
									href="https://adventurelog.app/docs/configuration/strava_integration.html"
									target="_blank"
									rel="noopener noreferrer"
								>
									{$t('navbar.documentation')}
								</a>
							</p>
						{:else}
							<p class="text-sm text-base-content/70">
								{$t('google_maps.google_maps_integration_desc_no_staff')}
							</p>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</section>

	<!-- Built-in services -->
	<section class="bg-base-100 rounded-2xl shadow-xl p-8">
		<div class="flex items-center gap-4 mb-6">
			<div class="p-3 bg-success/10 rounded-xl text-success">
				<Sparkles class="w-6 h-6" />
			</div>
			<div>
				<h2 class="text-2xl font-bold">{$t('settings.integrations_hub.builtin_title')}</h2>
				<p class="text-base-content/70">{$t('settings.integrations_hub.builtin_desc')}</p>
			</div>
		</div>

		<ul class="divide-y divide-base-300 rounded-xl border border-base-300 bg-base-200/60">
			{#each BUILTIN_INTEGRATIONS as integration (integration.id)}
				{@const Icon = builtinIcons[integration.icon]}
				<li class="flex items-start gap-3 p-4">
					<div class="p-1.5 text-primary shrink-0">
						<Icon class="w-5 h-5" />
					</div>
					<div class="min-w-0 flex-1">
						<div class="flex items-start justify-between gap-3">
							<p class="font-medium">{$t(integration.nameKey)}</p>
							<span class="badge badge-success badge-sm shrink-0">
								{$t('settings.integrations_hub.included')}
							</span>
						</div>
						<p class="text-sm text-base-content/70 mt-0.5">{$t(integration.descriptionKey)}</p>
					</div>
				</li>
			{/each}
		</ul>
	</section>
</div>
