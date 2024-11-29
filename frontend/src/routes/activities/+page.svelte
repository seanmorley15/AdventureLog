<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import { t } from 'svelte-i18n';

	export let data: PageData;

	let activities: string[] = data.props.activities;
</script>

<!-- make a table with pinned rows -->
<table class="table table-compact">
	<thead>
		<tr>
			<th>{$t('navbar.tag')}</th>
			<th>{$t('adventures.actions')}</th>
		</tr>
	</thead>
	<tbody>
		{#each activities as activity}
			<tr>
				<td>{activity}</td>
				<td>
					<button
						class="btn btn-sm btn-primary"
						on:click={() => goto(`/search?query=${activity}&property=activity_types`)}
						>{$t('adventures.see_adventures')}</button
					>
				</td>
			</tr>
		{/each}
	</tbody>
</table>

<svelte:head>
	<title>My Tags</title>
	<meta name="description" content="View my tags." />
</svelte:head>
