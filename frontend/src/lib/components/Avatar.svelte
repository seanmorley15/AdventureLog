<script lang="ts">
	import { goto } from '$app/navigation';
	import { t } from 'svelte-i18n';

	// Icons
	import Account from '~icons/mdi/account';
	import MapMarker from '~icons/mdi/map-marker';
	import Shield from '~icons/mdi/shield-account';
	import Settings from '~icons/mdi/cog';
	import Logout from '~icons/mdi/logout';

	export let user: any;

	let letter: string = user.first_name?.[0] || user.username?.[0] || '?';

	// Get display name
	$: displayName = user.first_name
		? `${user.first_name} ${user.last_name || ''}`.trim()
		: user.username || 'User';

	// Get initials for fallback
	$: initials =
		user.first_name && user.last_name ? `${user.first_name[0]}${user.last_name[0]}` : letter;

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
</script>

<div class="dropdown dropdown-bottom dropdown-end z-[100]">
	<div
		tabindex="0"
		role="button"
		class="btn btn-ghost btn-circle avatar hover:bg-base-200 transition-colors"
	>
		<div class="w-10 rounded-full ring-2 ring-primary/20 hover:ring-primary/40 transition-all">
			{#if user.profile_pic}
				<img src={user.profile_pic} alt={$t('navbar.profile')} class="rounded-full object-cover" />
			{:else}
				<div
					class="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-primary-content font-semibold text-sm"
				>
					{initials.toUpperCase()}
				</div>
			{/if}
		</div>
	</div>

	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<ul
		tabindex="0"
		class="dropdown-content z-[100] menu p-4 shadow-2xl bg-base-100 border border-base-300 rounded-2xl w-72 mt-2"
	>
		<!-- User Info Header -->
		<div class="px-2 py-3 mb-3 border-b border-base-300">
			<div class="flex items-center gap-3">
				<div class="avatar placeholder">
					<div class="w-12 rounded-full ring-2 ring-primary/20">
						{#if user.profile_pic}
							<img
								src={user.profile_pic}
								alt={$t('navbar.profile')}
								class="rounded-full object-cover"
							/>
						{:else}
							<div
								class="w-12 h-12 bg-gradient-to-br from-primary to-secondary rounded-full flex items-center justify-center text-primary-content font-semibold text-lg"
								style="line-height: 3rem;"
							>
								{initials.toUpperCase()}
							</div>
						{/if}
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
