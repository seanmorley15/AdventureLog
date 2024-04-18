import { DrizzlePostgreSQLAdapter } from "@lucia-auth/adapter-drizzle";
import { Lucia, TimeSpan } from "lucia";
import { dev } from "$app/environment";
import { userTable, sessionTable } from "$lib/db/schema";
import { db } from "$lib/db/db.server";

const adapter = new DrizzlePostgreSQLAdapter(db, sessionTable, userTable);

export const lucia = new Lucia(adapter, {
  sessionCookie: {
    attributes: {
      secure: !dev,
    },
  },
  getUserAttributes: (attributes) => {
    return {
      // attributes has the type of DatabaseUserAttributes
      username: attributes.username,
      id: attributes.id,
      first_name: attributes.first_name,
      last_name: attributes.last_name,
      icon: attributes.icon,
      signup_date: attributes.signup_date,
      last_login: attributes.last_login,
      role: attributes.role,
    };
  },
});

declare module "lucia" {
  interface Register {
    Lucia: typeof lucia;
    DatabaseUserAttributes: DatabaseUser;
  }
}

export interface DatabaseUser {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  icon: string;
  hashed_password: string;
  signup_date: Date;
  last_login: Date;
  role: string;
}
