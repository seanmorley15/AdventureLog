<script lang="ts">
	interface ShareMeta {
		title: string;
		description: string;
		imageUrl: string;
		pageUrl: string;
	}

	interface Props {
		name?: string | null;
		shareMeta?: ShareMeta | null;
	}

	let { name = null, shareMeta = null }: Props = $props();
</script>

<svelte:head>
	<title>{name || 'Adventure'}</title>
	{#if shareMeta}
		<meta name="description" content={shareMeta.description} />
		<meta property="og:title" content={shareMeta.title} />
		<meta property="og:description" content={shareMeta.description} />
		<meta property="og:image" content={shareMeta.imageUrl} />
		<meta property="og:url" content={shareMeta.pageUrl} />
		<meta property="og:type" content="website" />
		<meta name="twitter:card" content="summary_large_image" />
		<meta name="twitter:title" content={shareMeta.title} />
		<meta name="twitter:description" content={shareMeta.description} />
		<meta name="twitter:image" content={shareMeta.imageUrl} />
	{:else}
		<meta name="description" content="Explore the world and add countries to your visited list!" />
	{/if}
</svelte:head>
