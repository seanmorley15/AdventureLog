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

export const tryRefreshToken = async (refreshToken: string) => {
	const csrfToken = await fetchCSRFToken();
	const refreshFetch = await fetch(`${serverEndpoint}/auth/token/refresh/`, {
		method: 'POST',
		headers: {
			'X-CSRFToken': csrfToken,
			'Content-Type': 'application/json' // Corrected header name
		},
		body: JSON.stringify({ refresh: refreshToken })
	});

	if (refreshFetch.ok) {
		const refresh = await refreshFetch.json();
		const token = `auth=${refresh.access}`;
		return token;
		// event.cookies.set('auth', `auth=${refresh.access}`, {
		// 	httpOnly: true,
		// 	sameSite: 'lax',
		// 	expires: new Date(Date.now() + 60 * 60 * 1000), // 60 minutes
		// 	path: '/'
		// });
	}
};
