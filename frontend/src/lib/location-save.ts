import { DEFAULT_CURRENCY, normalizeMoneyPayload } from '$lib/money';
import type { Location } from '$lib/types';

type SaveLocationInput = {
	location: Partial<Location>;
	locationToEdit?: { id: string } | null;
	collectionId?: string | null;
	defaultCurrency?: string;
};

function toFixedCoordinate(value: unknown): number | null {
	if (value === null || value === undefined) return null;
	const parsed = typeof value === 'string' ? Number(value) : Number(value);
	if (Number.isNaN(parsed)) return null;
	return Number(parsed.toFixed(6));
}

function sanitizeLink(value: unknown): string | null {
	if (!value || typeof value !== 'string' || !value.trim()) {
		return null;
	}

	try {
		new URL(value);
		return value;
	} catch {
		return null;
	}
}

function parseApiError(errorData: any): string {
	let errorMsg = errorData?.detail || errorData?.name?.[0] || '';
	if (errorMsg) return String(errorMsg);

	const fieldErrors = Object.entries(errorData || {})
		.filter(([_, value]) => Array.isArray(value))
		.map(([key, value]) => `${key}: ${(value as string[]).join(', ')}`)
		.join('; ');

	return fieldErrors || 'Failed to save location';
}

export async function saveLocation({
	location,
	locationToEdit = null,
	collectionId = null,
	defaultCurrency = DEFAULT_CURRENCY
}: SaveLocationInput): Promise<Location> {
	const payload: Record<string, any> = {
		...location,
		latitude: toFixedCoordinate(location.latitude),
		longitude: toFixedCoordinate(location.longitude),
		link: sanitizeLink(location.link),
		description:
			typeof location.description === 'string' && location.description.trim()
				? location.description
				: null
	};

	if (collectionId) {
		payload.collections = [collectionId];
	}

	if (location.price === null || location.price === undefined) {
		payload.price = null;
		payload.price_currency = null;
	} else {
		const normalized = normalizeMoneyPayload(payload, 'price', 'price_currency', defaultCurrency);
		payload.price = normalized.price;
		payload.price_currency = normalized.price_currency;
	}

	const isUpdate = Boolean(locationToEdit?.id);
	if (isUpdate && !collectionId) {
		delete payload.collections;
	}

	const res = await fetch(isUpdate ? `/api/locations/${locationToEdit?.id}` : '/api/locations', {
		method: isUpdate ? 'PATCH' : 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	if (!res.ok) {
		const errorData = await res.json().catch(() => ({}));
		throw new Error(parseApiError(errorData));
	}

	return res.json();
}
