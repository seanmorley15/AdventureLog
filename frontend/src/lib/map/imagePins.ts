import type { ContentImage, Collection, ImageSource, MapImagePinSelection } from '$lib/types';
import type { FullMapFeatureCollection } from '$lib/components/map/FullMap.svelte';

export type ImageMapPin = {
	id: string;
	image: string;
	latitude: number;
	longitude: number;
	source: ImageSource;
	is_primary: boolean;
	parent_type: string;
	parent_id: string;
	parent_name: string | null;
};

export type ImagePinParentType = 'location' | 'lodging' | 'transportation' | 'visit' | 'note';

export type ImagePinContext = {
	parentType: ImagePinParentType | string;
	parentId: string;
	parentName: string;
};

export type ImagePinProperties = {
	imageId: string;
	imageUrl: string;
	source: ImageSource;
	isPrimary: boolean;
	parentType: string;
	parentId: string;
	parentName: string;
};

export type ImagePinFeatureCollection = FullMapFeatureCollection<ImagePinProperties>;

export function hasImageCoordinates(
	image: Pick<ContentImage, 'latitude' | 'longitude'> | null | undefined
): boolean {
	if (!image) return false;
	const { latitude, longitude } = image;
	return (
		latitude !== null &&
		latitude !== undefined &&
		longitude !== null &&
		longitude !== undefined &&
		Number.isFinite(latitude) &&
		Number.isFinite(longitude)
	);
}

export function contentImageToFeature(
	image: ContentImage,
	context?: ImagePinContext
): ImagePinFeatureCollection['features'][number] | null {
	if (!hasImageCoordinates(image)) return null;

	return {
		type: 'Feature',
		geometry: {
			type: 'Point',
			coordinates: [Number(image.longitude), Number(image.latitude)]
		},
		properties: {
			imageId: image.id,
			imageUrl: image.image,
			source: image.source ?? 'upload',
			isPrimary: Boolean(image.is_primary),
			parentType: context?.parentType ?? 'location',
			parentId: context?.parentId ?? '',
			parentName: context?.parentName ?? ''
		}
	};
}

export function contentImagesToGeoJson(
	images: ContentImage[] | null | undefined,
	context?: ImagePinContext
): ImagePinFeatureCollection {
	const features =
		images
			?.map((image) => contentImageToFeature(image, context))
			.filter((feature): feature is NonNullable<typeof feature> => feature !== null) ?? [];

	return { type: 'FeatureCollection', features };
}

export function imageMapPinToFeature(
	pin: ImageMapPin
): ImagePinFeatureCollection['features'][number] {
	return {
		type: 'Feature',
		geometry: {
			type: 'Point',
			coordinates: [pin.longitude, pin.latitude]
		},
		properties: {
			imageId: pin.id,
			imageUrl: pin.image,
			source: pin.source,
			isPrimary: pin.is_primary,
			parentType: pin.parent_type,
			parentId: pin.parent_id,
			parentName: pin.parent_name ?? ''
		}
	};
}

export function imageMapPinsToGeoJson(pins: ImageMapPin[]): ImagePinFeatureCollection {
	return {
		type: 'FeatureCollection',
		features: pins.map(imageMapPinToFeature)
	};
}

export function countGeotaggedImages(images: ContentImage[] | null | undefined): number {
	return images?.filter((image) => hasImageCoordinates(image)).length ?? 0;
}

export function collectCollectionImageGeoJson(collection: Collection): ImagePinFeatureCollection {
	const features: ImagePinFeatureCollection['features'] = [];

	for (const location of collection.locations ?? []) {
		for (const feature of contentImagesToGeoJson(location.images, {
			parentType: 'location',
			parentId: location.id,
			parentName: location.name
		}).features) {
			features.push(feature);
		}
	}

	for (const lodging of collection.lodging ?? []) {
		for (const feature of contentImagesToGeoJson(lodging.images, {
			parentType: 'lodging',
			parentId: lodging.id,
			parentName: lodging.name
		}).features) {
			features.push(feature);
		}
	}

	for (const transportation of collection.transportations ?? []) {
		for (const feature of contentImagesToGeoJson(transportation.images, {
			parentType: 'transportation',
			parentId: transportation.id,
			parentName: transportation.name
		}).features) {
			features.push(feature);
		}
	}

	return { type: 'FeatureCollection', features };
}

export function collectEntityGroupsWithImages(
	items: Array<{
		id: string;
		name: string;
		type: ImagePinParentType;
		images?: ContentImage[];
	}>
): ImagePinFeatureCollection {
	const features: ImagePinFeatureCollection['features'] = [];

	for (const item of items) {
		for (const feature of contentImagesToGeoJson(item.images, {
			parentType: item.type,
			parentId: item.id,
			parentName: item.name
		}).features) {
			features.push(feature);
		}
	}

	return { type: 'FeatureCollection', features };
}

export function imagePinPropsToSelection(props: ImagePinProperties): MapImagePinSelection {
	return {
		kind: 'image',
		imageId: props.imageId,
		imageUrl: props.imageUrl,
		source: props.source,
		isPrimary: props.isPrimary,
		parentType: props.parentType,
		parentId: props.parentId,
		parentName: props.parentName
	};
}

export function mapImagePinSelectionToProps(selection: MapImagePinSelection): ImagePinProperties {
	return {
		imageId: selection.imageId,
		imageUrl: selection.imageUrl,
		source: selection.source,
		isPrimary: selection.isPrimary,
		parentType: selection.parentType,
		parentId: selection.parentId,
		parentName: selection.parentName
	};
}

export function getImagePinNavigationUrl(props: ImagePinProperties): string | null {
	if (!props.parentId) return null;
	switch (props.parentType) {
		case 'location':
			return `/locations/${props.parentId}`;
		case 'lodging':
			return `/lodging/${props.parentId}`;
		case 'transportation':
			return `/transportations/${props.parentId}`;
		default:
			return null;
	}
}

export function getImagePinParentTypeKey(parentType: string): string {
	switch (parentType) {
		case 'lodging':
			return 'adventures.lodging';
		case 'transportation':
			return 'adventures.transportation';
		case 'visit':
			return 'adventures.visit';
		case 'note':
			return 'adventures.note';
		default:
			return 'adventures.location';
	}
}

export async function fetchImageMapPins(): Promise<ImageMapPin[]> {
	const response = await fetch('/api/images/map_pins/', { credentials: 'same-origin' });
	if (!response.ok) {
		throw new Error(`Failed to fetch image map pins (${response.status})`);
	}
	const data = await response.json();
	return Array.isArray(data) ? data : [];
}

export function mergeImagePinCollections(
	...collections: ImagePinFeatureCollection[]
): ImagePinFeatureCollection {
	const seen = new Set<string>();
	const features: ImagePinFeatureCollection['features'] = [];

	for (const collection of collections) {
		for (const feature of collection.features) {
			const key = feature.properties.imageId || `${feature.geometry.coordinates.join(',')}`;
			if (seen.has(key)) continue;
			seen.add(key);
			features.push(feature);
		}
	}

	return { type: 'FeatureCollection', features };
}
