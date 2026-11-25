import type { Schemas } from '#lib/api/index.js';

/** What taking a place away from the people who travelled there would do. See "Travelers" in API.md. */
export type UnlinkPreview = Schemas['UnlinkPreview'];
export type ReleasePreview = Omit<UnlinkPreview, 'removed_placements'>;
export type CollectionDeletePreview = Schemas['CollectionDeletePreview'];
export type DeletionPreview = Schemas['DeletionPreview'];
export type PrivacyPreview = Schemas['PrivacyPreview'];

/** Whether anyone gets a copy or anything is deleted: the cases that deserve a real dialog. */
export function hasTravelerImpact(
	preview: Pick<ReleasePreview, 'people_released' | 'visits_deleted' | 'others_uploads'>
): boolean {
	return (
		preview.people_released.length > 0 || preview.visits_deleted > 0 || preview.others_uploads > 0
	);
}

async function readPreview<T>(res: Response): Promise<T> {
	const data = await res.json().catch(() => null);
	if (!res.ok || !data) throw new Error('preview failed');
	return data as T;
}

/** A dry run: who would get a copy if the place left the collection. Changes nothing. Throws on failure. */
export async function fetchUnlinkPreview(
	locationId: string,
	collectionId: string
): Promise<UnlinkPreview> {
	return readPreview(
		await fetch(`/api/locations/${locationId}/collections/${collectionId}/?dry_run=1`, {
			method: 'DELETE'
		})
	);
}

/** A dry run: who would get a copy of which places if the collection were deleted. Throws on failure. */
export async function fetchCollectionDeletePreview(
	collectionId: string
): Promise<CollectionDeletePreview> {
	return readPreview(
		await fetch(`/api/collections/${collectionId}/?dry_run=1`, { method: 'DELETE' })
	);
}
