<script lang="ts">
	import { t } from 'svelte-i18n';
	import CashMultiple from '~icons/mdi/cash-multiple';
	import OpenInNew from '~icons/mdi/open-in-new';

	export let title: string = $t('adventures.basic_information') || 'Basic Information';
	export let icon: string = 'ℹ️';
	export let price: string | null = null;
	export let link: string | null = null;
	export let tags: string[] = [];
</script>

<div class="card bg-base-200 shadow-xl">
	<div class="card-body">
		<h3 class="card-title text-lg mb-4">{icon} {title}</h3>
		<div class="space-y-3">
			<!-- Price -->
			{#if price}
				<div class="flex items-start gap-3">
					<CashMultiple class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
					<div>
						<div class="text-sm opacity-70 mb-0.5">{$t('adventures.price')}</div>
						<div class="text-base font-semibold">{price}</div>
					</div>
				</div>
			{/if}

			<!-- Tags -->
			{#if tags && tags.length > 0}
				<div>
					<div class="text-sm opacity-70 mb-1">{$t('adventures.tags')}</div>
					<div class="flex flex-wrap gap-1">
						{#each tags as tag}
							<span class="badge badge-sm badge-outline">{tag}</span>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Link -->
			{#if link}
				<div class="flex items-start gap-3">
					<OpenInNew class="w-5 h-5 text-primary mt-1 flex-shrink-0" />
					<div class="flex-1">
						<div class="text-sm opacity-70 mb-1">{$t('adventures.link')}</div>
						<a
							href={link}
							class="link link-primary text-sm break-all"
							target="_blank"
							rel="noopener noreferrer"
						>
							{link.length > 30 ? `${link.slice(0, 30)}...` : link}
						</a>
					</div>
				</div>
			{/if}

			<!-- Additional content via slot -->
			<slot />
		</div>
	</div>
</div>
