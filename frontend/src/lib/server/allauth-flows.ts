/** Pending/available flow entries returned by django-allauth headless 401 responses. */
export type AllauthFlow = { id: string; is_pending?: boolean };

export type AllauthAuthResponse = {
	status?: number;
	data?: { flows?: AllauthFlow[] };
	meta?: { is_authenticated?: boolean };
};

export function getAllauthFlows(body: unknown): AllauthFlow[] {
	if (!body || typeof body !== 'object') return [];
	const data = (body as AllauthAuthResponse).data;
	return Array.isArray(data?.flows) ? data.flows : [];
}

export function hasPendingAllauthFlow(body: unknown, flowId: string): boolean {
	return getAllauthFlows(body).some((flow) => flow.id === flowId && flow.is_pending === true);
}
