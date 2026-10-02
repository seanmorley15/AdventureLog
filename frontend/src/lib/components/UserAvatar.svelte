<script lang="ts">
	import { getAvatarGradient, getAvatarSeed, getUserInitials, type AvatarUser } from '$lib/avatar';

	interface Props {
		user?: AvatarUser & { profile_pic?: string | null };
		profilePic?: string | null | undefined;
		alt?: string;
		className?: string;
		imgClass?: string;
		textClass?: string;
	}

	let {
		user = {},
		profilePic = undefined,
		alt = '',
		className = 'w-10 h-10 rounded-full',
		imgClass = 'w-full h-full object-cover',
		textClass = 'text-sm'
	}: Props = $props();

	let pic = $derived(profilePic ?? user.profile_pic ?? null);
	let initials = $derived(getUserInitials(user));
	let gradient = $derived(getAvatarGradient(getAvatarSeed(user)));
</script>

{#if pic}
	<img src={pic} {alt} class="{className} {imgClass}" />
{:else}
	<div
		class="flex items-center justify-center font-semibold select-none leading-none aspect-square {textClass} {className}"
		style="background: {gradient}; color: #fff;"
		role="img"
		aria-label={alt || initials}
	>
		{initials}
	</div>
{/if}
