import { error, fail, redirect, type Actions } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import {
  adventureTable,
  sessionTable,
  userPlannedTrips,
  userTable,
  userVisitedWorldTravel,
} from "$lib/db/schema";
import { lucia, type DatabaseUser } from "$lib/server/auth";
import { count, eq } from "drizzle-orm";
import { generateId } from "lucia";
import { Argon2id } from "oslo/password";

export const load: PageServerLoad = async (event) => {
  let users: DatabaseUser[] = [];
  let visitCount: number = NaN;
  let userCount: number = NaN;
  let planCount: number = NaN;
  let tripCount: number = NaN;
  let featuredCount: number = NaN;
  let regionCount: number = NaN;
  if (!event.locals.user) {
    return redirect(302, "/login");
  }
  if (event.locals.user.role !== "admin") {
    return redirect(302, "/settings");
  }
  if (event.locals.user.role === "admin") {
    users = (await db.select().from(userTable).execute()) as DatabaseUser[];
    visitCount = (await db
      .select({ count: count() })
      .from(adventureTable)
      .where(eq(adventureTable.type, "mylog"))
      .execute()) as unknown as number;
    userCount = (await db
      .select({ count: count() })
      .from(userTable)
      .execute()) as unknown as number;
    regionCount = (await db
      .select({ count: count() })
      .from(userVisitedWorldTravel)
      .execute()) as unknown as number;
    planCount = (await db
      .select({ count: count() })
      .from(adventureTable)
      .where(eq(adventureTable.type, "planner"))
      .execute()) as unknown as number;
    tripCount = (await db
      .select({ count: count() })
      .from(userPlannedTrips)
      .execute()) as unknown as number;
    featuredCount = (await db
      .select({ count: count() })
      .from(adventureTable)
      .where(eq(adventureTable.type, "featured"))
      .execute()) as unknown as number;
  }
  return {
    users,
    visitCount,
    userCount,
    regionCount,
    planCount,
    tripCount,
    featuredCount,
  };
};

export const actions: Actions = {
  clearAllSessions: async (event) => {
    if (event.locals.user && event.locals.user.role !== "admin") {
      return error(403, {
        message: "You are not authorized to perform this action",
      });
    } else {
      console.log("ALL SESSIONS CLEARED by " + event.locals.user?.username);
      await db.delete(sessionTable).execute();
      return {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          message: "Cleared all sessions",
        }),
      };
    }
  },
  adduser: async (event) => {
    const formData = await event.request.formData();
    const formUsername = formData.get("username");
    let username = formUsername?.toString().toLocaleLowerCase();
    let role = formData.get("role");
    if (!role) {
      role = "user";
    } else {
      role = "admin";
    }
    console.log("role", role);

    if (typeof formUsername !== "string") {
      return fail(400, { message: "Invalid username" });
    }
    const password = formData.get("password");
    const firstName = formData.get("first_name");
    const lastName = formData.get("last_name");
    // username must be between 4 ~ 31 characters, and only consists of lowercase letters, 0-9, -, and _
    // keep in mind some database (e.g. mysql) are case insensitive

    if (!event.locals.user) {
      return redirect(302, "/");
    }
    // check all to make sure all fields are provided
    if (!username || !password || !firstName || !lastName) {
      return fail(400, { message: "All fields are required" });
    }

    if (!event.locals.user || event.locals.user.role !== "admin") {
      return fail(403, {
        message: "You are not authorized to perform this action",
      });
    }

    if (
      typeof username !== "string" ||
      username.length < 3 ||
      username.length > 31 ||
      !/^[a-zA-Z0-9_-]+$/.test(username)
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

    const userId = generateId(15);
    const hashedPassword = await new Argon2id().hash(password);

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

    return { success: true };
  },
  background: async (event) => {
    console.log("background");
    const formData = await event.request.formData();
    const background = formData.get("background") as File | null;
    if (!background) {
      return fail(400, { message: "No background provided" });
    }
    if (!event.locals.user) {
      return redirect(302, "/");
    }
    let res = await event.fetch("/api/upload", {
      method: "POST",
      body: background,
      headers: {
        bucket: "images",
        type: "background",
      },
    });
    await res.json();
    console.log("Background uploaded");
    if (!res.ok) {
      return fail(500, { message: "Failed to upload background" });
    }
    return { success: true };
  },
};
