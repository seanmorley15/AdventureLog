<script lang="ts">
  import { createEventDispatcher } from "svelte";
  const dispatch = createEventDispatcher();
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;

  export let title: string;
  export let message: string;
  export let isWarning: boolean;

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  function confirm() {
    dispatch("confirm");
    close();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }
</script>

<dialog id="my_modal_1" class="modal {isWarning ? 'bg-warning' : ''}">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">{title}</h3>
    <p class="py-1 mb-2">{message}</p>
    <button class="btn btn-sucess mr-2" on:click={confirm}>Confirm</button>
    <button class="btn btn-neutral" on:click={close}>Close</button>
  </div>
</dialog>
