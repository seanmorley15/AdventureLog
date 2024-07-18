<script lang="ts">
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
					<!-- <button
						class="btn btn-sm btn-error"
						on:click={() => {
							activities = activities.filter((a) => a !== activity);
						}}>Remove</button
					> -->
				</td>
			</tr>
		{/each}
	</tbody>
</table>
<!-- 		</ul> -->
