<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	import { onMount } from 'svelte';
	let modal: HTMLDialogElement;
	import { t } from 'svelte-i18n';
	import { appVersion, copyrightYear, versionChangelog } from '$lib/config';

	onMount(() => {
		modal = document.getElementById('my_modal_1') as HTMLDialogElement;
		if (modal) {
			modal.showModal();
		}
	});

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			dispatch('close');
		}
	}
</script>

<dialog id="my_modal_1" class="modal">
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
	<div class="modal-box" role="dialog" on:keydown={handleKeydown} tabindex="0">
		<h3 class="font-bold text-lg">
			{$t('about.about')} AdventureLog<span class=" inline-block"
				><img src="/favicon.png" alt="Map Logo" class="w-10 -mb-3 ml-2" /></span
			>
		</h3>
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
		<p class="py-1">{$t('about.license')}</p>
		<p class="py-1">
			<a
				href="https://github.com/seanmorley15/AdventureLog"
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary-500 underline">{$t('about.source_code')}</a
			>
		</p>
		<p class="py-1">{$t('about.message')}</p>
		<div class="divider"></div>
		<h3 class="font-bold text-md">{$t('about.oss_attributions')}</h3>
		<p class="py-1 mb-4">
			{$t('about.nominatim_1')}
			<a
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary-500 underline"
				href="https://operations.osmfoundation.org/policies/nominatim/">OpenStreepMap</a
			>. {$t('about.nominatim_2')}
			<br />
			{$t('about.other_attributions')}
		</p>

		<button class="btn btn-primary" on:click={close}>{$t('about.close')}</button>
	</div>
</dialog>
