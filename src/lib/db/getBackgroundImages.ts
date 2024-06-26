import { ensureBucketExists, getObjectUrl, s3Client } from "$lib/server/s3";
import { ListObjectsV2Command } from "@aws-sdk/client-s3";

/**
 * Retrieves a random background image URL from the "backgrounds" bucket.
 * If the randomly selected image is ".emptyFolderPlaceholder", it recursively calls itself to get another image.
 * If no images are found in the bucket, a default image URL is returned.
 *
 * @returns A Promise that resolves to a string representing the URL of the background image.
 */
export const getBackgroundImages = async (): Promise<string> => {
  await ensureBucketExists("backgrounds");

  const data = await s3Client.send(
    new ListObjectsV2Command({ Bucket: "backgrounds" })
  );

  const randomImages = data.Contents?.map((item) => item.Key) ?? [];
  const randomIndex = Math.floor(Math.random() * randomImages.length);

  const randomImage = randomImages[randomIndex];

  if (randomImage == ".emptyFolderPlaceholder") {
    return getBackgroundImages();
  }

  console.log(randomImage);

  let url = getObjectUrl("backgrounds", randomImage as string);
  console.log(url);

  if (!data.Contents) {
    url =
      "https://512pixels.net/downloads/macos-wallpapers-thumbs/10-14-Night-Thumb.jpg";
  }

  return url as string;
};
