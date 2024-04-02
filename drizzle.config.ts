import type { Config } from 'drizzle-kit';
import * as dotenv from 'dotenv';
dotenv.config();
const { DATABASE_URL } = process.env;
if (!DATABASE_URL) {
 throw new Error('No url');
}
export default {
 schema: './src/lib/db/schema.ts',
 out: './migrations',
 driver: 'pg',
 dbCredentials: {
  connectionString: DATABASE_URL
 }
} satisfies Config;