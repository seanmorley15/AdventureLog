const PUBLIC_SERVER_URL = process.env['PUBLIC_SERVER_URL'];
const endpoint = PUBLIC_SERVER_URL || 'http://localhost:8000';

/** @type {import('./$types').RequestHandler} */
export async function GET(event) {
	let sessionid = event.cookies.get('sessionid');
	let fileName = event.params.file;
	let res = await fetch(`${endpoint}/media/attachments/${fileName}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Cookie: `sessionid=${sessionid}`
		}
	});
	let data = await res.text();
	return new Response(data, {
		status: res.status,
		headers: {
			'Content-Type': 'application/xml'
		}
	});
}
