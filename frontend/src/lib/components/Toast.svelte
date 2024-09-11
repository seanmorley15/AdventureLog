<script lang="ts">
	import { toasts } from '$lib/toasts';

	let toastList: any[] = [];

	toasts.subscribe((value) => {
		toastList = value;
		console.log(toastList);
	});
</script>

<div class="toast toast-top mt-14 toast-end z-50 min-w-20">
	{#each toastList as { type, message, id, duration }}
		{#if type == 'success'}
			<div class="alert alert-success">
				<span>{message}</span>
			</div>
		{/if}
		{#if type == 'error'}
			<div class="alert alert-error">
				<span>{message}</span>
			</div>
		{/if}
		{#if type == 'info'}
			<div class="alert alert-info">
				<span>{message}</span>
			</div>
		{/if}
		{#if type == 'warning'}
			<div class="alert alert-warning">
				<span>{message}</span>
			</div>
		{/if}
	{/each}
</div>
