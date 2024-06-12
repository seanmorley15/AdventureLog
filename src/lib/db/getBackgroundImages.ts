import { eq } from "drizzle-orm";
import { db } from "./db.server";
import { imagesTable } from "./schema";

export const getBackgroundImages = async (numberOfResults: number | null) => {
  const images = await db
    .select({ url: imagesTable.url })
    .from(imagesTable)
    .where(eq(imagesTable.type, "background"))
    .execute();

  if (numberOfResults) {
    let randomIndex = Math.floor(Math.random() * images.length);
    return images.slice(randomIndex, randomIndex + numberOfResults) as {
      url: string;
    }[];
  }

  return images as { url: string }[];
};
