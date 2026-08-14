<script lang="ts">
	import { run } from 'svelte/legacy';

	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import { normalizeBasemapType } from '$lib';
	import type {
		EndurainIntegration,
		ImmichIntegration,
		WandererIntegration,
		User,
		APIKey,
		MediaUsage,
		AuthUserSession
	} from '$lib/types.js';
	import { onMount, untrack } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';
	import TotpModal from '$lib/components/TOTPModal.svelte';
	import IntegrationsSettings from '$lib/components/settings/IntegrationsSettings.svelte';
	import SettingsNav from '$lib/components/settings/SettingsNav.svelte';
	import ProfileSettingsPanel from '$lib/components/settings/ProfileSettingsPanel.svelte';
	import EmailsSettingsPanel from '$lib/components/settings/EmailsSettingsPanel.svelte';
	import SecuritySettingsPanel from '$lib/components/settings/SecuritySettingsPanel.svelte';
	import DataSettingsPanel from '$lib/components/settings/DataSettingsPanel.svelte';
	import DangerZoneSettingsPanel from '$lib/components/settings/DangerZoneSettingsPanel.svelte';
	import AboutSettingsPanel from '$lib/components/settings/AboutSettingsPanel.svelte';
	import AdminSettingsPanel from '$lib/components/settings/AdminSettingsPanel.svelte';
	import { isReauthRequired, reauthenticateWithPassword } from '$lib/reauthenticate';

	let { data = $bindable() } = $props();

	const LEGACY_TAB_MAP: Record<string, string> = {
		import_export: 'data',
		advanced: 'about'
	};

	let user = $state({} as User);
	let emails: typeof data.props.emails = $state([]);

	type Provider = { name: string; usage_required: boolean };

	let new_email = $state('');
	let public_url: string = $derived(data.props.publicUrl);
	let immichIntegration = $state<ImmichIntegration | null>(null);
	let googleMapsEnabled = $state(false);
	let stravaGlobalEnabled = $state(false);
	let stravaUserEnabled = $state(false);
	let wandererEnabled = $state(false);
	let wandererIntegration: WandererIntegration | null = $state(null);
	let endurainEnabled = $state(false);
	let endurainIntegration: EndurainIntegration | null = $state(null);
	let activeSection = $state('profile');

	let socialProviders: Provider[] = $derived(data.props.socialProviders ?? []);
	let passwordPolicy = $derived(data.props.passwordPolicy);
	let newPassword = $state('');
	let confirmPassword = $state('');
	let acknowledgeRestoreOverride = $state(false);
	let isRestoring = $state(false);
	let isMFAModalOpen = $state(false);
	let mfaDisableNeedsReauth = $state(false);
	let mfaDisablePassword = $state('');
	let mfaDisableReauthError = $state(false);
	let isDisablingMfa = $state(false);
	let isVerifyingMfaDisablePassword = $state(false);
	let deleteConfirmation = $state('');
	let deletePassword = $state('');
	let isDeletingAccount = false;

	let apiKeys: APIKey[] = $state<APIKey[]>([]);
	let sessions: AuthUserSession[] = $state<AuthUserSession[]>([]);
	let mediaUsage: MediaUsage = $derived(
		data.props.mediaUsage ??
			({
				total_bytes: 0,
				limit_bytes: null,
				images_bytes: 0,
				attachments_bytes: 0,
				profile_pics_bytes: 0,
				images_files: 0,
				attachments_files: 0,
				profile_pics_files: 0
			} as MediaUsage)
	);

	$effect.pre(() => {
		const nextUser = data.user;
		const nextEmails = data.props.emails;
		const nextImmich = data.props.immichIntegration;
		const nextGoogleMaps = data.props.googleMapsEnabled;
		const nextStravaGlobal = data.props.stravaGlobalEnabled;
		const nextStravaUser = data.props.stravaUserEnabled;
		const nextWandererEnabled = data.props.wandererEnabled;
		const nextWanderer = data.props.wandererIntegration;
		const nextEndurainEnabled = data.props.endurainEnabled;
		const nextEndurain = data.props.endurainIntegration;
		const nextApiKeys = data.props.apiKeys ?? [];
		const nextSessions = data.props.sessions ?? [];

		untrack(() => {
			if (nextUser) {
				user = {
					...nextUser,
					map_style: normalizeBasemapType(nextUser.map_style)
				};
				emails = nextEmails;
			}
			immichIntegration = nextImmich;
			googleMapsEnabled = nextGoogleMaps;
			stravaGlobalEnabled = nextStravaGlobal;
			stravaUserEnabled = nextStravaUser;
			wandererEnabled = nextWandererEnabled;
			wandererIntegration = nextWanderer;
			endurainEnabled = nextEndurainEnabled;
			endurainIntegration = nextEndurain;
			apiKeys = nextApiKeys;
			sessions = nextSessions;
		});
	});
	let isRevokingSession = $state(false);
	let newApiKeyName = $state('');
	let newlyCreatedKey: string | null = $state(null);
	let keyCopied = $state(false);

	const formatBytes = (bytes: number) => {
		if (!bytes || bytes <= 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, index);
		const precision = value >= 10 || index === 0 ? 0 : 1;
		return `${value.toFixed(precision)} ${units[index]}`;
	};

	let totalMediaBytes = $derived(mediaUsage?.total_bytes ?? 0);
	let mediaLimitBytes = $derived(mediaUsage?.limit_bytes ?? null);
	let totalMediaFiles =
		$derived((mediaUsage?.images_files ?? 0) +
		(mediaUsage?.attachments_files ?? 0) +
		(mediaUsage?.profile_pics_files ?? 0));
	let overallUsagePercent = $derived(mediaLimitBytes
		? Math.min(100, Math.round((totalMediaBytes / mediaLimitBytes) * 100))
		: 0);
	let imagesPercent = $derived(mediaLimitBytes
		? Math.min(100, Math.round((mediaUsage.images_bytes / mediaLimitBytes) * 100))
		: 0);
	let attachmentsPercent = $derived(mediaLimitBytes
		? Math.min(100, Math.round((mediaUsage.attachments_bytes / mediaLimitBytes) * 100))
		: 0);
	let profilePicsPercent = $derived(mediaLimitBytes
		? Math.min(100, Math.round((mediaUsage.profile_pics_bytes / mediaLimitBytes) * 100))
		: 0);
	let mediaLimitLabel = $derived(mediaLimitBytes ? formatBytes(mediaLimitBytes) : 'Unlimited');

	let profileSharingImpact =
		$derived((user?.shared_collection_count ?? 0) + (user?.pending_collection_invite_count ?? 0));

	run(() => {
		if (browser && $page.form?.deleteAccountError) {
			addToast('error', $t($page.form.deleteAccountError));
		}
	});

	let canDeleteAccount =
		$derived(deleteConfirmation.trim() === user?.username &&
		(!user?.has_password || user?.disable_password || deletePassword.length > 0));

	function normalizeSection(tab: string | null) {
		if (!tab) return 'profile';
		if (tab === 'danger' || tab === 'about' || tab === 'data') return tab;
		return LEGACY_TAB_MAP[tab] ?? tab;
	}

	function setActiveSection(sectionId: string) {
		activeSection = sectionId;
		if (browser) {
			const url = new URL($page.url);
			url.searchParams.set('tab', sectionId);
			url.searchParams.delete('focus');
			history.replaceState({}, '', url);
		}
	}

	function handlePublicProfileToggle(nextValue: boolean) {
		if (
			user.public_profile &&
			!nextValue &&
			profileSharingImpact > 0 &&
			!confirm(
				$t('settings.public_profile_private_confirm', {
					values: {
						shared: user.shared_collection_count ?? 0,
						invites: user.pending_collection_invite_count ?? 0
					}
				})
			)
		) {
			return;
		}
		user.public_profile = nextValue;
	}

	function profileUpdateToastMessage(form: {
		left_shared_collections?: number;
		revoked_collection_invites?: number;
	}) {
		const messages: string[] = [$t('settings.update_success')];
		if ((form.left_shared_collections ?? 0) > 0) {
			messages.push(
				$t('settings.public_profile_left_collections', {
					values: { count: form.left_shared_collections ?? 0 }
				})
			);
		}
		if ((form.revoked_collection_invites ?? 0) > 0) {
			messages.push(
				$t('settings.public_profile_revoked_invites', {
					values: { count: form.revoked_collection_invites ?? 0 }
				})
			);
		}
		return messages.join(' ');
	}

	onMount(() => {
		if (!browser) return;
		activeSection = normalizeSection($page.url.searchParams.get('tab'));
		if ($page.url.searchParams.get('page') === 'success') {
			addToast('success', $t('settings.update_success'));
		}
	});

	run(() => {
		if (browser && $page.form?.success) {
			const leftShared = $page.form.left_shared_collections ?? 0;
			const revokedInvites = $page.form.revoked_collection_invites ?? 0;
			if (leftShared > 0 || revokedInvites > 0) {
				addToast('success', profileUpdateToastMessage($page.form));
				user.shared_collection_count = 0;
				user.pending_collection_invite_count = Math.max(
					0,
					(user.pending_collection_invite_count ?? 0) - revokedInvites
				);
				window.location.href = '/settings?tab=profile';
			} else {
				window.location.href = '/settings?page=success';
			}
		}
		if (browser && $page.form?.error) addToast('error', $t('settings.update_error'));
		if (browser && $page.form) isRestoring = false;
	});

	async function checkVisitedRegions() {
		const res = await fetch('/api/reverse-geocode/mark_visited_region/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		const result = await res.json();
		if (res.ok) {
			addToast(
				'success',
				`${result.new_regions} ${$t('adventures.regions_updated')}. ${result.new_cities} ${$t('adventures.cities_updated')}.`
			);
		} else {
			addToast('error', $t('adventures.error_updating_regions'));
		}
	}

	async function removeEmail(email: { email: string; verified?: boolean; primary?: boolean }) {
		const res = await fetch('/auth/browser/v1/account/email', {
			method: 'DELETE',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: email.email })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_removed'));
			emails = emails.filter((e) => e.email !== email.email);
		} else {
			addToast('error', $t('settings.email_removed_error'));
		}
	}

	async function disablePassword() {
		const method = user.disable_password ? 'POST' : 'DELETE';
		const res = await fetch('/auth/disable-password/', {
			method,
			headers: { 'Content-Type': 'application/json' }
		});
		if (res.ok) {
			addToast(
				'success',
				$t(user.disable_password ? 'settings.password_disabled' : 'settings.password_enabled')
			);
		} else {
			addToast(
				'error',
				$t(
					user.disable_password
						? 'settings.password_disabled_error'
						: 'settings.password_enabled_error'
				)
			);
			user.disable_password = !user.disable_password;
		}
	}

	async function verifyEmail(email: { email: string; verified?: boolean; primary?: boolean }) {
		const res = await fetch('/auth/browser/v1/account/email', {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: email.email })
		});
		if (res.ok) addToast('success', $t('settings.verify_email_success'));
		else addToast('error', $t('settings.verify_email_error'));
	}

	async function addEmail() {
		const res = await fetch('/auth/browser/v1/account/email', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: new_email })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_added'));
			emails = [...emails, { email: new_email, verified: false, primary: false }];
			new_email = '';
		} else {
			const error = await res.json();
			addToast('error', $t(`settings.${error.errors[0].code}`) || $t('settings.generic_error'));
		}
	}

	async function primaryEmail(email: { email: string; verified?: boolean; primary?: boolean }) {
		const res = await fetch('/auth/browser/v1/account/email', {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email: email.email, primary: true })
		});
		if (res.ok) {
			addToast('success', $t('settings.email_set_primary'));
			emails = emails.map((e) => ({ ...e, primary: e.email === email.email }));
		} else {
			addToast('error', $t('settings.email_set_primary_error'));
		}
	}

	async function disableMfa() {
		if (isDisablingMfa) return;
		isDisablingMfa = true;
		try {
			const res = await fetch('/auth/browser/v1/account/authenticators/totp', {
				method: 'DELETE',
				credentials: 'include'
			});
			if (res.ok) {
				mfaDisableNeedsReauth = false;
				mfaDisablePassword = '';
				mfaDisableReauthError = false;
				addToast('success', $t('settings.mfa_disabled'));
				data.props.authenticators = false;
				return;
			}

			let body: unknown = null;
			try {
				body = await res.json();
			} catch {
				/* ignore parse errors */
			}

			if (isReauthRequired(res, body)) {
				if (user?.has_password === false) {
					mfaDisableNeedsReauth = false;
					addToast('error', $t('settings.reset_session_error'));
					return;
				}
				mfaDisableNeedsReauth = true;
				addToast('info', $t('settings.reauth_required_disable_desc'));
				return;
			}

			addToast('error', $t('settings.generic_error'));
		} finally {
			isDisablingMfa = false;
		}
	}

	async function verifyMfaDisablePassword() {
		if (!mfaDisablePassword || isVerifyingMfaDisablePassword) return;
		isVerifyingMfaDisablePassword = true;
		mfaDisableReauthError = false;
		try {
			const { ok, status } = await reauthenticateWithPassword(mfaDisablePassword);
			if (ok) {
				mfaDisableNeedsReauth = false;
				mfaDisablePassword = '';
				mfaDisableReauthError = false;
				addToast('success', $t('settings.reauth_success'));
				await disableMfa();
				return;
			}
			if (status === 400) {
				mfaDisableReauthError = true;
				return;
			}
			addToast('error', $t('settings.generic_error'));
		} finally {
			isVerifyingMfaDisablePassword = false;
		}
	}

	function cancelMfaDisableReauth() {
		mfaDisableNeedsReauth = false;
		mfaDisablePassword = '';
		mfaDisableReauthError = false;
	}

	async function createApiKey() {
		if (!newApiKeyName.trim()) return;
		const res = await fetch('/auth/api-keys/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name: newApiKeyName.trim() })
		});
		if (res.ok) {
			const created = await res.json();
			newlyCreatedKey = created.key;
			keyCopied = false;
			apiKeys = [
				...apiKeys,
				{
					id: created.id,
					name: created.name,
					key_prefix: created.key_prefix,
					created_at: created.created_at,
					last_used_at: created.last_used_at
				}
			];
			newApiKeyName = '';
		} else {
			addToast('error', $t('api_keys.create_error'));
		}
	}

	async function copyKey() {
		if (!newlyCreatedKey) return;
		try {
			await navigator.clipboard.writeText(newlyCreatedKey);
			keyCopied = true;
			setTimeout(() => (keyCopied = false), 2000);
		} catch {
			addToast('error', $t('api_keys.copy_error'));
		}
	}

	async function deleteApiKey(id: string) {
		const res = await fetch(`/auth/api-keys/${id}/`, { method: 'DELETE' });
		if (res.ok) {
			apiKeys = apiKeys.filter((k) => k.id !== id);
			addToast('success', $t('api_keys.key_revoked'));
		} else {
			addToast('error', $t('api_keys.revoke_error'));
		}
	}

	async function revokeSessions(ids: number[]) {
		if (!ids.length || isRevokingSession) return;
		isRevokingSession = true;
		try {
			const res = await fetch('/auth/browser/v1/auth/sessions', {
				method: 'DELETE',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ sessions: ids })
			});
			if (res.status === 401) {
				await goto('/login');
				return;
			}
			if (!res.ok) {
				addToast('error', $t('settings.sessions_revoke_error'));
				return;
			}
			const payload = await res.json();
			sessions = Array.isArray(payload?.data)
				? payload.data
				: sessions.filter((s) => !ids.includes(s.id));
			addToast(
				'success',
				ids.length > 1 ? $t('settings.sessions_others_revoked') : $t('settings.sessions_revoked')
			);
		} catch {
			addToast('error', $t('settings.sessions_revoke_error'));
		} finally {
			isRevokingSession = false;
		}
	}

	function revokeSession(id: number) {
		return revokeSessions([id]);
	}

	function revokeOtherSessions() {
		if (!confirm($t('settings.sessions_revoke_others_confirm'))) return;
		const otherIds = sessions.filter((s) => !s.is_current).map((s) => s.id);
		return revokeSessions(otherIds);
	}

	function confirmDeleteAccount() {
		return confirm($t('settings.delete_account_confirm_prompt'));
	}
</script>

{#if isMFAModalOpen}
	<TotpModal
		user={data.user}
		on:close={() => (isMFAModalOpen = false)}
		bind:is_enabled={data.props.authenticators}
	/>
{/if}

<div class="min-h-screen bg-gradient-to-br from-base-200 to-base-300">
	<div class="bg-base-100 shadow-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-8 max-w-7xl">
			<h1 class="text-4xl font-bold text-primary">{$t('settings.settings_page')}</h1>
			<p class="mt-1 font-medium text-base-content/80">{$t('settings.account_settings')}</p>
		</div>
	</div>

	<div class="container mx-auto px-6 py-8 max-w-7xl">
		<div class="flex flex-col lg:flex-row gap-8">
			<aside class="lg:w-64 shrink-0">
				<SettingsNav {activeSection} isStaff={user.is_staff} onSelect={setActiveSection} />
			</aside>

			<main class="flex-1 min-w-0">
				{#if activeSection === 'profile'}
					<ProfileSettingsPanel {user} onPublicProfileToggle={handlePublicProfileToggle} />
				{:else if activeSection === 'emails'}
					<EmailsSettingsPanel
						{emails}
						bind:newEmail={new_email}
						onVerify={verifyEmail}
						onMakePrimary={primaryEmail}
						onRemove={removeEmail}
						onAdd={addEmail}
					/>
				{:else if activeSection === 'security'}
					<SecuritySettingsPanel
						{user}
						{emails}
						authenticators={data.props.authenticators}
						{socialProviders}
						publicUrl={public_url}
						{passwordPolicy}
						bind:newPassword
						bind:confirmPassword
						{apiKeys}
						bind:newApiKeyName
						{newlyCreatedKey}
						{keyCopied}
						{sessions}
						{isRevokingSession}
						{mfaDisableNeedsReauth}
						bind:mfaDisablePassword
						{mfaDisableReauthError}
						{isDisablingMfa}
						{isVerifyingMfaDisablePassword}
						onEnableMfa={() => (isMFAModalOpen = true)}
						onDisableMfa={disableMfa}
						onVerifyMfaDisablePassword={verifyMfaDisablePassword}
						onCancelMfaDisableReauth={cancelMfaDisableReauth}
						onDisablePassword={disablePassword}
						onCreateApiKey={createApiKey}
						onCopyKey={copyKey}
						onDeleteApiKey={deleteApiKey}
						onRevokeSession={revokeSession}
						onRevokeOtherSessions={revokeOtherSessions}
						onDismissNewKey={() => {
							newlyCreatedKey = null;
							keyCopied = false;
						}}
					/>
				{:else if activeSection === 'integrations'}
					<IntegrationsSettings
						{user}
						bind:immichIntegration
						bind:googleMapsEnabled
						bind:stravaGlobalEnabled
						bind:stravaUserEnabled
						bind:wandererEnabled
						bind:wandererIntegration
						bind:endurainEnabled
						bind:endurainIntegration
					/>
				{:else if activeSection === 'data'}
					<DataSettingsPanel
						{mediaUsage}
						{formatBytes}
						{totalMediaBytes}
						{mediaLimitBytes}
						{totalMediaFiles}
						{overallUsagePercent}
						{imagesPercent}
						{attachmentsPercent}
						{profilePicsPercent}
						{mediaLimitLabel}
						bind:acknowledgeRestoreOverride
						{isRestoring}
						onRestoreStart={() => (isRestoring = true)}
					/>
				{:else if activeSection === 'danger'}
					<DangerZoneSettingsPanel
						{user}
						bind:deleteConfirmation
						bind:deletePassword
						{isDeletingAccount}
						{canDeleteAccount}
						onDeleteSubmit={confirmDeleteAccount}
					/>
				{:else if activeSection === 'about'}
					<AboutSettingsPanel {user} />
				{:else if activeSection === 'admin'}
					{#if user.is_staff}
						<AdminSettingsPanel publicUrl={public_url} onUpdateRegions={checkVisitedRegions} />
					{:else}
						<div class="bg-base-100 rounded-2xl shadow-xl p-12 text-center">
							<div class="text-6xl mb-4">🔒</div>
							<h2 class="text-2xl font-bold mb-2">{$t('settings.access_restricted')}</h2>
							<p class="text-base-content/70">{$t('settings.access_restricted_desc')}</p>
						</div>
					{/if}
				{/if}
			</main>
		</div>
	</div>
</div>

<svelte:head>
	<title>User Settings | AdventureLog</title>
	<meta
		name="description"
		content="Manage your AdventureLog profile, security, integrations, data, and account settings."
	/>
</svelte:head>
