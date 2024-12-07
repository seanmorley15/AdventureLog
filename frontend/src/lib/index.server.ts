const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const serverEndpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

export const fetchCSRFToken = async () => {
	const csrfTokenFetch = await fetch(`${serverEndpoint}/csrf/`);
	if (csrfTokenFetch.ok) {
		const csrfToken = await csrfTokenFetch.json();
		return csrfToken.csrfToken;
	} else {
		return null;
	}
};
