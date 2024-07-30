<script>
	import Navbar from '$lib/components/Navbar.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import 'tailwindcss/tailwind.css';
	export let data;

	const enableAnalytics = process.env['ENABLE_ANALYTICS'] || 'false';
	const unamiKey = process.env['UNAMI_KEY'] || '';
</script>

<svelte:head>
	{#if enableAnalytics === 'true' && unamiKey}
		<script defer src="https://cloud.umami.is/script.js" data-website-id={unamiKey}></script>
	{/if}
</svelte:head>

<Navbar {data} />
<Toast />

<slot></slot>
