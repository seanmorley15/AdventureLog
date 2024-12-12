<script lang="ts">
	import type { PageData } from '../$types';

	export let data: PageData;
</script>

{#if data.verified}
	<h1>Email verified</h1>
	<p>Your email has been verified. You can now log in.</p>
{:else}
	<h1>Email verification failed</h1>
	<p>Your email could not be verified. Please try again.</p>
{/if}
