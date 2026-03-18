<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';

	// Icons
	import Close from '~icons/mdi/close';
	import AlertCircle from '~icons/mdi/alert-circle';
	import Phone from '~icons/mdi/cellphone';
	import QrCodeIcon from '~icons/mdi/qrcode';
	import Key from '~icons/mdi/key';
	import Delete from '~icons/mdi/delete';
	import Refresh from '~icons/mdi/refresh';
	import Warning from '~icons/mdi/alert';

	const dispatch = createEventDispatcher();
	let modal: HTMLDialogElement;

	let qrCodeData: string | null = null;
	let apiKeyId: string | null = null;
	let apiKeyName: string | null = null;
	let apiKeyPrefix: string | null = null;
	let createdAt: string | null = null;
	let isLoading = false;
	let error: string | null = null;

	onMount(async () => {
		modal = document.querySelector('#mobile-qr-modal') as HTMLDialogElement;
		modal.showModal();
		await checkExistingKey();
	});

	async function checkExistingKey() {
		isLoading = true;
		error = null;

		try {
			const res = await fetch('/auth/mobile-qr/', {
				method: 'GET',
				credentials: 'include'
			});

			if (res.ok) {
				const data = await res.json();
				apiKeyId = data.id;
				apiKeyName = data.name;
				apiKeyPrefix = data.key_prefix;
				createdAt = data.created_at;
				// We have an existing key, but no QR code (key is not returned on GET for security)
				// User can delete and recreate if needed
			} else if (res.status === 404) {
				// No existing key, automatically generate one
				await generateQRCode();
			} else {
				error = 'Failed to check for existing mobile key';
			}
		} catch (err) {
			error = 'An error occurred while checking for existing mobile key';
			console.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function generateQRCode() {
		isLoading = true;
		error = null;

		try {
			const res = await fetch('/auth/mobile-qr/', {
				method: 'POST',
				credentials: 'include'
			});

			if (res.ok) {
				const data = await res.json();
				qrCodeData = data.qr_code;
				apiKeyId = data.id;
				apiKeyName = data.name;
				apiKeyPrefix = data.key_prefix;
				createdAt = data.created_at;
				addToast(
					'success',
					$t('mobile.qr_generated', { default: 'QR code generated successfully' })
				);
			} else {
				const errorData = await res.json();
				error = errorData.detail || 'Failed to generate QR code';
			}
		} catch (err) {
			error = 'An error occurred while generating the QR code';
			console.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function deleteApiKey() {
		if (!confirm('Are you sure you want to delete this mobile API key?')) {
			return;
		}

		isLoading = true;
		error = null;

		try {
			const res = await fetch('/auth/mobile-qr/', {
				method: 'DELETE',
				credentials: 'include'
			});

			if (res.ok || res.status === 204) {
				// Key deleted, close modal
				addToast('success', $t('mobile.key_deleted', { default: 'Mobile API key deleted' }));
				closeModal();
			} else {
				error = 'Failed to delete API key';
			}
		} catch (err) {
			error = 'An error occurred while deleting the API key';
			console.error(err);
		} finally {
			isLoading = false;
		}
	}

	async function regenerateQRCode() {
		// Delete the existing key and generate a new one
		isLoading = true;
		error = null;

		try {
			const res = await fetch('/auth/mobile-qr/', {
				method: 'DELETE',
				credentials: 'include'
			});

			if (res.ok || res.status === 204) {
				// Key deleted, now generate a new one
				await generateQRCode();
			} else {
				error = 'Failed to delete existing API key';
			}
		} catch (err) {
			error = 'An error occurred while regenerating the QR code';
			console.error(err);
		} finally {
			isLoading = false;
		}
	}

	function closeModal() {
		dispatch('close');
		modal.close();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeModal();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<dialog id="mobile-qr-modal" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-3xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
		role="dialog"
		on:keydown={handleKeydown}
		tabindex="0"
	>
		<!-- Header Section -->
		<div
			class=" top-0 z-10 bg-base-100/90 backdrop-blur-lg border-b border-base-300 -mx-6 -mt-6 px-6 py-4 mb-6"
		>
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="p-2 bg-primary/10 rounded-xl">
						<Phone class="w-8 h-8 text-primary" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-primary bg-clip-text">
							{$t('mobile.qr_title', { default: 'Mobile App Login' })}
						</h1>
						<p class="text-sm text-base-content/60">
							{$t('mobile.scan_to_login', { default: 'Scan QR code with mobile app' })}
						</p>
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={closeModal}>
					<Close class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			{#if isLoading}
				<div class="flex flex-col items-center justify-center py-12">
					<span class="loading loading-spinner loading-lg text-primary"></span>
					<p class="mt-4 text-base-content/60">
						{$t('mobile.loading', { default: 'Loading...' })}
					</p>
				</div>
			{:else if error}
				<div class="alert alert-error mb-4">
					<AlertCircle class="w-5 h-5" />
					<div>
						<h4 class="font-semibold">{$t('settings.error_occurred')}</h4>
						<p class="text-sm">{error}</p>
					</div>
				</div>
			{:else}
				<!-- QR Code Display -->
				{#if qrCodeData}
					<div class="card bg-base-200/50 border border-base-300/50 mb-6">
						<div class="card-body items-center text-center">
							<h3 class="card-title text-xl mb-4 flex items-center gap-2">
								<QrCodeIcon class="w-6 h-6 text-primary" />
								{$t('mobile.scan_qr', { default: 'Scan QR Code' })}
							</h3>
							<div class="p-4 bg-white rounded-xl border border-base-300 mb-4">
								<img src={qrCodeData} alt="QR Code" class="w-64 h-64" />
							</div>
							<p class="text-base-content/60 max-w-md">
								{$t('mobile.qr_instructions', {
									default: 'Open the AdventureLog mobile app and scan this QR code to log in.'
								})}
							</p>
						</div>
					</div>

					<!-- API Key Info Section -->
					<div class="card bg-base-200/50 border border-base-300/50 mb-6">
						<div class="card-body">
							<h3 class="card-title text-lg mb-4 flex items-center gap-2">
								<Key class="w-5 h-5 text-secondary" />
								{$t('mobile.key_info', { default: 'API Key Information' })}
							</h3>
							<div class="space-y-3">
								<div>
									<p class="text-sm text-base-content/60 mb-1">
										{$t('mobile.key_name', { default: 'Key Name' })}:
									</p>
									<p class="font-medium">{apiKeyName}</p>
								</div>
								<div>
									<p class="text-sm text-base-content/60 mb-1">
										{$t('mobile.key_prefix', { default: 'Key Prefix' })}:
									</p>
									<p class="font-mono text-sm bg-base-100/80 px-3 py-2 rounded-lg">
										{apiKeyPrefix}...
									</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Development Warning -->
					<div class="alert alert-warning">
						<Warning class="w-5 h-5" />
						<div>
							<h4 class="font-semibold">
								{$t('mobile.early_dev', { default: 'Early Development Notice' })}
							</h4>
							<p class="text-sm">
								{$t('mobile.early_dev_message', {
									default:
										'The mobile app is in super early development and is not yet available for download.'
								})}
							</p>
						</div>
					</div>
				{:else if apiKeyId}
					<!-- Existing key but no QR code shown -->
					<div class="card bg-base-200/50 border border-base-300/50 mb-6">
						<div class="card-body items-center text-center">
							<div class="p-3 bg-info/10 rounded-xl mb-4">
								<Key class="w-12 h-12 text-info" />
							</div>
							<h3 class="card-title text-xl mb-2">
								{$t('mobile.existing_key', { default: 'Existing Mobile Key Found' })}
							</h3>
							<p class="text-base-content/60 mb-4">
								{$t('mobile.existing_key_message', {
									default: 'You already have a mobile API key. Delete it to generate a new QR code.'
								})}
							</p>

							<!-- API Key Info -->
							<div class="w-full bg-base-100/80 rounded-xl p-4 space-y-3">
								<div>
									<p class="text-sm text-base-content/60 mb-1">
										{$t('mobile.key_name', { default: 'Key Name' })}:
									</p>
									<p class="font-medium">{apiKeyName}</p>
								</div>
								<div>
									<p class="text-sm text-base-content/60 mb-1">
										{$t('mobile.key_prefix', { default: 'Key Prefix' })}:
									</p>
									<p class="font-mono text-sm">{apiKeyPrefix}...</p>
								</div>
							</div>
						</div>
					</div>

					<!-- Development Warning -->
					<div class="alert alert-warning mb-6">
						<Warning class="w-5 h-5" />
						<div>
							<h4 class="font-semibold">
								{$t('mobile.early_dev', { default: 'Early Development Notice' })}
							</h4>
							<p class="text-sm">
								{$t('mobile.early_dev_message', {
									default:
										'The mobile app is in super early development and is not yet available for download.'
								})}
							</p>
						</div>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Footer Actions -->
		<div
			class="bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6 rounded-lg"
		>
			<div class="flex items-center justify-end gap-3">
				{#if qrCodeData}
					<button class="btn btn-outline gap-2" on:click={regenerateQRCode}>
						<Refresh class="w-4 h-4" />
						{$t('mobile.regenerate', { default: 'Regenerate' })}
					</button>
					<button class="btn btn-error gap-2" on:click={deleteApiKey}>
						<Delete class="w-4 h-4" />
						{$t('mobile.delete', { default: 'Delete Key' })}
					</button>
				{:else if apiKeyId}
					<button class="btn btn-primary gap-2" on:click={regenerateQRCode}>
						<QrCodeIcon class="w-4 h-4" />
						{$t('mobile.regenerate', { default: 'Regenerate QR Code' })}
					</button>
					<button class="btn btn-error gap-2" on:click={deleteApiKey}>
						<Delete class="w-4 h-4" />
						{$t('mobile.delete', { default: 'Delete Key' })}
					</button>
				{/if}
			</div>
		</div>
	</div>

	<!-- Backdrop -->
	<form method="dialog" class="modal-backdrop">
		<button type="button" on:click={closeModal}>close</button>
	</form>
</dialog>
