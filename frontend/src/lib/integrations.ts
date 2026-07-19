/** Shape returned by GET /api/integrations for Immich (legacy boolean or detailed object). */
export type ImmichIntegrationStatus =
	| boolean
	| {
			exists: boolean;
			copy_locally?: boolean;
	  };

export type IntegrationsResponse = {
	immich?: ImmichIntegrationStatus;
	google_maps?: boolean;
	strava?: { global?: boolean; user?: boolean };
	wanderer?: { exists?: boolean };
	endurain?: { exists?: boolean };
};

export function parseImmichIntegration(status: ImmichIntegrationStatus | undefined): {
	enabled: boolean;
	copyLocally: boolean;
} {
	if (typeof status === 'boolean') {
		return { enabled: status, copyLocally: false };
	}
	if (status && typeof status === 'object') {
		return {
			enabled: Boolean(status.exists),
			copyLocally: Boolean(status.copy_locally)
		};
	}
	return { enabled: false, copyLocally: false };
}
