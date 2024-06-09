import {
  error,
  redirect,
  type Actions,
  type RequestEvent,
} from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { userTable } from "$lib/db/schema";
import { eq } from "drizzle-orm";
import { Argon2id } from "oslo/password";
import type { DatabaseUser } from "$lib/server/auth";

export const load: PageServerLoad = async (event) => {
  if (event.locals.user)
    return {
      user: event.locals.user,
    };
  return redirect(302, "/login");
};

export const actions: Actions = {
  default: async (event: RequestEvent) => {
    const formData = (await event.request.formData()) as FormData;
    let userId = formData.get("user_id") as string;
    let username = formData.get("username") as string;
    let firstName = formData.get("first_name") as string;
    let lastName = formData.get("last_name") as string;
    let icon = formData.get("icon") as string;
    let profilePicture = formData.get("profilePicture") as File;
    console.log(profilePicture);

    let password = formData.get("password") as string;

    if (!userId) {
      return {
        status: 400,
        body: {
          message: "User ID is required",
        },
      };
    }

    // if (icon.length > 1) {
    //   return {
    //     status: 400,
    //     body: {
    //       message: "Icon must be a single character",
    //     },
    //   };
    // }

    const usernameTaken = await db
      .select()
      .from(userTable)
      .where(eq(userTable.username, username))
      .limit(1)
      .then((results) => results[0] as unknown as DatabaseUser | undefined);

    if (usernameTaken && usernameTaken.id !== userId) {
      return {
        status: 400,
        body: {
          message: "Username taken!",
        },
      };
    }

    if (password) {
      let hashedPassword = await new Argon2id().hash(password);
      console.log(hashedPassword);
      await db
        .update(userTable)
        .set({
          hashed_password: hashedPassword,
        })
        .where(eq(userTable.id, userId));
    }

    if (profilePicture) {
      const response = await event.fetch("/api/upload", {
        method: "POST",
        body: profilePicture,
      });

      const data = await response.json();

      if (data.error) {
        throw error(400, {
          message: "Error uploading profile picture",
        });
      }

      console.log(data);
    }

    await db
      .update(userTable)
      .set({
        username: username,
        first_name: firstName,
        last_name: lastName,
        icon: icon,
      })
      .where(eq(userTable.id, userId));

    // return a page refresh
    return {
      status: 303,
      headers: {
        location: "/settings",
      },
    };
  },
};
