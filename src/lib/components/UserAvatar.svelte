<script lang="ts">
  export let user: any;
  let firstLetter = user.first_name.charAt(0);
</script>

<div class="avatar placeholder">
  <div class="bg-neutral text-neutral-content rounded-full w-10 ml-4">
    <span class="text-2xl">{firstLetter}</span>
  </div>
</div>
