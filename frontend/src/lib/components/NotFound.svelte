<script lang="ts">
	import Lost from '$lib/assets/undraw_lost.svg';
	export let error: string | undefined;
</script>

<div
	class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8 -mt-20"
>
	<div class="mx-auto max-w-md text-center">
		<div class="flex items-center justify-center">
			<img src={Lost} alt="Lost" class="w-1/2" />
		</div>
		<h1 class="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
			No adventures found
		</h1>
		{#if !error}
			<p class="mt-4 text-muted-foreground">
				There are no adventures to display. Add some using the plus button at the bottom right or
				try changing filters!
			</p>
		{:else}
			<p class="text-error mt-2">{error}</p>
		{/if}
	</div>
</div>
