import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import dotenv from "dotenv";
import * as schema from "$lib/db/schema";
dotenv.config();
const { DATABASE_URL } = process.env;

const client = postgres(DATABASE_URL || ""); // Pass DATABASE_URL as a string argument
export const db = drizzle(client, { schema });
