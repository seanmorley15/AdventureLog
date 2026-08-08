<script lang="ts">
	export let padding: string = 'p-8';
	export let className: string = '';
	export let id: string | undefined = undefined;
</script>

<div {id} class="bg-base-100 rounded-2xl shadow-xl {padding} {className}">
	<slot />
</div>
