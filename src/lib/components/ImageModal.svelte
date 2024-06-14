<script lang="ts">
  import { getImage } from "$lib";
  import { createEventDispatcher } from "svelte";
  import { onMount } from "svelte";
  let modal: HTMLDialogElement;
  export let name: string;

  let viewType: string = "upload";

  let imageUrl: string = "";

  let imageFile: File | null = null;

  let key: string;

  const dispatch = createEventDispatcher();

  onMount(() => {
    modal = document.getElementById("my_modal_1") as HTMLDialogElement;
    if (modal) {
      modal.showModal();
    }
  });

  function close() {
    dispatch("close");
  }

  async function submit() {
    try {
      let key: string;
      if (viewType === "url") {
        // Get image from URL
        const response = await fetch(imageUrl);
        const blob = await response.blob();

        const uploadResponse = await fetch("/api/upload", {
          method: "POST",
          body: blob,
          headers: {
            bucket: "adventures",
            type: "adventure",
            "Content-Type": blob.type,
          },
        });

        const result = await uploadResponse.json();
        key = result.key;
        console.log(result);
      } else if (imageFile) {
        // Get the image from the file input

        const uploadResponse = await fetch("/api/upload", {
          method: "POST",
          body: imageFile,
          headers: {
            bucket: "adventures",
            type: "adventure",
            "Content-Type": imageFile.type,
          },
        });

        const result = await uploadResponse.json();
        key = result.key;
        console.log(result);
      } else {
        console.error("No file selected for upload");
        return;
      }

      dispatch("submit", key);
      close();
    } catch (error) {
      console.error("Error during submission", error);
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close();
    }
  }

  function setViewType(type: string) {
    viewType = type;
  }

  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      imageFile = target.files[0];
    }
  }

  async function searchImage() {
    try {
      imageUrl = await getImage(name);
    } catch (error) {
      console.error(error);
      // Handle the error
    }
  }
</script>

<dialog id="my_modal_1" class="modal">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <!-- svelte-ignore a11y-no-noninteractive-tabindex -->
  <div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
    <h3 class="font-bold text-lg">Image Upload</h3>
    <div class="join items-center justify-center flex mb-8">
      <input
        class="join-item btn btn-neutral"
        type="radio"
        name="upload"
        checked
        aria-label="Upload File"
        on:click={() => setViewType("upload")}
      />
      <input
        class="join-item btn btn-neutral"
        type="radio"
        name="upload"
        aria-label="Url"
        on:click={() => setViewType("url")}
      />
    </div>
    {#if viewType == "url"}
      <button class="btn btn-secondary" on:click={searchImage}
        >Search for Image</button
      >
      <form method="dialog" style="width: 100%;" class="mb-4">
        <div>
          <label for="rating">Image URL</label>
          <input
            type="text"
            id="imageUrl"
            bind:value={imageUrl}
            placeholder="Enter the URL of the image"
          />
        </div>
      </form>
    {/if}
    {#if viewType == "upload"}
      <form method="dialog" style="width: 100%;" class="mb-4">
        <div>
          <label for="rating">Image Upload</label>
          <input
            type="file"
            id="imageFile"
            on:change={handleFileChange}
            placeholder="Upload an image file"
          />
        </div>
      </form>
    {/if}

    <button class="btn btn-neutral" on:click={close}>Close</button>
    <button class="btn btn-primary" on:click={submit}>Submit</button>
  </div>
</dialog>