<script lang="ts">
	import { addToast } from '$lib/toasts';
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	// @ts-ignore
	import QRCode from 'qrcode';
	import { t } from 'svelte-i18n';
	import type { User } from '$lib/types';
	export let user: User | null = null;
	let secret: string | null = null;
	let qrCodeDataUrl: string | null = null;
	let totpUrl: string | null = null;
	let first_code: string = '';
	let recovery_codes: string[] = [];
	export let is_enabled: boolean;
	let reauthError: boolean = false;

	// import Account from '~icons/mdi/account';
	import Clear from '~icons/mdi/close';
	import Check from '~icons/mdi/check-circle';
	import Copy from '~icons/mdi/content-copy';
	import Error from '~icons/mdi/alert-circle';
	import Key from '~icons/mdi/key';
	import QrCode from '~icons/mdi/qrcode';
	import Security from '~icons/mdi/security';
	import Warning from '~icons/mdi/alert';
	import Shield from '~icons/mdi/shield-account';
	import Backup from '~icons/mdi/backup-restore';

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
		fetchSetupInfo();
		console.log(secret);
	});

	async function generateQRCode(secret: string | null) {
		try {
			if (secret) {
				qrCodeDataUrl = await QRCode.toDataURL(secret);
			}
		} catch (error) {
			console.error('Error generating QR code:', error);
		}
	}

	async function fetchSetupInfo() {
		const res = await fetch('/auth/browser/v1/account/authenticators/totp', {
			method: 'GET'
		});
		const data = await res.json();
		if (res.status == 404) {
			secret = data.meta.secret;
			totpUrl = `otpauth://totp/AdventureLog:${user?.username}?secret=${secret}&issuer=AdventureLog`;
			generateQRCode(totpUrl);
		} else if (res.ok) {
			close();
		} else {
			addToast('error', $t('settings.generic_error'));
		}
	}

	async function sendTotp() {
		const res = await fetch('/auth/browser/v1/account/authenticators/totp', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				code: first_code
			}),
			credentials: 'include'
		});
		console.log(res);
		if (res.ok) {
			addToast('success', $t('settings.mfa_enabled'));
			is_enabled = true;
			getRecoveryCodes();
		} else {
			if (res.status == 401) {
				reauthError = true;
			}
			addToast('error', $t('settings.generic_error'));
		}
	}

	async function getRecoveryCodes() {
		console.log('getting recovery codes');
		const res = await fetch('/auth/browser/v1/account/authenticators/recovery-codes', {
			method: 'GET'
		});
		if (res.ok) {
			let data = await res.json();
			recovery_codes = data.data.unused_codes;
		} else {
			addToast('error', $t('settings.generic_error'));
		}
	}

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}

	function copyToClipboard(copyText: string | null) {
		if (copyText) {
			navigator.clipboard.writeText(copyText).then(
				() => {
					addToast('success', $t('adventures.copied_to_clipboard'));
				},
				() => {
					addToast('error', $t('adventures.copy_failed'));
				}
			);
		}
	}
</script>

<dialog id="my_modal_1" class="modal backdrop-blur-sm">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div
		class="modal-box w-11/12 max-w-4xl bg-gradient-to-br from-base-100 via-base-100 to-base-200 border border-base-300 shadow-2xl"
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
					<div class="p-2 bg-warning/10 rounded-xl">
						<Shield class="w-8 h-8 text-warning" />
					</div>
					<div>
						<h1 class="text-3xl font-bold text-warning bg-clip-text">
							{$t('settings.enable_mfa')}
						</h1>
						<p class="text-sm text-base-content/60">
							{$t('settings.secure_your_account')}
						</p>
					</div>
				</div>

				<!-- Status Badge -->
				<div class="hidden md:flex items-center gap-2">
					<div class="badge badge-warning badge-lg gap-2">
						<Security class="w-4 h-4" />
						{is_enabled ? $t('settings.enabled') : $t('settings.setup_required')}
					</div>
				</div>

				<!-- Close Button -->
				<button class="btn btn-ghost btn-square" on:click={close}>
					<Clear class="w-5 h-5" />
				</button>
			</div>
		</div>

		<!-- Main Content -->
		<div class="px-2">
			<!-- QR Code Section -->
			{#if qrCodeDataUrl}
				<div class="card bg-base-200/50 border border-base-300/50 mb-6">
					<div class="card-body items-center text-center">
						<h3 class="card-title text-xl mb-4 flex items-center gap-2">
							<QrCode class="w-6 h-6 text-primary" />
							{$t('settings.scan_qr_code')}
						</h3>
						<div class="p-4 bg-white rounded-xl border border-base-300 mb-4">
							<img src={qrCodeDataUrl} alt="QR Code" class="w-64 h-64" />
						</div>
						<p class="text-base-content/60 max-w-md">
							{$t('settings.scan_with_authenticator_app')}
						</p>
					</div>
				</div>
			{/if}

			<!-- Secret Key Section -->
			{#if secret}
				<div class="card bg-base-200/50 border border-base-300/50 mb-6">
					<div class="card-body">
						<h3 class="card-title text-lg mb-4 flex items-center gap-2">
							<Key class="w-5 h-5 text-secondary" />
							{$t('settings.manual_entry')}
						</h3>
						<div class="flex items-center gap-3">
							<div class="flex-1">
								<input
									type="text"
									value={secret}
									class="input input-bordered w-full font-mono text-sm bg-base-100/80"
									readonly
								/>
							</div>
							<button class="btn btn-secondary gap-2" on:click={() => copyToClipboard(secret)}>
								<Copy class="w-4 h-4" />
								{$t('settings.copy')}
							</button>
						</div>
					</div>
				</div>
			{/if}

			<!-- Verification Code Section -->
			<div class="card bg-base-200/50 border border-base-300/50 mb-6">
				<div class="card-body">
					<h3 class="card-title text-lg mb-4 flex items-center gap-2">
						<Shield class="w-5 h-5 text-success" />
						{$t('settings.verify_setup')}
					</h3>
					<div class="form-control">
						<!-- svelte-ignore a11y-label-has-associated-control -->
						<label class="label">
							<span class="label-text font-medium">
								{$t('settings.authenticator_code')}
							</span>
						</label>
						<input
							type="text"
							placeholder={$t('settings.enter_6_digit_code')}
							class="input input-bordered bg-base-100/80 font-mono text-center text-lg tracking-widest"
							bind:value={first_code}
							maxlength="6"
						/>
						<!-- svelte-ignore a11y-label-has-associated-control -->
						<label class="label">
							<span class="label-text-alt text-base-content/60">
								{$t('settings.enter_code_from_app')}
							</span>
						</label>
					</div>
				</div>
			</div>

			<!-- Recovery Codes Section -->
			{#if recovery_codes.length > 0}
				<div class="card bg-base-200/50 border border-base-300/50 mb-6">
					<div class="card-body">
						<div class="flex items-center justify-between mb-4">
							<h3 class="card-title text-lg flex items-center gap-2">
								<Backup class="w-5 h-5 text-info" />
								{$t('settings.recovery_codes')}
							</h3>
							<button
								class="btn btn-info btn-sm gap-2"
								on:click={() => copyToClipboard(recovery_codes.join(', '))}
							>
								<Copy class="w-4 h-4" />
								{$t('settings.copy_all')}
							</button>
						</div>

						<div class="alert alert-warning mb-4">
							<Warning class="w-5 h-5" />
							<div>
								<h4 class="font-semibold">{$t('settings.important')}</h4>
								<p class="text-sm">{$t('settings.recovery_codes_desc')}</p>
							</div>
						</div>

						<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
							{#each recovery_codes as code, index}
								<div class="relative group">
									<input
										type="text"
										value={code}
										class="input input-bordered input-sm w-full font-mono text-center bg-base-100/80 pr-10"
										readonly
									/>
									<button
										class="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity btn btn-ghost btn-xs"
										on:click={() => copyToClipboard(code)}
									>
										<Copy class="w-3 h-3" />
									</button>
									<span
										class="absolute -top-2 -left-2 bg-base-content text-base-100 rounded-full w-5 h-5 text-xs flex items-center justify-center font-bold"
									>
										{index + 1}
									</span>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}

			<!-- Error Message -->
			{#if reauthError}
				<div class="alert alert-error mb-6">
					<Error class="w-5 h-5" />
					<div>
						<h4 class="font-semibold">{$t('settings.error_occurred')}</h4>
						<p class="text-sm">{$t('settings.reset_session_error')}</p>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer Actions -->
		<div
			class="bottom-0 bg-base-100/90 backdrop-blur-lg border-t border-base-300 -mx-6 -mb-6 px-6 py-4 mt-6 rounded-lg"
		>
			<div class="flex items-center justify-between">
				<div class="text-sm text-base-content/60">
					{is_enabled
						? $t('settings.mfa_already_enabled')
						: $t('settings.complete_setup_to_enable')}
				</div>
				<div class="flex items-center gap-3">
					{#if !is_enabled && first_code.length >= 6}
						<button class="btn btn-success gap-2" on:click={sendTotp}>
							<Shield class="w-4 h-4" />
							{$t('settings.enable_mfa')}
						</button>
					{/if}
					<button class="btn btn-primary gap-2" on:click={close}>
						<Check class="w-4 h-4" />
						{$t('about.close')}
					</button>
				</div>
			</div>
		</div>
	</div>
</dialog>
