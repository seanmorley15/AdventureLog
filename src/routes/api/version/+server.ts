import type { RequestEvent } from "@sveltejs/kit";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const packageJsonPath = join(__dirname, "..", "..", "..", "..", "package.json");
const json = readFileSync(packageJsonPath, "utf8");
const pkg = JSON.parse(json);

const version = pkg.version;

/**
 * Handles the GET request for the version API endpoint.
 * @param event - The request event object.
 * @returns A Promise that resolves to a Response object.
 */
export async function GET(event: RequestEvent): Promise<Response> {
  return new Response(JSON.stringify({ version: version }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
