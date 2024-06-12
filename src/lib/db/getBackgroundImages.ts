import { eq } from "drizzle-orm";
import { db } from "./db.server";
import { imagesTable } from "./schema";
import { getObjectUrl, s3Client } from "$lib/server/s3";
import { ListObjectsV2Command } from "@aws-sdk/client-s3";

export const getBackgroundImages = async () => {
  //   const images = await db
  //     .select({ url: imagesTable.url })
  //     .from(imagesTable)
  //     .where(eq(imagesTable.type, "background"))
  //     .execute();

  // list all objects in the bucket using listObjectsV2
  const data = await s3Client.send(
    new ListObjectsV2Command({ Bucket: "images" })
  );
  const randomImages = data.Contents?.map((item) => item.Key) ?? [];
  const randomIndex = Math.floor(Math.random() * randomImages.length);

  const randomImage = randomImages[randomIndex];

  console.log(randomImage);

  const url = getObjectUrl("images", randomImage as string);
  console.log(url);

  return url as string;
};
