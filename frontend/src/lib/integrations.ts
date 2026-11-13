/** Shape returned by GET /api/integrations for Immich (legacy boolean or detailed object). */
export type ImmichIntegrationStatus =
	| boolean
	| {
			exists: boolean;
			copy_locally?: boolean;
			/** The Immich web app, for links such as a place on the Immich map. */
			web_url?: string | null;
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
	webUrl: string | null;
} {
	if (typeof status === 'boolean') {
		return { enabled: status, copyLocally: false, webUrl: null };
	}
	if (status && typeof status === 'object') {
		return {
			enabled: Boolean(status.exists),
			copyLocally: Boolean(status.copy_locally),
			webUrl: status.exists && status.web_url ? status.web_url : null
		};
	}
	return { enabled: false, copyLocally: false, webUrl: null };
}
