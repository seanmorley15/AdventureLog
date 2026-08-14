<script lang="ts">
	import { t } from 'svelte-i18n';
	import Check from '~icons/mdi/check';
	import Close from '~icons/mdi/close';
	import {
		checkPasswordRequirement,
		getPasswordRequirements,
		type PasswordPolicy,
		type RequirementStatus
	} from '$lib/password-policy';

	interface Props {
		policy: PasswordPolicy;
		password?: string;
	}

	let { policy, password = '' }: Props = $props();

	let requirements = $derived(getPasswordRequirements(policy));
	let lengthStatus = $derived(checkPasswordRequirement('min_length', password, policy));
	let otherRequirements = $derived(requirements.filter((requirement) => requirement.id !== 'min_length'));

	function statusClass(status: RequirementStatus): string {
		if (status === true) return 'text-success';
		if (status === false) return 'text-error';
		return 'text-base-content/45';
	}
</script>

<div class="rounded-lg border border-base-300/80 bg-base-200/40 px-3 py-2 space-y-1">
	<p class="text-xs font-medium text-base-content/60 mb-1">
		{$t('auth.password_requirements_title')}
	</p>

	<div class="flex items-start gap-2 text-xs leading-snug {statusClass(lengthStatus)}">
		<span class="mt-0.5 shrink-0">
			{#if lengthStatus === true}
				<Check class="w-3.5 h-3.5" aria-hidden="true" />
			{:else if lengthStatus === false}
				<Close class="w-3.5 h-3.5" aria-hidden="true" />
			{:else}
				<span class="block w-3.5 h-3.5 rounded-full border border-current/40"></span>
			{/if}
		</span>
		<span>{$t('auth.password_requirement_min_length', { values: { min: policy.min_length } })}</span
		>
	</div>

	{#each otherRequirements as requirement (requirement.id)}
		<div class="flex items-start gap-2 text-xs leading-snug text-base-content/60">
			<span class="mt-2 shrink-0 block w-1 h-1 rounded-full bg-current"></span>
			<span>{$t(requirement.labelKey, { values: { min: policy.min_length } })}</span>
		</div>
	{/each}
</div>
