// src/routes/api/upload.js

import { deleteObject, ensureBucketExists, uploadObject } from "$lib/server/s3";
import type { RequestEvent } from "@sveltejs/kit";
import { generateId } from "lucia";

export async function POST(event: RequestEvent): Promise<Response> {
  try {
    const contentType = event.request.headers.get("content-type") ?? "";
    const fileExtension = contentType.split("/").pop();
    const fileName = `${generateId(75)}.${fileExtension}`;
    const bucket = event.request.headers.get("bucket") as string;

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

    // check if the file is an image
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

    if (event.locals.user?.icon) {
      const key: string = event.locals.user.icon.split("/").pop() as string;
      await deleteObject(bucket, key);
    }

    const objectUrl = await uploadObject(
      bucket,
      fileName,
      Buffer.from(fileBuffer)
    );

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
