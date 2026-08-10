export type SunriseSunset = {
	date: string;
	sunrise: string;
	sunset: string;
};

export function visitDateKey(startDate: string | null | undefined): string | null {
	if (!startDate) return null;
	return startDate.split('T')[0] ?? null;
}

export async function fetchSunriseSunset(
	locationId: string,
	date: string
): Promise<SunriseSunset | null> {
	const params = new URLSearchParams({
		location_id: locationId,
		date
	});

	const response = await fetch(`/api/sunrise-sunset/lookup/?${params.toString()}`);
	if (!response.ok) {
		return null;
	}

	return (await response.json()) as SunriseSunset;
}
