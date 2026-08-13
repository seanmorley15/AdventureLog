<script lang="ts">
	import { enhance } from '$app/forms';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';
	import { addToast } from '$lib/toasts';
	import type { MediaUsage, Subscription, User } from '$lib/types';

	import CloudOutline from '~icons/mdi/cloud-outline';
	import CreditCardOutline from '~icons/mdi/credit-card-outline';
	import SyncIcon from '~icons/mdi/sync';
	import BackupRestore from '~icons/mdi/backup-restore';
	import UpdateIcon from '~icons/mdi/update';
	import HelpCircleOutline from '~icons/mdi/help-circle-outline';
	import OpenInNew from '~icons/mdi/open-in-new';
	import CheckCircle from '~icons/mdi/check-circle';
	import AlertCircle from '~icons/mdi/alert-circle';
	import CalendarClock from '~icons/mdi/calendar-clock';
	import DatabaseOutline from '~icons/mdi/database-outline';

	export let data;

	const subscription: Subscription | null = data.subscription ?? null;
	const cloudMode = data.cloudMode ?? false;
	const hasAccess = data.hasAccess ?? true;
	const user: User | null = data.user ?? null;
	const mediaUsage: MediaUsage =
		data.mediaUsage ??
		({
			total_bytes: 0,
			limit_bytes: null,
			images_bytes: 0,
			attachments_bytes: 0,
			profile_pics_bytes: 0,
			images_files: 0,
			attachments_files: 0,
			profile_pics_files: 0
		} as MediaUsage);

	const msPerDay = 1000 * 60 * 60 * 24;
	const planPrice = '4.99';
	const planCurrency = 'USD';

	let isSubscribing = false;
	let isOpeningPortal = false;
	let lastFormMessage: string | null = null;

	const statusConfig: Record<string, { labelKey: string; badgeClass: string; iconClass: string }> =
		{
			trial: {
				labelKey: 'billing.status_trial',
				badgeClass: 'badge-info',
				iconClass: 'text-info'
			},
			active: {
				labelKey: 'billing.status_active',
				badgeClass: 'badge-success',
				iconClass: 'text-success'
			},
			canceled: {
				labelKey: 'billing.status_canceled',
				badgeClass: 'badge-ghost',
				iconClass: 'text-base-content/60'
			},
			past_due: {
				labelKey: 'billing.status_past_due',
				badgeClass: 'badge-warning',
				iconClass: 'text-warning'
			}
		};

	const planFeatures = [
		{ icon: CloudOutline, key: 'billing.feature_hosting' },
		{ icon: UpdateIcon, key: 'billing.feature_updates' },
		{ icon: BackupRestore, key: 'billing.feature_backups' },
		{ icon: SyncIcon, key: 'billing.feature_sync' }
	];

	$: statusKey = subscription?.status ?? 'unknown';
	$: statusMeta = statusConfig[statusKey] ?? {
		labelKey: 'billing.status_unknown',
		badgeClass: 'badge-ghost',
		iconClass: 'text-base-content/60'
	};
	$: trialEndsAt = subscription?.trial_ends_at ? new Date(subscription.trial_ends_at) : null;
	$: periodEndsAt = subscription?.current_period_ends_at
		? new Date(subscription.current_period_ends_at)
		: null;
	$: daysRemaining = trialEndsAt
		? Math.max(0, Math.ceil((trialEndsAt.getTime() - Date.now()) / msPerDay))
		: null;
	$: trialProgress =
		daysRemaining !== null ? Math.min(100, Math.max(0, ((30 - daysRemaining) / 30) * 100)) : 0;
	$: isActive = subscription?.status === 'active';
	$: isTrial = subscription?.status === 'trial';
	$: isPastDue = subscription?.status === 'past_due';
	$: isCanceled = subscription?.status === 'canceled';
	$: hasScheduledSubscription = isTrial && Boolean(subscription?.stripe_subscription_id);
	$: disableCheckout =
		!cloudMode ||
		isActive ||
		hasScheduledSubscription ||
		(isPastDue && Boolean(subscription?.stripe_subscription_id));
	$: canManageBilling =
		cloudMode && Boolean(subscription?.stripe_customer_id || subscription?.stripe_subscription_id);

	$: totalMediaBytes = mediaUsage.total_bytes ?? 0;
	$: mediaLimitBytes = mediaUsage.limit_bytes ?? null;
	$: totalMediaFiles =
		(mediaUsage.images_files ?? 0) +
		(mediaUsage.attachments_files ?? 0) +
		(mediaUsage.profile_pics_files ?? 0);
	$: overallUsagePercent = mediaLimitBytes
		? Math.min(100, Math.round((totalMediaBytes / mediaLimitBytes) * 100))
		: 0;
	$: mediaLimitLabel = mediaLimitBytes ? formatBytes(mediaLimitBytes) : $t('billing.unlimited');

	function formatBytes(bytes: number) {
		if (!bytes || bytes <= 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
		const value = bytes / Math.pow(1024, index);
		const precision = value >= 10 || index === 0 ? 0 : 1;
		return `${value.toFixed(precision)} ${units[index]}`;
	}

	function formatDaysRemaining(days: number) {
		return days === 1
			? $t('billing.days_remaining_one', { values: { days } })
			: $t('billing.days_remaining_other', { values: { days } });
	}

	function formatDate(date: Date) {
		return date.toLocaleDateString(undefined, {
			year: 'numeric',
			month: 'long',
			day: 'numeric'
		});
	}

	function clearQueryParam(param: string) {
		if (!browser) return;
		const url = new URL(window.location.href);
		url.searchParams.delete(param);
		history.replaceState({}, '', url);
	}

	onMount(() => {
		if (!browser) return;

		const params = new URLSearchParams(window.location.search);
		if (params.get('success') === '1') {
			addToast('success', $t('billing.checkout_success'));
			clearQueryParam('success');
		}
		if (params.get('canceled') === '1') {
			addToast('info', $t('billing.checkout_canceled'));
			clearQueryParam('canceled');
		}
	});

	$: if (browser && $page.form?.message && $page.form.message !== lastFormMessage) {
		lastFormMessage = $page.form.message;
		const action = $page.form.action ?? 'subscribe';
		const title =
			action === 'portal' ? $t('billing.portal_error_title') : $t('billing.checkout_error_title');
		addToast('error', `${title}: ${$page.form.message}`);
	}

	function handleSubscribeEnhance() {
		isSubscribing = true;
		return async ({
			update,
			result
		}: {
			update: () => Promise<void>;
			result: { type: string };
		}) => {
			if (result.type !== 'redirect') {
				isSubscribing = false;
			}
			await update();
		};
	}

	function handlePortalEnhance() {
		isOpeningPortal = true;
		return async ({
			update,
			result
		}: {
			update: () => Promise<void>;
			result: { type: string };
		}) => {
			if (result.type !== 'redirect') {
				isOpeningPortal = false;
			}
			await update();
		};
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-base-200 to-base-300">
	<div class="bg-base-100 shadow-lg border-b border-base-300">
		<div class="container mx-auto px-6 py-8 max-w-5xl">
			<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
				<div>
					<div class="badge badge-outline badge-primary gap-2 mb-3">
						<CloudOutline class="w-3.5 h-3.5" />
						{$t('billing.cloud_badge')}
					</div>
					<h1 class="text-4xl font-bold text-primary pb-1">{$t('billing.page_title')}</h1>
					<p class="text-base-content/70 mt-2 max-w-2xl">{$t('billing.page_description')}</p>
				</div>
				{#if subscription && cloudMode}
					<div class="flex flex-col items-start md:items-end gap-2">
						<span class={`badge badge-lg ${statusMeta.badgeClass}`}>
							{$t(statusMeta.labelKey)}
						</span>
						{#if user}
							<p class="text-sm text-base-content/60">@{user.username}</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="container mx-auto px-6 py-8 max-w-5xl">
		<div class="space-y-8">
			{#if !cloudMode}
				<div role="alert" class="alert alert-info shadow-lg">
					<HelpCircleOutline class="w-6 h-6 shrink-0" />
					<div>
						<p class="font-semibold">{$t('billing.self_hosted_title')}</p>
						<p class="text-sm opacity-80">{$t('billing.self_hosted_description')}</p>
					</div>
				</div>
			{:else if !hasAccess}
				<div role="alert" class="alert alert-warning shadow-lg">
					<AlertCircle class="w-6 h-6 shrink-0" />
					<div>
						{#if isPastDue}
							<p class="font-semibold">{$t('billing.alert_past_due_title')}</p>
							<p class="text-sm opacity-80">{$t('billing.alert_past_due_description')}</p>
						{:else if isCanceled}
							<p class="font-semibold">{$t('billing.alert_canceled_title')}</p>
							<p class="text-sm opacity-80">{$t('billing.alert_canceled_description')}</p>
						{:else}
							<p class="font-semibold">{$t('billing.alert_trial_ended_title')}</p>
							<p class="text-sm opacity-80">{$t('billing.alert_trial_ended_description')}</p>
						{/if}
					</div>
				</div>
			{:else if hasScheduledSubscription}
				<div role="alert" class="alert alert-success shadow-lg">
					<CheckCircle class="w-6 h-6 shrink-0" />
					<div>
						<p class="font-semibold">{$t('billing.alert_scheduled_title')}</p>
						<p class="text-sm opacity-80">
							{#if trialEndsAt}
								{$t('billing.alert_scheduled_description', {
									values: { date: formatDate(trialEndsAt) }
								})}
							{:else}
								{$t('billing.alert_scheduled_description_fallback')}
							{/if}
						</p>
					</div>
				</div>
			{:else if isActive && subscription?.cancel_at_period_end}
				<div role="alert" class="alert alert-warning shadow-lg">
					<AlertCircle class="w-6 h-6 shrink-0" />
					<div>
						<p class="font-semibold">{$t('billing.alert_cancel_scheduled_title')}</p>
						<p class="text-sm opacity-80">
							{#if periodEndsAt}
								{$t('billing.alert_cancel_scheduled_description', {
									values: { date: formatDate(periodEndsAt) }
								})}
							{:else}
								{$t('billing.alert_cancel_scheduled_description_fallback')}
							{/if}
						</p>
					</div>
				</div>
			{/if}

			<div class="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
				<div class="space-y-8">
					<div class="bg-base-100 rounded-2xl shadow-xl p-8">
						<div class="flex items-center gap-4 mb-6">
							<div class="p-3 bg-primary/10 rounded-xl">
								<CreditCardOutline class="w-7 h-7 text-primary" />
							</div>
							<div>
								<h2 class="text-2xl font-bold">{$t('billing.plan_title')}</h2>
								<p class="text-base-content/70">{$t('billing.plan_description')}</p>
							</div>
						</div>

						<div
							class="p-6 bg-gradient-to-br from-primary/5 to-secondary/5 rounded-2xl border border-primary/10 mb-6"
						>
							<div class="flex flex-wrap items-end gap-3 mb-4">
								<div>
									<p class="text-sm text-base-content/60 uppercase tracking-wide font-medium">
										{$t('billing.monthly_price')}
									</p>
									<p class="text-4xl font-bold text-primary">
										{planPrice}
										<span class="text-lg font-medium text-base-content/70">{planCurrency}</span>
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<span class="badge badge-primary badge-outline">{$t('billing.trial_badge')}</span>
									<span class="badge badge-ghost">{$t('billing.unlimited_usage')}</span>
								</div>
							</div>

							<ul class="grid gap-3 sm:grid-cols-2">
								{#each planFeatures as feature}
									<li class="flex items-start gap-3">
										<div class="p-1.5 bg-base-100 rounded-lg shadow-sm">
											<svelte:component this={feature.icon} class="w-4 h-4 text-primary" />
										</div>
										<span class="text-sm text-base-content/80 pt-0.5">{$t(feature.key)}</span>
									</li>
								{/each}
							</ul>
						</div>

						<div class="flex flex-col sm:flex-row gap-3">
							{#if !(isPastDue && canManageBilling)}
								<form
									method="POST"
									action="?/subscribe"
									use:enhance={handleSubscribeEnhance}
									class="flex-1"
								>
									<button
										type="submit"
										class="btn btn-primary w-full"
										disabled={disableCheckout || isSubscribing}
									>
										{#if isSubscribing}
											<span class="loading loading-spinner loading-sm"></span>
											{$t('billing.redirecting_checkout')}
										{:else if isActive}
											<CheckCircle class="w-5 h-5" />
											{$t('billing.subscribed')}
										{:else if hasScheduledSubscription}
											<CalendarClock class="w-5 h-5" />
											{$t('billing.subscription_scheduled')}
										{:else if isCanceled}
											{$t('billing.resubscribe', {
												values: { price: planPrice, currency: planCurrency }
											})}
										{:else}
											{$t('billing.subscribe', {
												values: { price: planPrice, currency: planCurrency }
											})}
										{/if}
									</button>
								</form>
							{/if}

							{#if canManageBilling}
								<form
									method="POST"
									action="?/manageBilling"
									use:enhance={handlePortalEnhance}
									class={isPastDue ? 'flex-1' : ''}
								>
									<button
										type="submit"
										class="btn {isPastDue ? 'btn-primary' : 'btn-outline'} w-full sm:w-auto"
										disabled={isOpeningPortal}
									>
										{#if isOpeningPortal}
											<span class="loading loading-spinner loading-sm"></span>
										{:else}
											<OpenInNew class="w-4 h-4" />
										{/if}
										{isPastDue ? $t('billing.update_payment') : $t('billing.manage_billing')}
									</button>
								</form>
							{/if}
						</div>

						<p class="text-xs text-base-content/50 mt-4">
							{$t('billing.stripe_notice')}
						</p>
					</div>

					{#if cloudMode}
						<div class="bg-base-100 rounded-2xl shadow-xl p-8">
							<div class="flex items-center gap-4 mb-6">
								<div class="p-3 bg-secondary/10 rounded-xl">
									<DatabaseOutline class="w-7 h-7 text-secondary" />
								</div>
								<div>
									<h2 class="text-2xl font-bold">{$t('billing.storage_title')}</h2>
									<p class="text-base-content/70">{$t('billing.storage_description')}</p>
								</div>
							</div>

							<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-4">
								<p class="text-sm text-base-content/70">
									{#if mediaLimitBytes}
										{$t('billing.storage_using', {
											values: {
												used: formatBytes(totalMediaBytes),
												limit: mediaLimitLabel,
												percent: overallUsagePercent
											}
										})}
									{:else}
										{$t('billing.storage_using_unlimited', {
											values: { used: formatBytes(totalMediaBytes) }
										})}
									{/if}
								</p>
								<div class="badge badge-primary badge-lg">
									{#if mediaLimitBytes}
										{$t('billing.storage_percent_used', {
											values: { percent: overallUsagePercent }
										})}
									{:else}
										{$t('billing.unlimited')}
									{/if}
								</div>
							</div>

							<progress
								class="progress progress-primary w-full mb-6"
								value={mediaLimitBytes ? overallUsagePercent : 0}
								max="100"
							></progress>

							<div class="stats stats-vertical lg:stats-horizontal w-full bg-base-200 shadow-inner">
								<div class="stat py-4">
									<div class="stat-title">{$t('billing.storage_total')}</div>
									<div class="stat-value text-primary text-2xl">{formatBytes(totalMediaBytes)}</div>
									<div class="stat-desc">
										{totalMediaFiles}
										{$t('adventures.files')}
									</div>
								</div>
								<div class="stat py-4">
									<div class="stat-title">{$t('adventures.images')}</div>
									<div class="stat-value text-secondary text-2xl">
										{formatBytes(mediaUsage.images_bytes)}
									</div>
									<div class="stat-desc">
										{mediaUsage.images_files}
										{$t('adventures.files')}
									</div>
								</div>
								<div class="stat py-4">
									<div class="stat-title">{$t('adventures.attachments')}</div>
									<div class="stat-value text-accent text-2xl">
										{formatBytes(mediaUsage.attachments_bytes)}
									</div>
									<div class="stat-desc">
										{mediaUsage.attachments_files}
										{$t('adventures.files')}
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<div class="space-y-8">
					<div class="bg-base-100 rounded-2xl shadow-xl p-8">
						<div class="flex items-center gap-4 mb-6">
							<div class="p-3 bg-accent/10 rounded-xl">
								<CalendarClock class="w-7 h-7 text-accent" />
							</div>
							<div>
								<h2 class="text-xl font-bold">{$t('billing.account_status')}</h2>
								<p class="text-sm text-base-content/70">
									{$t('billing.account_status_description')}
								</p>
							</div>
						</div>

						<div class="space-y-4">
							<div class="flex items-center justify-between p-4 bg-base-200 rounded-xl">
								<span class="text-sm font-medium text-base-content/70"
									>{$t('billing.status_label')}</span
								>
								<span class={`badge ${statusMeta.badgeClass}`}>{$t(statusMeta.labelKey)}</span>
							</div>

							{#if isTrial && daysRemaining !== null && hasAccess}
								<div class="p-4 bg-base-200 rounded-xl">
									<div class="flex items-center justify-between mb-2">
										<span class="text-sm font-medium text-base-content/70">
											{$t('billing.trial_progress')}
										</span>
										<span class="text-sm font-semibold">
											{formatDaysRemaining(daysRemaining)}
										</span>
									</div>
									<progress class="progress progress-info w-full" value={trialProgress} max="100"
									></progress>
									{#if trialEndsAt}
										<p class="text-xs text-base-content/60 mt-2">
											{$t('billing.trial_ends', { values: { date: formatDate(trialEndsAt) } })}
										</p>
									{/if}
								</div>
							{/if}

							{#if hasScheduledSubscription && trialEndsAt}
								<div class="p-4 bg-base-200 rounded-xl">
									<p class="text-sm font-medium text-base-content/70">
										{$t('billing.billing_starts')}
									</p>
									<p class="font-semibold mt-1">{formatDate(trialEndsAt)}</p>
								</div>
							{/if}

							{#if periodEndsAt}
								<div class="p-4 bg-base-200 rounded-xl">
									<p class="text-sm font-medium text-base-content/70">
										{#if subscription?.cancel_at_period_end}
											{$t('billing.access_until')}
										{:else if isActive}
											{$t('billing.renews_on')}
										{:else}
											{$t('billing.period_ends')}
										{/if}
									</p>
									<p class="font-semibold mt-1">{formatDate(periodEndsAt)}</p>
								</div>
							{/if}

							{#if isActive && !subscription?.cancel_at_period_end}
								<div
									class="flex items-start gap-2 p-4 bg-success/10 rounded-xl border border-success/20"
								>
									<CheckCircle class="w-5 h-5 text-success shrink-0 mt-0.5" />
									<p class="text-sm text-base-content/80">{$t('billing.active_description')}</p>
								</div>
							{/if}
						</div>
					</div>

					<div class="bg-base-100 rounded-2xl shadow-xl p-8">
						<h2 class="text-xl font-bold mb-4">{$t('billing.help_title')}</h2>
						<div class="space-y-4">
							<div class="collapse collapse-arrow bg-base-200">
								<input type="checkbox" />
								<div class="collapse-title text-sm font-medium">
									{$t('billing.faq_trial_question')}
								</div>
								<div class="collapse-content text-sm text-base-content/70">
									<p>{$t('billing.faq_trial_answer')}</p>
								</div>
							</div>
							<div class="collapse collapse-arrow bg-base-200">
								<input type="checkbox" />
								<div class="collapse-title text-sm font-medium">
									{$t('billing.faq_cancel_question')}
								</div>
								<div class="collapse-content text-sm text-base-content/70">
									<p>{$t('billing.faq_cancel_answer')}</p>
								</div>
							</div>
							<div class="collapse collapse-arrow bg-base-200">
								<input type="checkbox" />
								<div class="collapse-title text-sm font-medium">
									{$t('billing.faq_payment_question')}
								</div>
								<div class="collapse-content text-sm text-base-content/70">
									<p>{$t('billing.faq_payment_answer')}</p>
								</div>
							</div>
						</div>

						<div class="divider my-4"></div>

						<a
							href="https://adventurelog.app"
							target="_blank"
							rel="noopener noreferrer"
							class="btn btn-ghost btn-sm gap-2"
						>
							<HelpCircleOutline class="w-4 h-4" />
							{$t('billing.learn_more')}
							<OpenInNew class="w-3.5 h-3.5 opacity-60" />
						</a>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<svelte:head>
	<title>{$t('billing.page_title')} | AdventureLog</title>
	<meta name="description" content={$t('billing.page_description')} />
</svelte:head>
