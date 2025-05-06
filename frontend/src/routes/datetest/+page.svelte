<script>
	import DateRangeDropdown from '$lib/components/DateRangeDropdown.svelte';

	let utcStartDate = '';
	let utcEndDate = '';
</script>

<DateRangeDropdown bind:utcStartDate bind:utcEndDate />

<p>{new Date(utcStartDate).toLocaleString()} - {new Date(utcEndDate).toLocaleString()}</p>

<p>UTC Start Date: {utcStartDate}</p>
<p>UTC End Date: {utcEndDate}</p>
