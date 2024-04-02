import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import dotenv from 'dotenv';
dotenv.config();
const { DATABASE_URL } = process.env;

const client =  postgres(DATABASE_URL) 
export const db = drizzle(client, {});
