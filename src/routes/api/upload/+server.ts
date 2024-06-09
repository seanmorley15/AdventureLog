// src/routes/api/upload.js

import minioClient from "$lib/server/minio.js";
import type { RequestEvent } from "@sveltejs/kit";
import { generateId } from "lucia";

export async function POST(event: RequestEvent): Promise<Response> {
  try {
    const contentType = event.request.headers.get("content-type") ?? "";
    const fileExtension = contentType.split("/").pop();
    const fileName = `${generateId(25)}.${fileExtension}`;

    console.log(fileName);

    const fileBuffer = await event.request.arrayBuffer();
    const metaData = {
      "Content-Type": contentType,
    };

    const found: Boolean = await minioClient.bucketExists("profile-pics");

    if (!found) {
      await minioClient.makeBucket("profile-pics");
    }

    await minioClient.putObject(
      "profile-pics",
      fileName,
      Buffer.from(fileBuffer)
    );

    const fileUrl = await minioClient.presignedGetObject(
      "profile-pics",
      fileName
    );

    console.log(fileUrl);

    return new Response(JSON.stringify({ fileUrl }), {
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
