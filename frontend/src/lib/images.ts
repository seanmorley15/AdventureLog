import type { ContentImage, ImageSource } from '$lib/types';

export function normalizeContentImage(
	partial: Partial<ContentImage> & Pick<ContentImage, 'id' | 'image'>
): ContentImage {
	return {
		id: partial.id,
		image: partial.image,
		is_primary: partial.is_primary ?? false,
		immich_id: partial.immich_id ?? null,
		source: partial.source ?? 'upload',
		source_url: partial.source_url ?? null,
		latitude: partial.latitude ?? null,
		longitude: partial.longitude ?? null
	};
}

export function googleContentImage(id: string, image: string, isPrimary = false): ContentImage {
	return normalizeContentImage({ id, image, is_primary: isPrimary, source: 'google' });
}

export function defaultImageSource(source?: ImageSource | null): ImageSource {
	return source ?? 'upload';
}
