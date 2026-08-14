<script lang="ts">
	import { t } from 'svelte-i18n';

	interface Props {
		activeSection: string;
		isStaff?: boolean;
		onSelect: (sectionId: string) => void;
	}

	let { activeSection, isStaff = false, onSelect }: Props = $props();

	type NavItem = { id: string; icon: string; label: () => string };

	let navItems = $derived(
		[
			{ id: 'profile', icon: '👤', label: () => $t('navbar.profile') },
			{ id: 'emails', icon: '📧', label: () => $t('settings.emails') },
			{ id: 'security', icon: '🔒', label: () => $t('settings.security') },
			{ id: 'integrations', icon: '🔗', label: () => $t('settings.integrations') },
			{ id: 'data', icon: '📦', label: () => $t('settings.data_and_storage') },
			...(!isStaff ? [{ id: 'danger', icon: '⚠️', label: () => $t('settings.danger_zone') }] : []),
			{ id: 'about', icon: 'ℹ️', label: () => $t('settings.about') },
			...(isStaff ? [{ id: 'admin', icon: '⚙️', label: () => $t('settings.administration') }] : [])
		] satisfies NavItem[]
	);
</script>

<div class="bg-base-100 rounded-2xl shadow-xl p-6 sticky top-8">
	<nav class="flex flex-col gap-1">
		{#each navItems as item (item.id)}
			<button
				type="button"
				class={[
					'flex items-center gap-3 w-full rounded-xl px-3 py-3 text-left font-semibold transition-all duration-200',
					activeSection === item.id
						? item.id === 'danger'
							? 'bg-error text-error-content shadow-lg'
							: 'bg-primary text-primary-content shadow-lg'
						: 'text-base-content hover:bg-base-200'
				]}
				onclick={() => onSelect(item.id)}
			>
				<span class="text-xl">{item.icon}</span>
				<span>{item.label()}</span>
			</button>
		{/each}
	</nav>
</div>
