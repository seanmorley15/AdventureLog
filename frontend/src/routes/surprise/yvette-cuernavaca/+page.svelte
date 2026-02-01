<script lang="ts">
	import { page } from '$app/stores';
	import SurpriseRevealFlow from '$lib/surprise/SurpriseRevealFlow.svelte';

	// Get personalization from URL parameters (e.g., ?for=yvette or ?invite=yvette2026)
	$: recipientName = $page.url.searchParams.get('for') || $page.url.searchParams.get('invite') || 'Yvette';
	$: pageTitle = `${recipientName} — Sorpresa en Cuernavaca`;
</script>

<svelte:head>
	<title>{pageTitle}</title>
	<meta name="description" content="A beautiful treasure hunt experience in Cuernavaca - discover amazing locations!" />
	<meta property="og:title" content={pageTitle} />
	<meta property="og:description" content="Join us on a magical journey through Cuernavaca!" />
</svelte:head>

<SurpriseRevealFlow />
