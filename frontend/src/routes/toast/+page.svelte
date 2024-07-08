<script>
	import { addToast } from '$lib/toasts';

	const showToast = () => {
		addToast('success', 'This is a success message!');
		addToast('error', 'This is an error message!');
		addToast('info', 'This is an info message!');
		addToast('warning', 'This is a warning message!');
	};
</script>

<button on:click={showToast}>Show Toast</button>
