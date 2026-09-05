<script lang="ts">
	import { page } from '$app/stores';
	import { t } from 'svelte-i18n';
	import type { Subscription } from '$lib/types';
	import { dateFormatFromUser, formatDisplayDate } from '$lib/dateFormat';

	interface Props {
		subscription?: Subscription | null;
		hasAccess?: boolean;
		cloudMode?: boolean;
	}

	let { subscription = null, hasAccess = true, cloudMode = false }: Props = $props();

	const msPerDay = 1000 * 60 * 60 * 24;
	const dateFormat = $derived(dateFormatFromUser($page.data?.user));

	let trialEndsAt = $derived(subscription?.trial_ends_at ? new Date(subscription.trial_ends_at) : null);
	let daysRemaining = $derived(trialEndsAt
		? Math.max(0, Math.ceil((trialEndsAt.getTime() - Date.now()) / msPerDay))
		: null);
	let isTrial = $derived(subscription?.status === 'trial');
	let hasScheduledSubscription = $derived(Boolean(subscription?.stripe_subscription_id));
	let isPaidTrial = $derived(isTrial && hasScheduledSubscription);
	let hideOnBillingPage = $derived($page.url.pathname.startsWith('/subscribe'));

	function formatBillingDate(date: Date) {
		return formatDisplayDate(date.toISOString().split('T')[0], dateFormat);
	}
</script>

{#if cloudMode && subscription && !hideOnBillingPage}
	{#if !hasAccess}
		<div role="alert" class="alert alert-warning rounded-none border-b border-warning/40 shadow-xs">
			<div>
				<p class="font-semibold">{$t('billing.banner_access_paused_title')}</p>
				<p class="text-sm opacity-80">{$t('billing.banner_access_paused_description')}</p>
			</div>
			<a href="/subscribe" class="btn btn-primary btn-sm">{$t('billing.banner_subscribe')}</a>
		</div>
	{:else if isPaidTrial}
		<div role="alert" class="alert alert-success rounded-none border-b border-success/40 shadow-xs">
			<div>
				<p class="font-semibold">{$t('billing.banner_scheduled_title')}</p>
				<p class="text-sm opacity-80">
					{#if trialEndsAt}
						{$t('billing.banner_scheduled_description', {
							values: {
								date: formatBillingDate(trialEndsAt)
							}
						})}
					{:else}
						{$t('billing.banner_scheduled_description_fallback')}
					{/if}
				</p>
			</div>
		</div>
	{:else if isTrial}
		<div role="alert" class="alert alert-info rounded-none border-b border-info/40 shadow-xs">
			<div>
				<p class="font-semibold">{$t('billing.banner_trial_active_title')}</p>
				<p class="text-sm opacity-80">
					{#if daysRemaining !== null}
						{$t(
							daysRemaining === 1
								? 'billing.banner_trial_active_description_one'
								: 'billing.banner_trial_active_description_other',
							{ values: { days: daysRemaining } }
						)}
					{:else}
						{$t('billing.alert_trial_active_description', {
							values: { days: 0, count: 0 }
						})}
					{/if}
				</p>
			</div>
			<a href="/subscribe" class="btn btn-primary btn-sm">{$t('billing.banner_manage_billing')}</a>
		</div>
	{/if}
{/if}
