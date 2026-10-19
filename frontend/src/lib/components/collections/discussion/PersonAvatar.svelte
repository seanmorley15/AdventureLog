<script lang="ts" module>
	export type PersonSummary = {
		name?: string;
		username: string | null;
		profile_pic?: string | null;
		can_view_profile?: boolean;
		is_guest?: boolean;
	};
</script>

<script lang="ts">
	import UserAvatar from '$lib/components/UserAvatar.svelte';
	import LinkVariant from '~icons/mdi/link-variant';

	interface Props {
		person: PersonSummary;
		size?: 'xs' | 'sm' | 'md';
		/** Turn off the link, e.g. inside something that is already a link. */
		linked?: boolean;
	}

	let { person, size = 'md', linked = true }: Props = $props();

	const SIZES = { xs: 'h-6 w-6', sm: 'h-7 w-7', md: 'h-9 w-9' } as const;
	let href = $derived(
		linked && person.username && person.can_view_profile ? `/profile/${person.username}` : null
	);
	let label = $derived(person.name || person.username || '');
</script>

{#snippet circle()}
	<!-- A fixed-size circle: UserAvatar fills its parent. -->
	<span
		class="flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-base-300 {SIZES[
			size
		]}"
	>
		{#if person.username}
			<UserAvatar
				user={{
					username: person.username,
					first_name: person.name ?? '',
					last_name: '',
					profile_pic: person.profile_pic ?? null
				}}
				alt={label}
				className="h-full w-full rounded-full"
				textClass="text-xs"
			/>
		{:else if person.is_guest}
			<LinkVariant class="h-4 w-4 opacity-70" aria-hidden="true" />
		{:else}
			<span class="text-xs font-semibold" aria-hidden="true">
				{(label || '?').slice(0, 1).toUpperCase()}
			</span>
		{/if}
	</span>
{/snippet}

{#if href}
	<a {href} class="shrink-0 rounded-full" aria-label={label} title={label}>
		{@render circle()}
	</a>
{:else}
	{@render circle()}
{/if}
