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
		const res = await fetch('/_allauth/browser/v1/account/authenticators/totp', {
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
		const res = await fetch('/_allauth/browser/v1/account/authenticators/totp', {
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
		const res = await fetch('/_allauth/browser/v1/account/authenticators/recovery-codes', {
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

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">{$t('settings.enable_mfa')}</h3>

		{#if qrCodeDataUrl}
			<div class="mb-4 flex items-center justify-center mt-2">
				<img src={qrCodeDataUrl} alt="QR Code" class="w-64 h-64" />
			</div>
		{/if}
		<div class="flex items-center justify-center mb-6">
			{#if secret}
				<div class="flex items-center">
					<input
						type="text"
						placeholder={secret}
						class="input input-bordered w-full max-w-xs"
						readonly
					/>
					<button class="btn btn-primary ml-2" on:click={() => copyToClipboard(secret)}
						>{$t('settings.copy')}</button
					>
				</div>
			{/if}
		</div>

		<input
			type="text"
			placeholder={$t('settings.authenticator_code')}
			class="input input-bordered w-full max-w-xs"
			bind:value={first_code}
		/>

		<div class="recovery-codes-container">
			{#if recovery_codes.length > 0}
				<h3 class="mt-4 text-center font-bold text-lg">{$t('settings.recovery_codes')}</h3>
				<p class="text-center text-lg mb-2">
					{$t('settings.recovery_codes_desc')}
				</p>
				<button
					class="btn btn-primary ml-2"
					on:click={() => copyToClipboard(recovery_codes.join(', '))}>{$t('settings.copy')}</button
				>
			{/if}
			<div class="recovery-codes-grid flex flex-wrap">
				{#each recovery_codes as code}
					<div
						class="recovery-code-item flex items-center justify-center m-2 w-full sm:w-1/2 md:w-1/3 lg:w-1/4"
					>
						<input type="text" value={code} class="input input-bordered w-full" readonly />
					</div>
				{/each}
			</div>
		</div>

		{#if reauthError}
			<div class="alert alert-error mt-4">
				{$t('settings.reset_session_error')}
			</div>
		{/if}

		{#if !is_enabled}
			<button class="btn btn-primary mt-4" on:click={sendTotp}>{$t('settings.enable_mfa')}</button>
		{/if}

		<button class="btn btn-primary mt-4" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
