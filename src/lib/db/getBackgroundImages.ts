import { eq } from "drizzle-orm";
import { db } from "./db.server";
import { imagesTable } from "./schema";
import { ensureBucketExists, getObjectUrl, s3Client } from "$lib/server/s3";
import { ListObjectsV2Command } from "@aws-sdk/client-s3";

export const getBackgroundImages = async () => {
  await ensureBucketExists("backgrounds");

  const data = await s3Client.send(
    new ListObjectsV2Command({ Bucket: "backgrounds" })
  );

  const randomImages = data.Contents?.map((item) => item.Key) ?? [];
  const randomIndex = Math.floor(Math.random() * randomImages.length);

  const randomImage = randomImages[randomIndex];

  console.log(randomImage);

  let url = getObjectUrl("backgrounds", randomImage as string);
  console.log(url);

  if (!data.Contents) {
    url =
      "https://512pixels.net/downloads/macos-wallpapers-thumbs/10-14-Night-Thumb.jpg";
  }

  return url as string;
};
