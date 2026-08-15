<script lang="ts">
	import type { Subscription } from '$lib/types';

	export let subscription: Subscription | null = null;
	export let hasAccess = true;
	export let cloudMode = false;

	const msPerDay = 1000 * 60 * 60 * 24;

	$: trialEndsAt = subscription?.trial_ends_at ? new Date(subscription.trial_ends_at) : null;
	$: daysRemaining = trialEndsAt
		? Math.max(0, Math.ceil((trialEndsAt.getTime() - Date.now()) / msPerDay))
		: null;
	$: isTrial = subscription?.status === 'trial';
	$: hasScheduledSubscription = Boolean(subscription?.stripe_subscription_id);
	$: isPaidTrial = isTrial && hasScheduledSubscription;
</script>

{#if cloudMode && subscription}
	{#if !hasAccess}
		<div role="alert" class="alert alert-warning rounded-none border-b border-warning/40">
			<div>
				<p class="font-semibold">Your AdventureLog Cloud access is paused.</p>
				<p class="text-sm opacity-80">
					Subscribe to restore full access and keep your data in sync.
				</p>
			</div>
			<a href="/subscribe" class="btn btn-primary btn-sm">Subscribe</a>
		</div>
	{:else if isPaidTrial}
		<div role="alert" class="alert alert-success rounded-none border-b border-success/40">
			<div>
				<p class="font-semibold">Subscription scheduled.</p>
				<p class="text-sm opacity-80">
					{#if trialEndsAt}
						Paid billing starts on {trialEndsAt.toLocaleDateString()}.
					{:else}
						Paid billing will start after your trial ends.
					{/if}
				</p>
			</div>
		</div>
	{:else if isTrial}
		<div role="alert" class="alert alert-info rounded-none border-b border-info/40">
			<div>
				<p class="font-semibold">AdventureLog Cloud trial active.</p>
				<p class="text-sm opacity-80">
					{#if daysRemaining !== null}
						{daysRemaining} day{daysRemaining === 1 ? '' : 's'} remaining in your trial.
					{:else}
						Your trial is active.
					{/if}
				</p>
			</div>
			<a href="/subscribe" class="btn btn-primary btn-sm">Manage billing</a>
		</div>
	{/if}
{/if}
