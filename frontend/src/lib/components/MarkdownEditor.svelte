<script lang="ts">
	import { marked } from 'marked'; // Import the markdown parser
	import { t } from 'svelte-i18n';
	import DOMPurify from 'dompurify'; // Import DOMPurify to sanitize HTML

	export let text: string | null | undefined = ''; // Markdown text
	export let editor_height: string = 'h-64'; // Editor height
	let is_preview: boolean = false; // Toggle between Edit and Preview mode

	// Function to parse markdown to HTML
	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	// References for scroll syncing
	let editorRef: HTMLTextAreaElement | null = null;
	let previewRef: HTMLElement | null = null;

	// Sync scrolling between editor and preview
	const syncScroll = () => {
		if (editorRef && previewRef) {
			const ratio = editorRef.scrollTop / (editorRef.scrollHeight - editorRef.clientHeight);
			previewRef.scrollTop = ratio * (previewRef.scrollHeight - previewRef.clientHeight);
		}
	};
</script>

<div class="join justify-center mt-2">
	<button
		type="button"
		class="join-item btn btn-sm btn-outline"
		on:click={() => (is_preview = false)}
		class:btn-active={!is_preview}
	>
		{$t('transportation.edit')}
	</button>
	<button
		type="button"
		class="join-item btn btn-sm btn-outline"
		on:click={() => (is_preview = true)}
		class:btn-active={is_preview}
	>
		{$t('adventures.preview')}
	</button>
</div>

<div class="flex flex-col mt-4 gap-4">
	<!-- Markdown Editor -->
	{#if !is_preview}
		<textarea
			class="textarea textarea-bordered resize-none {editor_height}  w-full"
			bind:this={editorRef}
			bind:value={text}
			placeholder={$t('adventures.md_instructions')}
			on:scroll={syncScroll}
		></textarea>
	{/if}

	<!-- Markdown Preview -->
	{#if is_preview}
		<article
			class="prose overflow-auto h-96 max-w-full w-full p-4 border border-base-300 rounded-lg bg-base-300"
			bind:this={previewRef}
		>
			{@html DOMPurify.sanitize(renderMarkdown(text || ''))}
		</article>
	{/if}
</div>

<style>
	/* Optional: Smooth scrolling for synced scroll effect */
	textarea,
	article {
		scroll-behavior: smooth;
	}

	/* Force both editor and preview to have equal width */
	textarea,
	article {
		width: 100%;
	}
</style>
