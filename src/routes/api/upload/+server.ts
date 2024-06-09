// src/routes/api/upload.js

import minioClient from "$lib/server/minio.js";
import type { RequestEvent } from "@sveltejs/kit";
import { generateId } from "lucia";
import { MINIO_URL } from "$env/static/private";

export async function POST(event: RequestEvent): Promise<Response> {
  try {
    const contentType = event.request.headers.get("content-type") ?? "";
    const fileExtension = contentType.split("/").pop();
    const fileName = `${generateId(25)}.${fileExtension}`;

    const fileBuffer = await event.request.arrayBuffer();
    const metaData = {
      "Content-Type": contentType,
    };

    const found: Boolean = await minioClient.bucketExists("profile-pics");

    if (!found) {
      await minioClient.makeBucket("profile-pics");
      // Set a bucket policy to allow public read access
      const bucketPolicy = {
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Principal: "*",
            Action: ["s3:GetBucketLocation", "s3:ListBucket"],
            Resource: `arn:aws:s3:::profile-pics`,
          },
          {
            Effect: "Allow",
            Principal: "*",
            Action: "s3:GetObject",
            Resource: `arn:aws:s3:::profile-pics/*`,
          },
        ],
      };
      await minioClient.setBucketPolicy(
        "profile-pics",
        JSON.stringify(bucketPolicy)
      );
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

    const publicUrl = `${MINIO_URL}/profile-pics/${fileName}`;

    return new Response(JSON.stringify({ publicUrl }), {
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
