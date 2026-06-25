<script lang="ts">
	import { getAvatarGradient, getAvatarSeed, getUserInitials, type AvatarUser } from '$lib/avatar';

	export let user: AvatarUser & { profile_pic?: string | null } = {};
	export let profilePic: string | null | undefined = undefined;
	export let alt = '';
	export let className = 'w-10 h-10 rounded-full';
	export let imgClass = 'w-full h-full object-cover';
	export let textClass = 'text-sm';

	$: pic = profilePic ?? user.profile_pic ?? null;
	$: initials = getUserInitials(user);
	$: gradient = getAvatarGradient(getAvatarSeed(user));
</script>

{#if pic}
	<img src={pic} {alt} class="{className} {imgClass}" />
{:else}
	<div
		class="flex items-center justify-center font-semibold select-none {textClass} {className}"
		style="background: {gradient}; color: #fff;"
		role="img"
		aria-label={alt || initials}
	>
		{initials}
	</div>
{/if}
