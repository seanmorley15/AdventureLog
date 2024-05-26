import { db } from "$lib/db/db.server";
import { adventureTable } from "$lib/db/schema";
import type { Adventure } from "$lib/utils/types";
import { eq } from "drizzle-orm";

export const load = async () => {
  const result = await db
    .select()
    .from(adventureTable)
    .where(eq(adventureTable.type, "featured"))
    .orderBy(adventureTable.id);
  return {
    result: result as Adventure[],
  };
};
