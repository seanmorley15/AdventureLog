<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Lost from '$lib/assets/undraw_lost.svg';
</script>

<h1>{$page.status}: {$page.error?.message}</h1>

{#if $page.status === 404}
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8"
	>
		<div class="mx-auto max-w-md text-center">
			<img src={Lost} alt="Lost in the forest" />
			<h1 class="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
				Oops, looks like you've wandered off the beaten path.
			</h1>
			<p class="mt-4 text-muted-foreground">
				We couldn't find the page you were looking for. Don't worry, we can help you find your way
				back.ry, we can
			</p>
			<div class="mt-6 flex flex-col items-center gap-4 sm:flex-row">
				<button class="btn btn-neutral" on:click={() => goto('/')}>Go to Homepage</button>
			</div>
		</div>
	</div>
{/if}
