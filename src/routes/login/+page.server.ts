import { lucia } from "$lib/server/auth";
import { error, fail, redirect } from "@sveltejs/kit";
import { Argon2id } from "oslo/password";
import { db } from "$lib/db/db.server";

import type { Actions, PageServerLoad } from "./$types";
import type { DatabaseUser } from "$lib/server/auth";
import { userTable } from "$lib/db/schema";
import { eq } from "drizzle-orm";

export const load: PageServerLoad = async (event) => {
  if (event.locals.user) {
    return redirect(302, "/");
  }
  return {};
};

export const actions: Actions = {
  default: async (event) => {
    const formData = await event.request.formData();
    const username = formData.get("username");
    const password = formData.get("password");

    if (!username || !password) {
      return error(400, {
        message: "Missing username or password",
      });
    }

    if (
      typeof username !== "string" ||
      username.length < 3 ||
      username.length > 31 ||
      !/^[a-z0-9_-]+$/.test(username)
    ) {
      return error(400, {
        message: "Invalid username",
      });
    }
    if (
      typeof password !== "string" ||
      password.length < 6 ||
      password.length > 255
    ) {
      return error(400, {
        message: "Invalid password",
      });
    }

    const existingUser:any = await db
      .select()
      .from(userTable)
      .where(eq(userTable.username, username))
      .limit(1)
      .then((results) => results[0] as unknown as DatabaseUser | undefined);

    if (!existingUser) {
      return error(400, {
        message: "Incorrect username or password",
      });
    }

    const validPassword = await new Argon2id().verify(
      existingUser.hashed_password,
      password
    );
    if (!validPassword) {
      return error(400, {
        message: "Incorrect username or password",
      });
    }

    await db
      .update(userTable)
      .set({
        last_login: new Date(),
      })
      .where(eq(userTable.id, existingUser.id))
      .execute();

    const session = await lucia.createSession(existingUser.id, {});
    const sessionCookie = lucia.createSessionCookie(session.id);
    event.cookies.set(sessionCookie.name, sessionCookie.value, {
      path: ".",
      ...sessionCookie.attributes,
    });

    return redirect(302, "/");

  },
};
