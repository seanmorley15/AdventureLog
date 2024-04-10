import { redirect, type Actions } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";
import { db } from "$lib/db/db.server";
import { userTable } from "$lib/db/schema";
import { eq } from "drizzle-orm";

export const load: PageServerLoad = async (event) => {
  if (event.locals.user)
    return {
      user: event.locals.user,
    };
    return redirect(302, "/login");
};

export const actions: Actions = {
    default: async (event: { request: { formData: () => any; }; }) => {
    const formData = await event.request.formData();
    let userId = formData.get("user_id");
    let username = formData.get("username");
    let firstName = formData.get("first_name");
    let lastName = formData.get("last_name");

    if (!userId) {
        return {
            status: 400,
            body: {
                message: "User ID is required"
            }
        };
    }

    await db.update(userTable)
        .set({
            username: username,
            first_name: firstName,
            last_name: lastName,
        })
        .where(eq(userTable.id, userId));

        return {
            status: 200,
            body: {
                message: "User updated"
                
            }
        };
    }
};