<script lang="ts" module>
	export type ShareSheetTab = 'people' | 'links' | 'story';
</script>

<script lang="ts">
	import { apiErrorMessage } from '#lib/api/index.js';
	import { onDestroy, onMount, untrack } from 'svelte';
	import { t } from 'svelte-i18n';
	import type {
		Collection,
		CollectionSharing,
		CollectionSharingPerson,
		CollectionVisibility,
		CommentAccess,
		StoryGroup,
		User
	} from '#lib/types.js';
	import { addToast } from '#lib/toasts.js';
	import { STORY_GROUP_NAMES } from '#lib/collections/story.js';
	import { copyToClipboard } from '#lib/index.js';
	import UserAvatar from '#lib/components/UserAvatar.svelte';
	import ShareVariant from '~icons/mdi/share-variant';
	import Close from '~icons/mdi/close';
	import ContentCopy from '~icons/mdi/content-copy';
	import EyeOutline from '~icons/mdi/eye-outline';
	import LinkVariant from '~icons/mdi/link-variant';
	import AccountPlus from '~icons/mdi/account-plus';
	import LockOutline from '~icons/mdi/lock-outline';
	import Earth from '~icons/mdi/earth';
	import OpenInNew from '~icons/mdi/open-in-new';
	import CheckCircle from '~icons/mdi/check-circle';
	import InformationOutline from '~icons/mdi/information-outline';
	import AccountMultiple from '~icons/mdi/account-multiple-outline';
	import TrashCanOutline from '~icons/mdi/trash-can-outline';
	import Plus from '~icons/mdi/plus';
	import Check from '~icons/mdi/check';
	import CommentMultiple from '~icons/mdi/comment-multiple-outline';
	import BookOpenPageVariant from '~icons/mdi/book-open-page-variant-outline';

	/** Works with the full collection page payload and with list cards. */
	type ShareTarget = Pick<
		Collection,
		'id' | 'name' | 'shared_with' | 'collaborators' | 'is_public'
	> & {
		visibility?: CollectionVisibility;
		story_groups?: Collection['story_groups'];
		comment_access?: CommentAccess;
	};

	interface Props {
		collection: ShareTarget;
		onClose: () => void;
		/** Opens on this tab, e.g. Story from a Publish button. */
		initialTab?: ShareSheetTab;
	}

	let { collection = $bindable(), onClose, initialTab = 'people' }: Props = $props();

	const STORY_GROUPS = STORY_GROUP_NAMES;
	// The story switches, grouped by what a reader would see.
	const GROUP_SECTIONS: { title: string; groups: StoryGroup[] }[] = [
		{ title: 'share.groups_places', groups: ['place_details', 'coordinates'] },
		{ title: 'share.groups_bookings', groups: ['costs', 'reservations', 'lodging_address'] },
		{ title: 'share.groups_notes', groups: ['note_text', 'checklist_text', 'attachments', 'gpx'] }
	];

	// Opens on the requested tab; switching tabs afterwards is the reader's choice.
	let tab = $state<ShareSheetTab>(untrack(() => initialTab));
	let showNewLink = $state(false);

	type Candidate = Pick<User, 'uuid' | 'username' | 'first_name' | 'last_name'> & {
		profile_pic?: string | null;
	};

	let sharing = $state<CollectionSharing | null>(null);
	// Invitee search runs on the server and returns a capped list, so the sheet
	// never loads every user on a large server.
	const SEARCH_MIN_LENGTH = 2;
	const SEARCH_LIMIT = 20;
	let searchQuery = $state('');
	let searchResults = $state<Candidate[]>([]);
	let searching = $state(false);
	let invitee = $state<Candidate | null>(null);
	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	let searchController: AbortController | null = null;
	let loading = $state(true);
	let busy = $state(false);
	let inviteRole = $state<'editor' | 'viewer'>('editor');
	let guestRole = $state<'editor' | 'viewer'>('viewer');
	let guestExpiryDays = $state(7);
	let guestLabel = $state('');

	let activeLinks = $derived((sharing?.guest_links ?? []).filter((link) => link.is_active));
	let inactiveLinkCount = $derived((sharing?.guest_links ?? []).length - activeLinks.length);
	let shownGroupCount = $derived(
		STORY_GROUPS.filter((group) => sharing?.story_groups?.[group]).length
	);
	let visibility = $derived<CollectionVisibility>(sharing?.visibility ?? 'private');
	const VISIBILITY_CHOICES = [
		{ value: 'private', icon: LockOutline },
		{ value: 'unlisted', icon: LinkVariant },
		{ value: 'public', icon: Earth }
	] as const;

	// Private is always available. With public links turned off on the server, the
	// current choice stays selectable so an existing story can still be made private.
	function isAvailable(option: CollectionVisibility) {
		return option === 'private' || option === visibility || !!sharing?.allow_public_links;
	}
	let storyUrl = $derived.by(() => {
		if (typeof window === 'undefined' || !sharing || visibility === 'private') return '';
		const base = `${window.location.origin}/collections/${collection.id}`;
		return visibility === 'unlisted'
			? `${base}?s=${encodeURIComponent(sharing.share_secret)}`
			: base;
	});

	function displayName(person: {
		first_name?: string | null;
		last_name?: string | null;
		username: string;
	}) {
		return [person.first_name, person.last_name].filter(Boolean).join(' ') || person.username;
	}

	async function request(url: string, method: string, body?: unknown) {
		busy = true;
		try {
			const res = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: body === undefined ? undefined : JSON.stringify(body)
			});
			// 204 (removed, revoked) has no body: an empty object still means success.
			const data = await res.json().catch(() => ({}));
			if (!res.ok) {
				addToast('error', apiErrorMessage(data, $t('share.update_failed')));
				return null;
			}
			return data;
		} finally {
			busy = false;
		}
	}

	async function loadSharing() {
		const data = await request(`/api/collections/${collection.id}/sharing/`, 'GET');
		if (data) sharing = data as CollectionSharing;
	}

	function onSearchInput(value: string) {
		searchQuery = value;
		invitee = null;
		clearTimeout(searchTimer);
		searchController?.abort();
		if (value.trim().length < SEARCH_MIN_LENGTH) {
			searchResults = [];
			searching = false;
			return;
		}
		searching = true;
		searchTimer = setTimeout(() => void runSearch(value.trim()), 250);
	}

	async function runSearch(query: string) {
		const controller = new AbortController();
		searchController = controller;
		try {
			const params = new URLSearchParams({ q: query, limit: String(SEARCH_LIMIT) });
			const res = await fetch(`/api/collections/${collection.id}/shareable-users/?${params}`, {
				signal: controller.signal
			});
			if (res.ok && searchController === controller) searchResults = await res.json();
		} catch (error) {
			if ((error as Error).name !== 'AbortError') searchResults = [];
		} finally {
			if (searchController === controller) searching = false;
		}
	}

	function chooseInvitee(user: Candidate) {
		invitee = user;
		searchQuery = displayName(user);
		searchResults = [];
	}

	function resetSearch() {
		clearTimeout(searchTimer);
		searchController?.abort();
		searchQuery = '';
		searchResults = [];
		searching = false;
		invitee = null;
	}

	function syncCollaborators() {
		if (!sharing) return;
		collection.shared_with = sharing.members.map((member) => member.uuid);
		collection.collaborators = (collection.collaborators ?? [])
			.filter((person) => person.is_owner || collection.shared_with?.includes(person.uuid))
			.map((person) => {
				const member = sharing?.members.find((m) => m.uuid === person.uuid);
				return member ? { ...person, role: member.role } : person;
			});
	}

	async function invite(event: SubmitEvent) {
		event.preventDefault();
		if (!invitee) return;
		const data = await request(`/api/collections/${collection.id}/invites/`, 'POST', {
			user: invitee.uuid,
			role: inviteRole
		});
		if (data) {
			addToast('success', $t('share.invite_sent'));
			resetSearch();
			sharing = data as CollectionSharing;
		}
	}

	async function setRole(person: CollectionSharingPerson, role: 'editor' | 'viewer') {
		const data = await request(
			`/api/collections/${collection.id}/members/${person.uuid}/`,
			'PATCH',
			{
				role
			}
		);
		if (data) {
			sharing = data as CollectionSharing;
			syncCollaborators();
		}
	}

	async function removeMember(person: CollectionSharingPerson) {
		const data = await request(
			`/api/collections/${collection.id}/members/${person.uuid}/`,
			'DELETE'
		);
		if (data) {
			addToast('success', `${$t('share.unshared')} ${displayName(person)}`);
			await loadSharing();
			syncCollaborators();
		}
	}

	async function revokeInvite(person: CollectionSharingPerson) {
		const data = await request(
			`/api/collections/${collection.id}/invites/${person.uuid}/`,
			'DELETE'
		);
		if (data) {
			addToast('success', $t('share.invite_revoked'));
			await loadSharing();
		}
	}

	async function createGuestLink(event: SubmitEvent) {
		event.preventDefault();
		const body: Record<string, unknown> = { role: guestRole, label: guestLabel.trim() };
		if (guestExpiryDays > 0) {
			body.expires_at = new Date(Date.now() + guestExpiryDays * 86_400_000).toISOString();
		}
		const data = await request(`/api/collections/${collection.id}/guest-links/`, 'POST', body);
		if (data) {
			sharing = data as CollectionSharing;
			guestLabel = '';
			showNewLink = false;
			const created = (sharing.guest_links ?? []).filter((link) => link.is_active).at(-1);
			if (created) await copy(guestUrl(created.token));
		}
	}

	async function revokeGuestLink(id: string) {
		const data = await request(`/api/collections/${collection.id}/guest-links/${id}/`, 'DELETE');
		if (data) await loadSharing();
	}

	function guestUrl(token: string) {
		return `${window.location.origin}/collections/${collection.id}?guest=${encodeURIComponent(token)}`;
	}

	async function copy(text: string) {
		try {
			await copyToClipboard(text);
			addToast('success', $t('adventures.link_copied'));
		} catch {
			addToast('error', $t('adventures.copy_failed'));
		}
	}

	async function setVisibility(next: CollectionVisibility) {
		if (!sharing || next === visibility) return;
		const data = await request(`/api/collections/${collection.id}/`, 'PATCH', { visibility: next });
		if (data) {
			sharing = { ...sharing, visibility: data.visibility };
			collection.visibility = data.visibility;
			collection.is_public = data.is_public;
			addToast('success', $t(`share.visibility_changed_${data.visibility}`));
		}
	}

	const COMMENT_CHOICES: CommentAccess[] = ['off', 'signed_in', 'link_holders'];

	async function setCommentAccess(next: CommentAccess) {
		if (!sharing || next === sharing.comment_access) return;
		const data = await request(`/api/collections/${collection.id}/`, 'PATCH', {
			comment_access: next
		});
		if (data) {
			sharing = { ...sharing, comment_access: data.comment_access };
			collection.comment_access = data.comment_access;
			addToast('success', $t(`share.comments_changed_${data.comment_access}`));
		}
	}

	async function toggleGroup(group: StoryGroup) {
		if (!sharing) return;
		const next = { ...sharing.story_groups, [group]: !sharing.story_groups[group] };
		const data = await request(`/api/collections/${collection.id}/`, 'PATCH', {
			story_groups: next
		});
		if (data) {
			const groups = data.story_groups ?? {};
			sharing = {
				...sharing,
				story_groups: Object.fromEntries(
					STORY_GROUPS.map((name) => [name, Boolean(groups[name])])
				) as CollectionSharing['story_groups']
			};
			collection.story_groups = groups;
		}
	}

	function formatExpiry(value: string | null) {
		if (!value) return $t('share.never_expires');
		return $t('share.expires_on', { values: { date: new Date(value).toLocaleDateString() } });
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}

	onMount(async () => {
		await loadSharing();
		loading = false;
	});

	onDestroy(() => {
		clearTimeout(searchTimer);
		searchController?.abort();
	});
</script>

{#snippet roleSelect(person: CollectionSharingPerson)}
	<select
		class="select select-sm w-28"
		aria-label={$t('share.role_for', { values: { name: displayName(person) } })}
		value={person.role}
		disabled={busy}
		onchange={(e) => setRole(person, e.currentTarget.value as 'editor' | 'viewer')}
	>
		<option value="editor">{$t('share.role_editor')}</option>
		<option value="viewer">{$t('share.role_viewer')}</option>
	</select>
{/snippet}

{#snippet sectionHeading(Icon: typeof ShareVariant, title: string, hint: string = '')}
	<div class="flex items-start gap-3">
		<div class="shrink-0 rounded-lg bg-primary/10 p-2">
			<Icon class="h-5 w-5 text-primary" />
		</div>
		<div class="min-w-0">
			<h2 class="text-lg font-bold text-base-content">{title}</h2>
			{#if hint}
				<p class="field-hint">{hint}</p>
			{/if}
		</div>
	</div>
{/snippet}

<dialog
	class="modal modal-open modal-bottom md:modal-middle backdrop-blur-xs"
	aria-labelledby="share-sheet-title"
	open
>
	<div
		class="modal-box flex max-h-[100dvh] w-full max-w-3xl flex-col overflow-hidden rounded-none border border-base-300 bg-base-100 p-0 shadow-2xl md:max-h-[90dvh] md:w-11/12 md:rounded-2xl"
		role="dialog"
		tabindex="0"
		onkeydown={handleKeydown}
	>
		<!-- Header, as in the other collection modals -->
		<div class="shrink-0 border-b border-base-300 bg-base-100 px-4 py-3 md:px-6 md:py-4">
			<div class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<div class="shrink-0 rounded-xl bg-primary/10 p-2">
						<ShareVariant class="h-8 w-8 text-primary" />
					</div>
					<div class="min-w-0">
						<h1 id="share-sheet-title" class="truncate text-2xl font-bold text-primary md:text-3xl">
							{$t('adventures.share')}
						</h1>
						<p class="truncate text-sm text-base-content/80">{collection.name}</p>
					</div>
				</div>
				<button
					type="button"
					class="btn btn-ghost btn-square shrink-0"
					aria-label={$t('about.close')}
					title={$t('about.close')}
					onclick={onClose}
				>
					<Close class="h-5 w-5" />
				</button>
			</div>
		</div>

		<div class="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4 md:px-6 md:py-5">
			<div role="tablist" class="tabs tabs-box w-full bg-base-200">
				<button
					type="button"
					role="tab"
					aria-selected={tab === 'people'}
					class="tab flex-1 gap-2 {tab === 'people' ? 'tab-active' : ''}"
					onclick={() => (tab = 'people')}
				>
					<AccountMultiple class="h-4 w-4" />
					{$t('share.people')}
					{#if sharing && sharing.members.length + sharing.invites.length > 0}
						<span class="badge badge-sm">{sharing.members.length + sharing.invites.length}</span>
					{/if}
				</button>
				<button
					type="button"
					role="tab"
					aria-selected={tab === 'links'}
					class="tab flex-1 gap-2 {tab === 'links' ? 'tab-active' : ''}"
					onclick={() => (tab = 'links')}
				>
					<LinkVariant class="h-4 w-4" />
					{$t('share.guest_links')}
					{#if activeLinks.length > 0}
						<span class="badge badge-sm">{activeLinks.length}</span>
					{/if}
				</button>
				<button
					type="button"
					role="tab"
					aria-selected={tab === 'story'}
					class="tab flex-1 gap-2 {tab === 'story' ? 'tab-active' : ''}"
					onclick={() => (tab = 'story')}
				>
					<BookOpenPageVariant class="h-4 w-4" />
					{$t('share.story')}
					<span class="badge badge-sm {visibility === 'private' ? 'badge-ghost' : 'badge-success'}">
						{$t(`share.visibility_${visibility}`)}
					</span>
				</button>
			</div>

			{#if loading || !sharing}
				<div class="flex justify-center py-16">
					<span class="loading loading-spinner loading-md"></span>
				</div>
			{:else if tab === 'people'}
				<!-- PEOPLE: invite first, then who already has access -->
				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-4 md:p-6">
						{@render sectionHeading(AccountPlus, $t('share.invite'), $t('share.people_hint'))}
						<form class="space-y-1" onsubmit={invite}>
							<label class="field-label" for="share-invite-search"
								>{$t('share.search_people')}</label
							>
							<div class="flex flex-wrap gap-2">
								<div class="relative min-w-48 flex-1">
									<input
										id="share-invite-search"
										type="search"
										class="input w-full"
										autocomplete="off"
										placeholder={$t('share.search_people')}
										role="combobox"
										aria-expanded={searchResults.length > 0}
										aria-controls="share-invite-results"
										value={searchQuery}
										oninput={(e) => onSearchInput(e.currentTarget.value)}
									/>
									{#if searchResults.length > 0}
										<ul
											id="share-invite-results"
											role="listbox"
											class="menu absolute top-full z-10 mt-1 max-h-64 w-full flex-nowrap overflow-y-auto rounded-box border border-base-300 bg-base-100 p-1 shadow-lg"
										>
											{#each searchResults as user (user.uuid)}
												<li role="option" aria-selected={invitee?.uuid === user.uuid}>
													<button
														type="button"
														class="flex items-center gap-2"
														onclick={() => chooseInvitee(user)}
													>
														<UserAvatar
															{user}
															alt={displayName(user)}
															className="w-6 h-6 rounded-full"
															textClass="text-[10px]"
														/>
														<span class="truncate">{displayName(user)}</span>
														<span class="truncate text-xs text-base-content/60"
															>@{user.username}</span
														>
													</button>
												</li>
											{/each}
										</ul>
									{/if}
								</div>
								<select class="select w-32" aria-label={$t('share.role')} bind:value={inviteRole}>
									<option value="editor">{$t('share.role_editor')}</option>
									<option value="viewer">{$t('share.role_viewer')}</option>
								</select>
								<button type="submit" class="btn btn-primary gap-2" disabled={busy || !invitee}>
									<AccountPlus class="h-5 w-5" />
									{$t('share.send_invite')}
								</button>
							</div>
							<p class="field-hint">
								{#if searching}
									{$t('share.searching')}
								{:else if searchQuery.trim().length >= SEARCH_MIN_LENGTH && !invitee && !searchResults.length}
									{$t('share.no_people_found')}
								{:else}
									{$t(`share.role_${inviteRole}_hint`)}
								{/if}
							</p>
						</form>
					</div>
				</div>

				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-3 p-4 md:p-6">
						{@render sectionHeading(AccountMultiple, $t('share.has_access'))}
						<ul class="divide-y divide-base-300">
							<li class="flex items-center gap-3 py-2.5">
								<UserAvatar
									user={sharing.owner}
									alt={displayName(sharing.owner)}
									className="w-9 h-9 rounded-full"
									textClass="text-xs"
								/>
								<span class="min-w-0 flex-1 truncate font-medium">{displayName(sharing.owner)}</span
								>
								<span class="badge badge-ghost">{$t('share.you')}</span>
							</li>
							{#each sharing.members as person (person.uuid)}
								<li class="flex items-center gap-3 py-2.5">
									<UserAvatar
										user={person}
										alt={displayName(person)}
										className="w-9 h-9 rounded-full"
										textClass="text-xs"
									/>
									<span class="min-w-0 flex-1">
										<span class="block truncate font-medium">{displayName(person)}</span>
										<span class="block truncate text-xs text-base-content/60"
											>@{person.username}</span
										>
									</span>
									{@render roleSelect(person)}
									<button
										type="button"
										class="btn btn-ghost btn-sm btn-square text-error"
										disabled={busy}
										aria-label={$t('share.remove_person', {
											values: { name: displayName(person) }
										})}
										title={$t('share.remove')}
										onclick={() => removeMember(person)}
									>
										<TrashCanOutline class="h-4 w-4" />
									</button>
								</li>
							{/each}
						</ul>
						{#if sharing.members.length === 0}
							<p class="text-sm text-base-content/60">{$t('share.no_members_yet')}</p>
						{/if}

						{#if sharing.invites.length > 0}
							<div class="divider my-0 text-xs text-base-content/60">
								{$t('share.waiting_for_response')}
							</div>
							<ul class="divide-y divide-base-300">
								{#each sharing.invites as person (person.uuid)}
									<li class="flex items-center gap-3 py-2.5">
										<span class="min-w-0 flex-1">
											<span class="block truncate font-medium">{displayName(person)}</span>
											<span class="badge badge-ghost badge-sm">{$t('share.pending')}</span>
										</span>
										{@render roleSelect(person)}
										<button
											type="button"
											class="btn btn-ghost btn-sm"
											disabled={busy}
											onclick={() => revokeInvite(person)}
										>
											{$t('share.cancel_invite')}
										</button>
									</li>
								{/each}
							</ul>
						{/if}
					</div>
				</div>
			{:else if tab === 'links'}
				<!-- GUEST LINKS: links for people without an account -->
				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-4 md:p-6">
						<div class="flex items-start justify-between gap-3">
							{@render sectionHeading(
								LinkVariant,
								$t('share.guest_links'),
								$t('share.guest_links_hint')
							)}
							{#if !showNewLink && activeLinks.length > 0}
								<button
									type="button"
									class="btn btn-primary btn-sm shrink-0 gap-1"
									onclick={() => (showNewLink = true)}
								>
									<Plus class="h-4 w-4" />
									{$t('share.new_link')}
								</button>
							{/if}
						</div>

						{#if showNewLink || activeLinks.length === 0}
							<form class="space-y-3 rounded-xl bg-base-200 p-4" onsubmit={createGuestLink}>
								<div class="grid gap-3 sm:grid-cols-[1fr_auto_auto]">
									<div>
										<label class="field-label" for="guest-link-label"
											>{$t('share.link_label')}</label
										>
										<input
											id="guest-link-label"
											class="input w-full"
											maxlength="100"
											bind:value={guestLabel}
											placeholder={$t('share.link_label_placeholder')}
										/>
									</div>
									<div>
										<label class="field-label" for="guest-link-role">{$t('share.role')}</label>
										<select id="guest-link-role" class="select w-32" bind:value={guestRole}>
											<option value="viewer">{$t('share.role_viewer')}</option>
											<option value="editor">{$t('share.role_editor')}</option>
										</select>
									</div>
									<div>
										<label class="field-label" for="guest-link-expiry"
											>{$t('share.expires_after')}</label
										>
										<select id="guest-link-expiry" class="select w-36" bind:value={guestExpiryDays}>
											<option value={1}>{$t('share.days_count', { values: { count: 1 } })}</option>
											<option value={7}>{$t('share.days_count', { values: { count: 7 } })}</option>
											<option value={30}>{$t('share.days_count', { values: { count: 30 } })}</option
											>
											<option value={0}>{$t('share.never_expires')}</option>
										</select>
									</div>
								</div>
								<p class="field-hint">{$t(`share.role_${guestRole}_hint`)}</p>
								<div class="flex justify-end gap-2">
									{#if activeLinks.length > 0}
										<button
											type="button"
											class="btn btn-ghost"
											onclick={() => (showNewLink = false)}
										>
											{$t('adventures.cancel')}
										</button>
									{/if}
									<button type="submit" class="btn btn-primary gap-2" disabled={busy}>
										<LinkVariant class="h-5 w-5" />
										{$t('share.create_and_copy')}
									</button>
								</div>
							</form>
						{/if}

						{#if activeLinks.length > 0}
							<ul class="divide-y divide-base-300">
								{#each activeLinks as link (link.id)}
									<li class="flex flex-wrap items-center gap-3 py-3">
										<div class="shrink-0 rounded-lg bg-base-200 p-2">
											<LinkVariant class="h-5 w-5 text-primary" />
										</div>
										<span class="min-w-0 flex-1">
											<span class="block truncate font-medium"
												>{link.label || $t('share.guest_link')}</span
											>
											<span
												class="flex flex-wrap items-center gap-1.5 text-xs text-base-content/60"
											>
												<span class="badge badge-ghost badge-sm">
													{link.role === 'editor'
														? $t('share.role_editor')
														: $t('share.role_viewer')}
												</span>
												{formatExpiry(link.expires_at)}
											</span>
										</span>
										<button
											type="button"
											class="btn btn-sm gap-1"
											onclick={() => copy(guestUrl(link.token))}
										>
											<ContentCopy class="h-4 w-4" />
											{$t('share.copy_link')}
										</button>
										<button
											type="button"
											class="btn btn-ghost btn-sm text-error"
											disabled={busy}
											onclick={() => revokeGuestLink(link.id)}
										>
											{$t('share.revoke')}
										</button>
									</li>
								{/each}
							</ul>
						{/if}
						{#if inactiveLinkCount > 0}
							<p class="field-hint">
								{$t('share.inactive_links', { values: { count: inactiveLinkCount } })}
							</p>
						{/if}
					</div>
				</div>
			{:else}
				<!-- STORY: status and link, who can read it, then what it shows -->
				{#if visibility === 'private'}
					<div role="status" class="alert rounded-xl border border-base-300">
						<LockOutline class="h-6 w-6 shrink-0" />
						<div>
							<h3 class="font-bold">{$t('share.story_is_private')}</h3>
							<p class="text-sm">
								{sharing.allow_public_links
									? $t('share.story_private_next_step')
									: $t('share.story_private_links_off')}
							</p>
						</div>
					</div>
				{:else}
					<div
						role="status"
						class="alert alert-success alert-soft flex-col items-stretch gap-3 rounded-xl"
					>
						<div class="flex items-center gap-2">
							<CheckCircle class="h-6 w-6 shrink-0" />
							<h3 class="font-bold">{$t(`share.story_is_live_${visibility}`)}</h3>
						</div>
						<div class="join w-full">
							<input
								class="input join-item min-w-0 flex-1 bg-base-100 font-mono text-sm text-base-content"
								readonly
								aria-label={$t('share.story_link')}
								value={storyUrl}
								onfocus={(e) => e.currentTarget.select()}
							/>
							<button
								type="button"
								class="btn btn-primary join-item gap-2"
								onclick={() => copy(storyUrl)}
							>
								<ContentCopy class="h-4 w-4" />
								{$t('share.copy')}
							</button>
						</div>
						<div class="flex flex-wrap gap-2">
							<a class="btn btn-sm gap-1" href={storyUrl} target="_blank" rel="noopener">
								<OpenInNew class="h-4 w-4" />
								{$t('share.open')}
							</a>
							<a
								class="btn btn-sm gap-1"
								href={`/collections/${collection.id}?preview=story`}
								data-sveltekit-reload
							>
								<EyeOutline class="h-4 w-4" />
								{$t('share.preview')}
							</a>
						</div>
					</div>
				{/if}

				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-4 md:p-6">
						<div id="share-who-can-read">
							{@render sectionHeading(Earth, $t('share.who_can_read'), $t('share.story_hint'))}
						</div>
						<div
							class="grid gap-2 sm:grid-cols-3"
							role="radiogroup"
							aria-labelledby="share-who-can-read"
						>
							{#each VISIBILITY_CHOICES as choice (choice.value)}
								{@const current = visibility === choice.value}
								{@const available = isAvailable(choice.value)}
								<button
									type="button"
									role="radio"
									aria-checked={current}
									aria-disabled={!available}
									class="flex flex-col items-start gap-1 rounded-xl border-2 p-3 text-left transition-colors {current
										? 'border-primary bg-primary/10'
										: available
											? 'border-base-300 hover:border-primary/50 hover:bg-base-200'
											: 'cursor-not-allowed border-base-300 opacity-50'}"
									disabled={busy || !available}
									onclick={() => setVisibility(choice.value)}
								>
									<span class="flex items-center gap-2 font-semibold">
										<choice.icon class="h-5 w-5 {current ? 'text-primary' : ''}" />
										{$t(`share.visibility_${choice.value}`)}
									</span>
									<span class="text-xs text-base-content/70">
										{available
											? $t(`share.visibility_${choice.value}_short`)
											: $t('share.turned_off')}
									</span>
								</button>
							{/each}
						</div>
						{#if !sharing.allow_public_links}
							<div role="note" class="alert alert-warning alert-soft rounded-xl text-sm">
								<InformationOutline class="h-5 w-5 shrink-0" />
								<div>
									<p class="font-semibold">{$t('share.public_links_off')}</p>
									{#if sharing.is_admin}
										<p>
											{$t('share.public_links_admin_hint_before')}
											<code class="rounded bg-base-100 px-1"
												>ALLOW_PUBLIC_COLLECTION_LINKS=true</code
											>
											{$t('share.public_links_admin_hint_after')}
										</p>
									{:else}
										<p>{$t('share.public_links_ask_admin')}</p>
									{/if}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-4 md:p-6">
						<div class="flex items-start justify-between gap-3">
							{@render sectionHeading(
								EyeOutline,
								$t('share.what_story_shows'),
								visibility === 'private'
									? `${$t('share.story_groups_hint')} ${$t('share.story_groups_private_hint')}`
									: $t('share.story_groups_hint')
							)}
							<span class="badge badge-ghost shrink-0">
								{$t('share.groups_on', {
									values: { count: shownGroupCount, total: STORY_GROUPS.length }
								})}
							</span>
						</div>
						{#each GROUP_SECTIONS as section (section.title)}
							<div class="space-y-2">
								<p class="text-xs font-semibold uppercase tracking-wide text-base-content/50">
									{$t(section.title)}
								</p>
								{#each section.groups as group (group)}
									<label class="field-toggle">
										<input
											type="checkbox"
											class="toggle toggle-primary"
											checked={Boolean(sharing.story_groups[group])}
											disabled={busy}
											onchange={() => toggleGroup(group)}
										/>
										<span>
											<span class="font-semibold text-base-content"
												>{$t(`share.group_${group}`)}</span
											>
											<p class="field-hint">{$t(`share.group_${group}_hint`)}</p>
										</span>
									</label>
								{/each}
							</div>
						{/each}
						<p class="field-hint flex items-start gap-2">
							<InformationOutline class="mt-0.5 h-4 w-4 shrink-0" />
							{$t('share.story_always_private')}
						</p>
					</div>
				</div>

				<div class="card border border-base-300 bg-base-100">
					<div class="card-body gap-4 p-4 md:p-6">
						{@render sectionHeading(
							CommentMultiple,
							$t('share.comments_title'),
							visibility === 'private' ? $t('share.comments_need_story') : $t('share.comments_hint')
						)}
						<div
							class="grid gap-2 sm:grid-cols-3"
							role="radiogroup"
							aria-label={$t('share.comments_title')}
						>
							{#each COMMENT_CHOICES as choice (choice)}
								{@const current = sharing.comment_access === choice}
								{@const available = choice === 'off' || visibility !== 'private'}
								<button
									type="button"
									role="radio"
									aria-checked={current}
									aria-disabled={!available}
									class="flex flex-col items-start gap-1 rounded-xl border-2 p-3 text-left transition-colors {current
										? 'border-primary bg-primary/10'
										: available
											? 'border-base-300 hover:border-primary/50 hover:bg-base-200'
											: 'cursor-not-allowed border-base-300 opacity-50'}"
									disabled={busy || !available}
									onclick={() => setCommentAccess(choice)}
								>
									<span class="font-semibold">{$t(`share.comments_${choice}`)}</span>
									<span class="text-xs text-base-content/70"
										>{$t(`share.comments_${choice}_hint`)}</span
									>
								</button>
							{/each}
						</div>
						{#if sharing.comment_access !== 'off'}
							<p class="field-hint flex items-start gap-2">
								<InformationOutline class="mt-0.5 h-4 w-4 shrink-0" />
								{$t('share.comments_public_note')}
							</p>
						{/if}
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer, as in the other collection modals. Changes save as you make them. -->
		<div
			class="shrink-0 border-t border-base-300 bg-base-100/90 px-4 py-3 backdrop-blur-lg md:px-6"
		>
			<div class="flex items-center justify-end gap-3">
				<span class="mr-auto hidden text-xs text-base-content/60 sm:inline"
					>{$t('share.saved_automatically')}</span
				>
				<button type="button" class="btn btn-primary gap-2" onclick={onClose}>
					<Check class="h-5 w-5" />
					{$t('share.done')}
				</button>
			</div>
		</div>
	</div>
	<button type="button" class="modal-backdrop" aria-label={$t('about.close')} onclick={onClose}
	></button>
</dialog>
