<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;
	const user = data.props.user;
	console.log(user);
</script>

<h1>{user.first_name} {user.last_name}</h1>
<p>{user.username}</p>

<p>{user.is_staff ? 'Admin' : 'User'}</p>
