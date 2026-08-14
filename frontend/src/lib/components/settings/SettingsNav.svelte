<script lang="ts">
	import { t } from 'svelte-i18n';

	interface Props {
		activeSection: string;
		isStaff?: boolean;
		onSelect: (sectionId: string) => void;
	}

	let { activeSection, isStaff = false, onSelect }: Props = $props();

	type NavItem = { id: string; icon: string; label: () => string };

	let navItems = $derived([
		{ id: 'profile', icon: '👤', label: () => $t('navbar.profile') },
		{ id: 'emails', icon: '📧', label: () => $t('settings.emails') },
		{ id: 'security', icon: '🔒', label: () => $t('settings.security') },
		{ id: 'integrations', icon: '🔗', label: () => $t('settings.integrations') },
		{ id: 'data', icon: '📦', label: () => $t('settings.data_and_storage') },
		...(!isStaff ? [{ id: 'danger', icon: '⚠️', label: () => $t('settings.danger_zone') }] : []),
		{ id: 'about', icon: 'ℹ️', label: () => $t('settings.about') },
		...(isStaff ? [{ id: 'admin', icon: '⚙️', label: () => $t('settings.administration') }] : [])
	] satisfies NavItem[]);
</script>

<div class="bg-base-100 rounded-2xl shadow-xl p-6 sticky top-8">
	<nav>
		<ul class="menu menu-vertical w-full space-y-1 p-0">
			{#each navItems as item}
				<li>
					<button
						type="button"
						class="flex items-center gap-3 p-3 rounded-xl transition-all duration-200 w-full {activeSection ===
						item.id
							? item.id === 'danger'
								? 'bg-error text-error-content shadow-lg'
								: 'bg-primary text-primary-content shadow-lg'
							: 'hover:bg-base-200'}"
						onclick={() => onSelect(item.id)}
					>
						<span class="text-xl">{item.icon}</span>
						<span class="font-medium">{item.label()}</span>
					</button>
				</li>
			{/each}
		</ul>
	</nav>
</div>
