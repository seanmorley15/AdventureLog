<script lang="ts">
	import { marked } from 'marked'; // Import the markdown parser
	import { t } from 'svelte-i18n';
	import DOMPurify from 'dompurify'; // Import DOMPurify to sanitize HTML

	interface Props {
		text?: string | null | undefined; // Markdown text
		editor_height?: string; // Editor height
	}

	let { text = $bindable(''), editor_height = 'h-64' }: Props = $props();
	let is_preview: boolean = $state(false); // Toggle between Edit and Preview mode

	// Function to parse markdown to HTML
	const renderMarkdown = (markdown: string) => {
		return marked(markdown) as string;
	};

	// References for scroll syncing
	let editorRef: HTMLTextAreaElement | null = $state(null);
	let previewRef: HTMLElement | null = $state(null);

	// Sync scrolling between editor and preview
	const syncScroll = () => {
		if (editorRef && previewRef) {
			const ratio = editorRef.scrollTop / (editorRef.scrollHeight - editorRef.clientHeight);
			previewRef.scrollTop = ratio * (previewRef.scrollHeight - previewRef.clientHeight);
		}
	};
</script>

<div class="join justify-start mt-2">
	<button
		type="button"
		class={['join-item btn btn-sm', !is_preview ? 'btn-neutral' : 'btn-ghost']}
		onclick={() => (is_preview = false)}
	>
		{$t('transportation.edit')}
	</button>
	<button
		type="button"
		class={['join-item btn btn-sm', is_preview ? 'btn-neutral' : 'btn-ghost']}
		onclick={() => (is_preview = true)}
	>
		{$t('adventures.preview')}
	</button>
</div>

<div class="flex flex-col mt-4 gap-4">
	<!-- Markdown Editor -->
	{#if !is_preview}
		<textarea
			class="textarea {editor_height} w-full"
			bind:this={editorRef}
			bind:value={text}
			placeholder={$t('adventures.md_instructions')}
			onscroll={syncScroll}
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
