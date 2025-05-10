<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Lost from '$lib/assets/undraw_lost.svg';
	import ServerError from '$lib/assets/undraw_server_error.svg';
</script>

{#if $page.status === 404}
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8"
	>
		<div class="mx-auto max-w-md text-center">
			<img src={Lost} alt="Lost in the forest" />
			<h1 class="text-center text-5xl font-extrabold mt-2">
				{$page.status}: {$page.error?.message}
			</h1>
			<h1 class="mt-4 text-xl font-bold tracking-tight text-foreground">
				Oops, looks like you've wandered off the beaten path.
			</h1>

			<p class="mt-4 text-muted-foreground">We couldn't find the page you were looking for.</p>
			<div class="mt-6 flex flex-col items-center gap-4 sm:flex-row">
				<button class="btn btn-neutral" on:click={() => goto('/')}>Go to Homepage</button>
			</div>
		</div>
	</div>
{/if}

{#if $page.status === 500}
	<div
		class="flex min-h-[100dvh] flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8"
	>
		<div class="mx-auto max-w-md text-center">
			<img src={ServerError} alt="Lost in the forest" />
			<h1 class="text-center text-5xl font-extrabold mt-2">
				{$page.status}: {$page.error?.message}
			</h1>
			<h1 class="mt-4 text-xl font-bold tracking-tight text-foreground">
				Oops, looks like something went wrong.
			</h1>

			<p class="mt-4">
				AdventureLog server encountered an error while processing your request.
				<br />
				Please check the server logs for more information.
			</p>

			<div class="alert alert-warning mt-4">
				<p class="text-muted-foreground">
					<strong>Administrators:</strong> Please check your setup using the
					<a class="link link-primary" target="_blank" href="https://adventurelog.app"
						>documentation</a
					>.
				</p>
			</div>

			<!-- If the route is /login give a hint as an alert -->
			{#if $page.url.pathname === '/login' || $page.url.pathname === '/signup'}
				<div class="alert alert-info mt-4">
					<p
						class="text-muted
						-foreground"
					>
						<strong>Hint:</strong> If you are an administrator, please check your PUBLIC_SERVER_URL
						in the frontend config to make sure it can reach the backend.
						<br />
					</p>
				</div>
			{/if}

			<div class="mt-6 flex flex-col items-center gap-4 sm:flex-row">
				<button class="btn btn-neutral" on:click={() => goto('/')}>Go to Homepage</button>
			</div>
		</div>
	</div>
{/if}
