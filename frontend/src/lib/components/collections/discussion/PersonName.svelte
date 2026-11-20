<script lang="ts">
	import type { PersonSummary } from './PersonAvatar.svelte';

	interface Props {
		person: PersonSummary;
		fallback?: string;
	}

	let { person, fallback = '' }: Props = $props();

	let name = $derived(person.name || person.username || fallback);
	let href = $derived(
		person.username && person.can_view_profile ? `/profile/${person.username}` : null
	);
</script>

{#if href}
	<a {href} class="font-semibold hover:underline">{name}</a>
{:else}
	<span class="font-semibold">{name}</span>
{/if}
