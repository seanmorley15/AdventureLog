<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { t } from 'svelte-i18n';

	// Icons
	import Account from '~icons/mdi/account';
	import MapMarker from '~icons/mdi/map-marker';
	import Shield from '~icons/mdi/shield-account';
	import Settings from '~icons/mdi/cog';
	import Logout from '~icons/mdi/logout';
	import Phone from '~icons/mdi/cellphone';
	import CreditCard from '~icons/mdi/credit-card';

	import MobileQR from '$lib/components/MobileQR.svelte';
	import UserAvatar from '$lib/components/UserAvatar.svelte';

	export let user: any;
	export let cloudMode = false;

	let showMobileQR = false;
	let showDevMobileLogin = false;
	let typedBuffer = '';
	const DEV_UNLOCK_KEYWORD = 'dev';

	// Get display name
	$: displayName = user.first_name
		? `${user.first_name} ${user.last_name || ''}`.trim()
		: user.username || 'User';

	// Menu items for better organization
	const menuItems = [
		{
			path: `/profile/${user.username}`,
			icon: Account,
			label: 'navbar.profile',
			section: 'main'
		},
		{
			path: '/locations',
			icon: MapMarker,
			label: 'locations.my_locations',
			section: 'main'
		},
		{
			path: '/settings',
			icon: Settings,
			label: 'navbar.settings',
			section: 'secondary'
		}
	];

	// Add admin item if user is staff
	$: adminMenuItem = user.is_staff
		? {
				path: '/admin',
				icon: Shield,
				label: 'navbar.admin_panel',
				section: 'secondary'
			}
		: null;

	function openMobileQR() {
		showMobileQR = true;
	}

	function closeMobileQR() {
		showMobileQR = false;
	}

	onMount(() => {
		const handleKeydown = (event: KeyboardEvent) => {
			if (event.metaKey || event.ctrlKey || event.altKey) return;
			if (event.key.length !== 1) return;

			typedBuffer = (typedBuffer + event.key.toLowerCase()).slice(-DEV_UNLOCK_KEYWORD.length);
			if (typedBuffer === DEV_UNLOCK_KEYWORD) {
				showDevMobileLogin = true;
			}
		};

		window.addEventListener('keydown', handleKeydown);

		return () => {
			window.removeEventListener('keydown', handleKeydown);
		};
	});
</script>

<div class="dropdown dropdown-bottom dropdown-end z-[999]">
	<div
		tabindex="0"
		role="button"
		class="btn btn-ghost btn-circle avatar hover:bg-base-200 transition-colors"
	>
		<div
			class="w-10 rounded-full ring-2 ring-primary/20 hover:ring-primary/40 transition-all overflow-hidden"
		>
			<UserAvatar
				{user}
				alt={$t('navbar.profile')}
				className="w-10 h-10 rounded-full"
				textClass="text-sm"
			/>
		</div>
	</div>

	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<ul
		tabindex="-1"
		class="dropdown-content z-[999] menu p-4 shadow-2xl bg-base-100 border border-base-300 rounded-2xl w-72 mt-2"
	>
		<!-- User Info Header -->
		<div class="px-2 py-3 mb-3 border-b border-base-300">
			<div class="flex items-center gap-3">
				<div class="avatar placeholder">
					<div class="w-12 rounded-full ring-2 ring-primary/20 overflow-hidden">
						<UserAvatar
							{user}
							alt={$t('navbar.profile')}
							className="w-12 h-12 rounded-full"
							textClass="text-lg"
						/>
					</div>
				</div>
				<div class="flex-1 min-w-0">
					<p class="font-semibold text-base text-base-content truncate">
						{$t('navbar.greeting')}, {displayName}
					</p>
					<p class="text-sm text-base-content/60 truncate">
						@{user.username}
					</p>
				</div>
			</div>
		</div>

		<!-- Main Menu Items -->
		<div class="space-y-1 mb-3">
			{#each menuItems.filter((item) => item.section === 'main') as item}
				<li>
					<button
						class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-base-200"
						on:click={() => goto(item.path)}
					>
						<svelte:component this={item.icon} class="w-5 h-5 text-base-content/70" />
						<span>{$t(item.label)}</span>
					</button>
				</li>
			{/each}
		</div>

		<div class="divider my-2"></div>

		<!-- Secondary Menu Items -->
		<div class="space-y-1 mb-3">
			{#if adminMenuItem}
				<li>
					<button
						class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-base-200"
						on:click={() => goto(adminMenuItem.path)}
					>
						<svelte:component this={adminMenuItem.icon} class="w-5 h-5 text-warning" />
						<span class="text-warning font-medium">{$t(adminMenuItem.label)}</span>
					</button>
				</li>
			{/if}

			{#if showDevMobileLogin}
				<!-- Mobile Login (dev unlock) -->
				<li>
					<button
						class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-base-200"
						on:click={openMobileQR}
					>
						<Phone class="w-5 h-5 text-base-content/70" />
						<span>{$t('navbar.mobile_login', { default: 'Mobile Login' })}</span>
					</button>
				</li>
			{/if}

			{#each menuItems.filter((item) => item.section === 'secondary') as item}
				<li>
					<button
						class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-base-200"
						on:click={() => goto(item.path)}
					>
						<svelte:component this={item.icon} class="w-5 h-5 text-base-content/70" />
						<span>{$t(item.label)}</span>
					</button>
				</li>
			{/each}

			{#if cloudMode}
				<li>
					<button
						class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-base-200"
						on:click={() => goto('/subscribe')}
					>
						<CreditCard class="w-5 h-5 text-base-content/70" />
						<span>{$t('navbar.billing')}</span>
					</button>
				</li>
			{/if}
		</div>

		<div class="divider my-2"></div>

		<!-- Logout -->
		<form method="post" class="w-full">
			<li class="w-full">
				<button
					formaction="/?/logout"
					class="btn btn-ghost justify-start gap-3 w-full text-left rounded-xl hover:bg-error/10 hover:text-error transition-colors"
				>
					<Logout class="w-5 h-5" />
					<span>{$t('navbar.logout')}</span>
				</button>
			</li>
		</form>
	</ul>
</div>

{#if showMobileQR}
	<MobileQR on:close={closeMobileQR} />
{/if}
