<script lang="ts">
	import type { Subscription } from '$lib/types';
	import { page } from '$app/stores';

	export let data;

	const subscription: Subscription | null = data.subscription ?? null;
	const cloudMode = data.cloudMode ?? false;
	const hasAccess = data.hasAccess ?? true;

	const statusLabels: Record<string, string> = {
		trial: 'Trial',
		active: 'Active',
		canceled: 'Canceled',
		past_due: 'Past due'
	};

	const statusStyles: Record<string, string> = {
		trial: 'badge-info',
		active: 'badge-success',
		canceled: 'badge-ghost',
		past_due: 'badge-warning'
	};

	$: statusLabel = subscription ? statusLabels[subscription.status] || 'Unknown' : 'Unknown';
	$: trialEndsAt = subscription?.trial_ends_at ? new Date(subscription.trial_ends_at) : null;
	$: daysRemaining = trialEndsAt
		? Math.max(0, Math.ceil((trialEndsAt.getTime() - Date.now()) / (1000 * 60 * 60 * 24)))
		: null;
	$: isActive = subscription?.status === 'active';
	$: isTrial = subscription?.status === 'trial';
	$: hasScheduledSubscription = isTrial && Boolean(subscription?.stripe_subscription_id);
	$: disableCheckout = !cloudMode || isActive || hasScheduledSubscription;
	$: canManageBilling = cloudMode && Boolean(subscription?.stripe_subscription_id);
	$: statusStyle = subscription
		? statusStyles[subscription.status] || 'badge-ghost'
		: 'badge-ghost';
</script>

<div class="max-w-5xl mx-auto px-6 py-10">
	<div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
		<div>
			<div class="badge badge-outline mb-3">AdventureLog Cloud</div>
			<h1 class="text-3xl font-semibold">Billing & Subscription</h1>
			<p class="text-base-content/70 mt-2 max-w-2xl">
				Manage your hosted AdventureLog subscription, payment method, and trial status.
			</p>
		</div>
		{#if subscription}
			<div class="flex items-center gap-2">
				<span class={`badge ${statusStyle}`}>{statusLabel}</span>
				{#if hasScheduledSubscription && trialEndsAt}
					<span class="text-sm text-base-content/60">
						Billing starts {trialEndsAt.toLocaleDateString()}
					</span>
				{/if}
			</div>
		{/if}
	</div>

	<div class="divider my-8"></div>

	{#if !cloudMode}
		<div role="alert" class="alert alert-info mb-8">
			<div>
				<p class="font-semibold">Cloud billing is not enabled.</p>
				<p class="text-sm opacity-80">
					This instance is running in self-hosted mode. All features are unlocked.
				</p>
			</div>
		</div>
	{:else if !hasAccess}
		<div role="alert" class="alert alert-warning mb-8">
			<div>
				<p class="font-semibold">Your trial has ended.</p>
				<p class="text-sm opacity-80">Subscribe to restore access and keep your data in sync.</p>
			</div>
		</div>
	{/if}

	{#if $page.form?.message}
		<div role="alert" class="alert alert-error mb-8">
			<div>
				<p class="font-semibold">Checkout failed.</p>
				<p class="text-sm opacity-80">{$page.form.message}</p>
			</div>
		</div>
	{/if}

	<div class="grid gap-6 lg:grid-cols-[2fr_1fr]">
		<div class="card bg-base-100 border border-base-300 shadow-sm">
			<div class="card-body">
				<h2 class="card-title">Plan details</h2>
				<div class="flex flex-wrap items-center gap-2">
					<span class="badge badge-primary">4.99 USD / month</span>
					<span class="badge badge-ghost">30-day trial</span>
					<span class="badge badge-ghost">Unlimited usage</span>
				</div>
				<ul class="list-disc list-inside text-base-content/80 space-y-1 mt-3">
					<li>Managed hosting with automatic updates</li>
					<li>Backups and media storage included</li>
					<li>Sync across devices</li>
				</ul>

				<form method="POST" action="?/subscribe" class="mt-6">
					<button type="submit" class="btn btn-primary" disabled={disableCheckout}>
						{#if isActive}
							You are subscribed
						{:else if hasScheduledSubscription}
							Subscription scheduled
						{:else}
							Subscribe for 4.99 USD/month
						{/if}
					</button>
				</form>

				{#if canManageBilling}
					<form method="POST" action="?/manageBilling" class="mt-3">
						<button type="submit" class="btn btn-outline">Manage billing in Stripe</button>
					</form>
				{/if}
			</div>
		</div>

		<div class="card bg-base-100 border border-base-300 shadow-sm">
			<div class="card-body">
				<h2 class="card-title">Account status</h2>
				<p class="text-base-content/70">Status: {statusLabel}</p>
				{#if hasScheduledSubscription && trialEndsAt}
					<p class="text-sm text-base-content/70 mt-2">
						Paid billing starts on {trialEndsAt.toLocaleDateString()}.
					</p>
				{:else if isTrial && daysRemaining !== null}
					<p class="text-sm text-base-content/70 mt-2">
						{daysRemaining} day{daysRemaining === 1 ? '' : 's'} left in your trial.
					</p>
				{/if}
				{#if subscription?.current_period_ends_at}
					<p class="text-sm text-base-content/70 mt-2">
						Current period ends on
						{new Date(subscription.current_period_ends_at).toLocaleDateString()}.
					</p>
				{/if}
				{#if subscription?.cancel_at_period_end}
					<p class="text-sm text-warning mt-2">
						Cancellation scheduled at the end of the billing period.
					</p>
				{/if}
			</div>
		</div>
	</div>
</div>

<svelte:head>
	<title>Billing & Subscription</title>
	<meta
		name="description"
		content="Manage your AdventureLog Cloud subscription, billing, and trial status."
	/>
</svelte:head>
