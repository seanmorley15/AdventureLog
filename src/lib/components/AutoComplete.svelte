<script lang="ts">
  export let items: String[] = [];
  export let selectedItem;

  $: inputVal = "";

  function onItemClicked(item: String) {
    selectedItem = item;
    inputVal = "";
  }

  $: filteredItems = items.filter(function (item) {
    return item.toLowerCase().includes(inputVal.toLowerCase());
  });
</script>

<div class="dropdown">
  <input
    class="input input-bordered"
    placeholder="Existing Activity Types"
    bind:value={inputVal}
  />
  <ul
    tabindex="0"
    class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52 max-h-80 flex-nowrap overflow-auto"
  >
    {#each filteredItems as item}
      <li>
        <a on:click|preventDefault={() => onItemClicked(item)}>{item}</a>
      </li>
    {/each}
  </ul>
</div>
