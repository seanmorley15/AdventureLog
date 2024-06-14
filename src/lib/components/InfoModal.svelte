<script lang="ts">
  import { createEventDispatcher } from "svelte";
  import type { Adventure } from "$lib/utils/types";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;
  import { appVersion, copyrightYear, versionChangelog } from "$lib/config";

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">About AdventureLog</h3>
    <p class="py-1">
      AdventureLog <a
        target="_blank"
        rel="noopener noreferrer"
        class="text-primary-500 underline"
        href={versionChangelog}>{appVersion}</a
      >
    </p>
    <p class="py-1">
      © {copyrightYear}
      <a
        href="https://github.com/seanmorley15"
        target="_blank"
        rel="noopener noreferrer"
        class="text-primary-500 underline">Sean Morley</a
      >
    </p>
    <p class="py-1">Liscensed under the GPL-3.0 License.</p>
    <p class="py-1">
      <a
        href="https://github.com/seanmorley15/AdventureLog"
        target="_blank"
        rel="noopener noreferrer"
        class="text-primary-500 underline">Source Code</a
      >
    </p>
    <p class="py-1">Made with ❤️ in the United States.</p>
    <div
      class="modal-action items-center"
      style="display: flex; flex-direction: column; align-items: center; width: 100%;"
    ></div>
    <button class="btn btn-primary" on:click={close}>Close</button>
  </div>
</dialog>
