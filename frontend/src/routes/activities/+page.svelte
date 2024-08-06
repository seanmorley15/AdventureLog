<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';

	export let data: PageData;

	let activities: string[] = data.props.activities;
</script>

<!-- make a table with pinned rows -->
<table class="table table-compact">
	<thead>
		<tr>
			<th>Activity</th>
			<th>Actions</th>
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
						>See Adventures</button
					>
				</td>
			</tr>
		{/each}
	</tbody>
</table>

<svelte:head>
	<title>My Activities</title>
	<meta name="description" content="View my activity types." />
</svelte:head>
