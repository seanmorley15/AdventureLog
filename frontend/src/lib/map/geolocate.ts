/**
 * Shared browser-geolocation helper.
 *
 * Exists because three components independently called
 * `navigator.geolocation.getCurrentPosition` with inconsistent (and in two cases
 * absent) error handling, so a failure looked to the user like the map simply
 * jumping to the wrong place.
 *
 * The important case it adds is the secure-context check. `navigator.geolocation`
 * is present on insecure origins, but calling it over plain HTTP on anything
 * other than localhost fails. Self-hosted instances reached by LAN IP
 * (e.g. http://192.168.2.10:8015) therefore hit this constantly, and the raw
 * browser error does not make the cause obvious.
 */

export type GeolocationFailureReason =
	| 'insecure'
	| 'unsupported'
	| 'denied'
	| 'unavailable'
	| 'timeout';

/** i18n key to show for each failure reason. */
export const GEOLOCATION_ERROR_KEYS: Record<GeolocationFailureReason, string> = {
	insecure: 'map.geolocation_insecure',
	unsupported: 'map.geolocation_unavailable',
	denied: 'map.geolocation_denied',
	unavailable: 'map.geolocation_unavailable',
	timeout: 'map.geolocation_timeout'
};

export class GeolocationFailure extends Error {
	reason: GeolocationFailureReason;
	/** i18n key suitable for passing straight to `$t(...)`. */
	messageKey: string;

	constructor(reason: GeolocationFailureReason, cause?: unknown) {
		super(`Geolocation failed: ${reason}`);
		this.name = 'GeolocationFailure';
		this.reason = reason;
		this.messageKey = GEOLOCATION_ERROR_KEYS[reason];
		if (cause !== undefined) {
			(this as { cause?: unknown }).cause = cause;
		}
	}
}

export type Coordinates = { lat: number; lng: number };

const DEFAULT_OPTIONS: PositionOptions = {
	enableHighAccuracy: true,
	timeout: 10000,
	maximumAge: 60000
};

/**
 * Resolve the user's current position, or reject with a `GeolocationFailure`
 * carrying an i18n key the caller can surface to the user.
 */
export function requestCurrentPosition(options: PositionOptions = {}): Promise<Coordinates> {
	return new Promise((resolve, reject) => {
		// Checked before `navigator.geolocation`: the API object exists on insecure
		// origins, so probing for it does not catch this case.
		if (typeof window !== 'undefined' && window.isSecureContext === false) {
			reject(new GeolocationFailure('insecure'));
			return;
		}

		if (typeof navigator === 'undefined' || !navigator.geolocation) {
			reject(new GeolocationFailure('unsupported'));
			return;
		}

		navigator.geolocation.getCurrentPosition(
			(position) =>
				resolve({
					lat: position.coords.latitude,
					lng: position.coords.longitude
				}),
			(error) => {
				let reason: GeolocationFailureReason = 'unavailable';
				if (error.code === error.PERMISSION_DENIED) {
					// Browsers also report insecure origins as PERMISSION_DENIED, so
					// disambiguate on the secure-context flag where available.
					reason =
						typeof window !== 'undefined' && window.isSecureContext === false
							? 'insecure'
							: 'denied';
				} else if (error.code === error.TIMEOUT) {
					reason = 'timeout';
				}
				reject(new GeolocationFailure(reason, error));
			},
			{ ...DEFAULT_OPTIONS, ...options }
		);
	});
}
