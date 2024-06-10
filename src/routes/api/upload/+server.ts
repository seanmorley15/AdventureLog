// src/routes/api/upload.js

import { ensureBucketExists, s3Client, uploadObject } from "$lib/server/s3";
import { HeadBucketCommand } from "@aws-sdk/client-s3";
import type { RequestEvent } from "@sveltejs/kit";
import { generateId } from "lucia";

export async function POST(event: RequestEvent): Promise<Response> {
  try {
    const contentType = event.request.headers.get("content-type") ?? "";
    const fileExtension = contentType.split("/").pop();
    const fileName = `${generateId(25)}.${fileExtension}`;

    if (!fileExtension || !fileName) {
      return new Response(JSON.stringify({ error: "Invalid file type" }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      });
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

    await ensureBucketExists("profile-pics");

    const objectUrl = await uploadObject(
      "profile-pics",
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
