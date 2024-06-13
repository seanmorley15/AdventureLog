<script lang="ts">
  import type { PageData } from "./$types";

  export let data: PageData;
</script>

<!--
// v0 by Vercel.
// https://v0.dev/t/EtPnDdQYcbn
-->

<!--
// v0 by Vercel.
// https://v0.dev/t/DYwTru570WN
-->

{#if data.user.icon}
  <div class="avatar flex items-center justify-center">
    <div class="w-24 rounded">
      <img src={data.user.icon} class="w-24 rounded-full" />
    </div>
  </div>
{/if}

<h1 class="text-center text-4xl font-bold">
  {data.user.first_name}, {data.user.last_name}
</h1>
<p class="text-center text-lg mt-2">{data.user.username}</p>

<p class="ml-1 text-lg text-center mt-4">Member Since</p>
<div class="flex items-center justify-center text-center">
  <iconify-icon icon="mdi:calendar" class="text-2xl"></iconify-icon>
  <p class="ml-1 text-xl">{data.user.signup_date.toDateString()}</p>
</div>
