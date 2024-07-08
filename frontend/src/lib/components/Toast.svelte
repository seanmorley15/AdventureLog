<script lang="ts">
	import { toasts } from '$lib/toasts';

	let toastList: any[] = [];

	toasts.subscribe((value) => {
		toastList = value;
		console.log(toastList);
	});
</script>

<div class="toast toast-top toast-end z-50 min-w-20">
	{#each toastList as { type, message, id, duration }}
		<div class="alert alert-{type}">
			<span>{message}</span>
		</div>
	{/each}
</div>
