// routes/signup/+page.server.ts
import { lucia } from "$lib/server/auth";
import { error, fail, redirect } from "@sveltejs/kit";
import { generateId } from "lucia";
import { Argon2id } from "oslo/password";
import { db } from "$lib/db/db.server";
import type { DatabaseUser } from "$lib/server/auth";

import type { Actions } from "./$types";
import { userTable } from "$lib/db/schema";
import { eq } from "drizzle-orm";

export const actions: Actions = {
  default: async (event) => {
    const formData = await event.request.formData();
    const username = formData.get("username");
    const password = formData.get("password");
    const firstName = formData.get("first_name");
    const lastName = formData.get("last_name");
    let role: string = "";
    // username must be between 4 ~ 31 characters, and only consists of lowercase letters, 0-9, -, and _
    // keep in mind some database (e.g. mysql) are case insensitive

    // check all to make sure all fields are provided
    if (!username || !password || !firstName || !lastName) {
      return fail(400, {
        message: "All fields are required",
      });
    }

    if (!event.locals.user) {
      role = "user";
    }

    if (event.locals.user && event.locals.user.role === "admin") {
      const isAdmin = formData.get("role") === "on";
      role = isAdmin ? "admin" : "user";
    }

    if (
      typeof username !== "string" ||
      username.length < 3 ||
      username.length > 31 ||
      !/^[a-z0-9_-]+$/.test(username)
    ) {
      return fail(400, {
        message: "Invalid username",
      });
    }
    if (
      typeof password !== "string" ||
      password.length < 6 ||
      password.length > 255
    ) {
      return fail(400, {
        message: "Invalid password",
      });
    }

    if (
      typeof firstName !== "string" ||
      firstName.length < 1 ||
      firstName.length > 255
    ) {
      return fail(400, {
        message: "Invalid first name",
      });
    }

    if (
      typeof lastName !== "string" ||
      lastName.length < 1 ||
      lastName.length > 255
    ) {
      return fail(400, {
        message: "Invalid last name",
      });
    }

    const userId = generateId(15);
    const hashedPassword = await new Argon2id().hash(password);

    const usernameTaken = await db
      .select()
      .from(userTable)
      .where(eq(userTable.username, username))
      .limit(1)
      .then((results) => results[0] as unknown as DatabaseUser | undefined);

    if (usernameTaken) {
      return fail(400, {
        message: "Username already taken",
      });
    }
    await db
      .insert(userTable)
      .values({
        id: userId,
        username: username,
        first_name: firstName,
        last_name: lastName,
        hashed_password: hashedPassword,
        signup_date: new Date(),
        role: role,
        last_login: new Date(),
      } as DatabaseUser)
      .execute();

    if (!event.locals.user) {
      const session = await lucia.createSession(userId, {});
      const sessionCookie = lucia.createSessionCookie(session.id);
      event.cookies.set(sessionCookie.name, sessionCookie.value, {
        path: ".",
        ...sessionCookie.attributes,
      });

      redirect(302, "/");
    } else {
      if (event.locals.user && event.locals.user.role !== "admin") {
        return error(403, {
          message: "You are not authorized to add users",
        });
      }

      return {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          message: "User created",
        }),
      };
    }
  },
};
