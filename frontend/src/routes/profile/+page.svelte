<script lang="ts">
	export let data;
</script>

<!--
  // v0 by Vercel.
  // https://v0.dev/t/EtPnDdQYcbn
  -->

<!--
  // v0 by Vercel.
  // https://v0.dev/t/DYwTru570WN
  -->

{#if data.user.profile_pic}
	<div class="avatar flex items-center justify-center">
		<div class="w-24 rounded">
			<!-- svelte-ignore a11y-missing-attribute -->
			<img src={data.user.profile_pic} class="w-24 rounded-full" />
		</div>
	</div>
{/if}

{#if data.user && data.user.first_name && data.user.last_name}
	<h1 class="text-center text-4xl font-bold">
		{data.user.first_name}, {data.user.last_name}
	</h1>
{/if}
<p class="text-center text-lg mt-2">{data.user.username}</p>

{#if data.user && data.user.date_joined}
	<p class="ml-1 text-lg text-center mt-4">Member Since</p>
	<div class="flex items-center justify-center text-center">
		<iconify-icon icon="mdi:calendar" class="text-2xl"></iconify-icon>
		<p class="ml-1 text-xl">{new Date(data.user.date_joined).toLocaleDateString()}</p>
	</div>
{/if}
