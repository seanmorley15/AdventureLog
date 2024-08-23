<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/stores';
	import { addToast } from '$lib/toasts';
	import type { Adventure, Collection, User } from '$lib/types.js';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { exportData } from '$lib';

	export let data;
	let user: User;
	if (data.user) {
		user = data.user;
	}

	onMount(async () => {
		if (browser) {
			const queryParams = new URLSearchParams($page.url.search);
			const pageParam = queryParams.get('page');

			if (pageParam === 'success') {
				addToast('success', 'Settings updated successfully!');
				console.log('Settings updated successfully!');
			}
		}
	});

	$: {
		if (browser && $page.form?.success) {
			window.location.href = '/settings?page=success';
		}
		if (browser && $page.form?.error) {
			addToast('error', 'Error updating settings');
		}
	}

	async function exportAdventures() {
		const url = await exportData();

		const a = document.createElement('a');
		a.href = url;
		a.download = 'adventure-log-export.json';
		a.click();
		URL.revokeObjectURL(url);
	}

	async function checkVisitedRegions() {
		let res = await fetch('/api/countries/region_check_all_adventures/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});
		let data = await res.json();
		if (res.ok) {
			addToast('success', `${data.regions_visited} regions updated`);
		} else {
			addToast('error', 'Error updating visited regions');
		}
	}
</script>

<h1 class="text-center font-extrabold text-4xl mb-6">Settings Page</h1>

<h1 class="text-center font-extrabold text-xl">User Account Settings</h1>
<div class="flex justify-center">
	<form
		method="post"
		action="?/changeDetails"
		use:enhance
		class="w-full max-w-xs"
		enctype="multipart/form-data"
	>
		<label for="username">Username</label>
		<input
			bind:value={user.username}
			name="username"
			id="username"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<label for="first_name">First Name</label>
		<input
			type="text"
			bind:value={user.first_name}
			name="first_name"
			id="first_name"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />

		<label for="last_name">Last Name</label>
		<input
			type="text"
			bind:value={user.last_name}
			name="last_name"
			id="last_name"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br />
		<!-- <label for="first_name">Email</label>
		<input
			type="email"
			bind:value={user.email}
			name="email"
			id="email"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/><br /> -->
		<label for="profilePicture">Profile Picture</label>
		<input
			type="file"
			name="profile_pic"
			id="profile_pic"
			class="file-input file-input-bordered w-full max-w-xs mb-2"
		/><br />
		<button class="py-2 mt-2 px-4 btn btn-primary">Update</button>
	</form>
</div>

{#if $page.form?.message}
	<div class="text-center text-error mt-4">
		{$page.form?.message}
	</div>
{/if}

<h1 class="text-center font-extrabold text-xl mt-4 mb-2">Password Change</h1>
<div class="flex justify-center">
	<form action="?/changePassword" method="post" class="w-full max-w-xs">
		<input
			type="password"
			name="password1"
			placeholder="New Password"
			id="password1"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<br />
		<input
			type="password"
			name="password2"
			id="password2"
			placeholder="Confirm New Password"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<button class="py-2 px-4 btn btn-primary mt-2">Change Password</button>
		<br />
	</form>
</div>

<h1 class="text-center font-extrabold text-xl mt-4 mb-2">Email Change</h1>
<div class="flex justify-center">
	<form action="?/changeEmail" method="post" class="w-full max-w-xs">
		<label for="current_email">Current Email</label>
		<input
			type="email"
			name="current_email"
			placeholder={user.email || 'No Email Set'}
			id="current_email"
			readonly
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<br />
		<input
			type="email"
			name="new_email"
			placeholder="New Email"
			id="new_email"
			class="block mb-2 input input-bordered w-full max-w-xs"
		/>
		<button class="py-2 px-4 btn btn-primary mt-2">Change Email</button>
	</form>
</div>
<div class="flex flex-col items-center">
	<h1 class="text-center font-extrabold text-xl mt-4 mb-2">Data Export</h1>
	<button class="btn btn-neutral mb-4" on:click={exportAdventures}> Export to JSON </button>
	<p>This may take a few seconds...</p>
</div>
<div class="flex flex-col items-center">
	<h1 class="text-center font-extrabold text-xl mt-4 mb-2">Visited Region Check</h1>
	<p>
		By selecting this, the server will check all of your visited adventures and mark the regions
		they are located in as "visited" in world travel.
	</p>
	<button class="btn btn-neutral mb-4" on:click={checkVisitedRegions}>Update Visited Regions</button
	>
	<p>This may take longer depending on the number of adventures you have.</p>
</div>

<small class="text-center"
	><b>For Debug Use:</b> Server PK={user.pk} | Date Joined: {user.date_joined
		? new Date(user.date_joined).toDateString()
		: ''} | Staff user: {user.is_staff}</small
>

<svelte:head>
	<title>User Settings | AdventureLog</title>
	<meta
		name="description"
		content="Update your user account settings here. Change your username, first name, last name, and profile icon."
	/>
</svelte:head>
