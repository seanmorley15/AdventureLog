<script>
	import Navbar from '$lib/components/Navbar.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import 'tailwindcss/tailwind.css';
	export let data;
</script>

<Navbar {data} />
<Toast />

<slot></slot>
