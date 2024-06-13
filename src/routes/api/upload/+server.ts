// src/routes/api/upload.js

import { db } from "$lib/db/db.server";
import { imagesTable } from "$lib/db/schema";
import { deleteObject, ensureBucketExists, uploadObject } from "$lib/server/s3";
import type { RequestEvent } from "@sveltejs/kit";
import { generateId } from "lucia";

/**
 * Handles the POST request for uploading a file to S3 storage.
 *
 * @param event - The request event object.
 * @returns A promise that resolves to a response object.
 */
export async function POST(event: RequestEvent): Promise<Response> {
  try {
    if (!event.locals.user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    const contentType = event.request.headers.get("content-type") ?? "";
    const fileExtension = contentType.split("/").pop();
    const fileName = `${generateId(75)}.${fileExtension}`;
    const bucket = event.request.headers.get("bucket") as string;
    const type = event.request.headers.get("type") as string | null;

    if (!fileExtension || !fileName) {
      return new Response(JSON.stringify({ error: "Invalid file type" }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    if (!bucket) {
      return new Response(
        JSON.stringify({ error: "Bucket name is required" }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    if (!contentType.startsWith("image")) {
      return new Response(JSON.stringify({ error: "Invalid file type" }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    const fileBuffer = await event.request.arrayBuffer();
    const metaData = {
      "Content-Type": contentType,
    };

    await ensureBucketExists(bucket);

    if (event.locals.user?.icon && bucket === "profile-pics") {
      const key: string = event.locals.user.icon.split("/").pop() as string;
      await deleteObject(bucket, key);
    }

    const objectUrl = await uploadObject(
      bucket,
      fileName,
      Buffer.from(fileBuffer)
    );

    if (bucket === "images" && type && type === "background") {
      let res = await db.insert(imagesTable).values({
        url: objectUrl,
        type: "background",
      });
    }

    console.log(`File uploaded to ${objectUrl}`);

    return new Response(JSON.stringify({ objectUrl }), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    console.error(error);
    return new Response(JSON.stringify({ error: "Error occured" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
}
