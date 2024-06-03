<script lang="ts">
  export let items: String[] = [];
  export let displayValue: String = "";
  export let selectedItem;

  let newAdd: String[] = [];

  $: inputVal = "";

  function onItemClicked(item: String) {
    // items.push(item);
    console.log(newAdd);
    if (newAdd.includes(item)) {
      return;
    } else {
      newAdd.push(item);
      selectedItem = item;
    }
  }

  $: filteredItems = items.filter(function (item) {
    return item.toLowerCase().includes(inputVal.toLowerCase());
  });
</script>

<div class="dropdown">
  <input
    class="input input-bordered"
    placeholder=""
    bind:value={displayValue}
  />
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <ul
    tabindex="0"
    class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-52 max-h-80 flex-nowrap overflow-auto"
  >
    {#each filteredItems as item}
      <!-- svelte-ignore a11y-click-events-have-key-events -->
      <!-- svelte-ignore a11y-no-static-element-interactions -->
      <!-- svelte-ignore a11y-missing-attribute -->
      <li>
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-missing-attribute -->
        <a on:click|preventDefault={() => onItemClicked(item)}>{item}</a>
      </li>
    {/each}
  </ul>
</div>
