<script lang="ts">
	import { t } from 'svelte-i18n';
	import SettingsCard from './SettingsCard.svelte';
	import SettingsSectionHeader from './SettingsSectionHeader.svelte';

	interface Props {
		publicUrl: string;
		onUpdateRegions: () => void;
	}

	let { publicUrl, onUpdateRegions }: Props = $props();
</script>

<SettingsCard>
	<SettingsSectionHeader
		icon="⚙️"
		iconBgClass="bg-error/10"
		title={$t('settings.administration')}
		description={$t('settings.administration_desc')}
	/>
	<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
		<div class="card bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20">
			<div class="card-body text-center">
				<div class="text-4xl mb-4">🛠️</div>
				<h3 class="card-title justify-center">{$t('navbar.admin_panel')}</h3>
				<p class="text-sm text-base-content/80 mb-4">{$t('settings.admin_panel_desc')}</p>
				<a class="btn btn-primary" href={`${publicUrl}/admin/`} target="_blank" rel="noreferrer">
					{$t('settings.launch_administration_panel')}
				</a>
			</div>
		</div>
		<div class="card bg-gradient-to-br from-info/10 to-success/10 border border-info/20">
			<div class="card-body text-center">
				<div class="text-4xl mb-4">📍</div>
				<h3 class="card-title justify-center">{$t('settings.region_updates')}</h3>
				<p class="text-sm text-base-content/80 mb-4">{$t('settings.region_updates_desc')}</p>
				<button class="btn btn-info" onclick={onUpdateRegions}>
					{$t('adventures.update_visited_regions')}
				</button>
			</div>
		</div>
	</div>
</SettingsCard>
