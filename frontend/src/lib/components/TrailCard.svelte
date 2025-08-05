<script lang="ts"></script>

<div class="relative group">
	{#if trailToEdit?.id === trail.id}
		<!-- Edit Mode -->
		<div class="bg-warning/10 p-4 rounded-lg border border-warning/30">
			<div class="flex items-center gap-2 mb-3">
				<EditIcon class="w-4 h-4 text-warning" />
				<span class="text-sm font-medium text-warning">Editing Trail</span>
			</div>
			<div class="grid gap-3">
				<input
					type="text"
					bind:value={editingTrailName}
					class="input input-bordered input-sm"
					placeholder="Trail name"
				/>
				<input
					type="url"
					bind:value={editingTrailLink}
					class="input input-bordered input-sm"
					placeholder="External link"
					disabled={editingTrailWandererId.trim() !== ''}
				/>
				<div class="text-center text-xs text-base-content/60">OR</div>
				<input
					type="text"
					bind:value={editingTrailWandererId}
					class="input input-bordered input-sm"
					placeholder="Wanderer Trail ID"
					disabled={editingTrailLink.trim() !== ''}
				/>
			</div>
			<div class="flex gap-2 mt-3">
				<button
					class="btn btn-success btn-xs flex-1"
					disabled={!validateEditTrailForm()}
					on:click={saveTrailEdit}
				>
					<CheckIcon class="w-3 h-3" />
					Save
				</button>
				<button class="btn btn-ghost btn-xs flex-1" on:click={cancelEditingTrail}>
					<CloseIcon class="w-3 h-3" />
					Cancel
				</button>
			</div>
		</div>
	{:else}
		<!-- Normal Display -->
		<div
			class="bg-base-50 p-4 rounded-lg border border-base-200 hover:border-base-300 transition-colors"
		>
			<div class="flex items-center gap-3 mb-3">
				<div class="p-2 bg-accent/10 rounded">
					{#if trail.wanderer_id}
						<Star class="w-4 h-4 text-accent" />
					{:else}
						<LinkIcon class="w-4 h-4 text-accent" />
					{/if}
				</div>
				<div class="flex-1 min-w-0">
					<div class="font-medium truncate">{trail.name}</div>
					<div class="text-xs text-accent/70 mt-1">
						{trail.provider || 'External'}
					</div>
				</div>
			</div>

			{#if trail.link}
				<a
					href={trail.link}
					target="_blank"
					rel="noopener noreferrer"
					class="text-xs text-accent hover:text-accent-focus mb-3 break-all block underline"
				>
					{trail.link}
				</a>
			{:else if trail.wanderer_id}
				<div class="text-xs text-base-content/60 mb-3 break-all">
					Wanderer ID: {trail.wanderer_id}
				</div>
			{:else}
				<div class="text-xs text-base-content/40 mb-3 italic">No external link available</div>
			{/if}

			<!-- Trail Controls -->
			<div class="flex gap-2 justify-end">
				<button
					type="button"
					class="btn btn-warning btn-xs btn-square tooltip tooltip-top"
					data-tip="Edit Trail"
					on:click={() => startEditingTrail(trail)}
				>
					<EditIcon class="w-3 h-3" />
				</button>
				<button
					type="button"
					class="btn btn-error btn-xs btn-square tooltip tooltip-top"
					data-tip="Remove Trail"
					on:click={() => removeTrail(trail.id)}
				>
					<TrashIcon class="w-3 h-3" />
				</button>
			</div>
		</div>
	{/if}
</div>
