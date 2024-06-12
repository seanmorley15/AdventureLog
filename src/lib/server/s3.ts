import {
  CreateBucketCommand,
  DeleteObjectCommand,
  HeadBucketCommand,
  PutBucketPolicyCommand,
  PutObjectCommand,
  S3Client,
  type S3ClientConfig,
} from "@aws-sdk/client-s3";
import { env } from "$env/dynamic/private";
console.log(env.AWS_ACCESS_KEY_ID as string);

const s3Config: S3ClientConfig = {
  region: (env.AWS_REGION as string) || "us-east-1",
  credentials: {
    accessKeyId: env.AWS_ACCESS_KEY_ID as string,
    secretAccessKey: env.AWS_SECRET_ACCESS_KEY as string,
  },
  endpoint: env.AWS_S3_ENDPOINT, // Add the endpoint
  forcePathStyle: true,
};

export const s3Client = new S3Client(s3Config);

export const ensureBucketExists = async (bucketName: string): Promise<void> => {
  const headBucketCommand = new HeadBucketCommand({ Bucket: bucketName });

  try {
    await s3Client.send(headBucketCommand);
    console.log(`Bucket ${bucketName} already exists.`);
  } catch (error: any) {
    console.log(error);
    if (error.$metadata.httpStatusCode === 404) {
      console.log(`Bucket ${bucketName} does not exist. Creating...`);
      const createBucketCommand = new CreateBucketCommand({
        Bucket: bucketName,
      });
      await s3Client.send(createBucketCommand);

      // Set a bucket policy to allow public read access
      const bucketPolicy = {
        Version: "2012-10-17",
        Statement: [
          {
            Effect: "Allow",
            Principal: "*", // This allows anyone (public)
            Action: ["s3:GetBucketLocation", "s3:ListBucket"],
            Resource: `arn:aws:s3:::${bucketName}`,
          },
          {
            Effect: "Allow",
            Principal: "*", // This allows anyone (public)
            Action: "s3:GetObject",
            Resource: `arn:aws:s3:::${bucketName}/*`,
          },
        ],
      };

      const putBucketPolicyCommand = new PutBucketPolicyCommand({
        Bucket: bucketName,
        Policy: JSON.stringify(bucketPolicy),
      });
      await s3Client.send(putBucketPolicyCommand);

      console.log(
        `Bucket ${bucketName} created and public read access policy set.`
      );
    } else {
      throw error; // Rethrow other errors
    }
  }
};

export const uploadObject = async (
  bucketName: string,
  fileName: string,
  fileBuffer: Buffer
): Promise<string> => {
  const putObjectCommand = new PutObjectCommand({
    Bucket: bucketName,
    Key: fileName,
    Body: fileBuffer,
  });

  try {
    await s3Client.send(putObjectCommand);

    let objectUrl: string;
    objectUrl = getObjectUrl(bucketName, fileName);
    return objectUrl;
  } catch (error) {
    console.error(
      `Error uploading file ${fileName} to bucket ${bucketName}:`,
      error
    );
    throw error;
  }
};

export const deleteObject = async (bucketName: string, fileName: string) => {
  const deleteObjectCommand = new DeleteObjectCommand({
    Bucket: bucketName,
    Key: fileName,
  });

  try {
    await s3Client.send(deleteObjectCommand);
  } catch (error) {
    console.error(
      `Error uploading file ${fileName} to bucket ${bucketName}:`,
      error
    );
    throw error;
  }
};

export const getObjectUrl = (bucketName: string, fileName: string): string => {
  let objectUrl: string;
  let endpoint = env.AWS_S3_ENDPOINT as string;

  if (endpoint.includes("amazonaws.com")) {
    // Amazon S3
    objectUrl = `https://${bucketName}.s3.${env.AWS_REGION}.amazonaws.com/${fileName}`;
  } else if (endpoint.includes("storage.googleapis.com")) {
    // Google Cloud Storage
    objectUrl = `https://storage.googleapis.com/${bucketName}/${fileName}`;
  } else if (endpoint.includes("digitaloceanspaces.com")) {
    // DigitalOcean Spaces
    objectUrl = `https://${bucketName}.${endpoint}/${fileName}`;
  } else if (endpoint.includes("supabase.co")) {
    // Supabase Storage
    endpoint = endpoint.replace("s3", "object/public"); // Remove the version
    console.log(endpoint);
    objectUrl = `${endpoint}/${bucketName}/${fileName}`;
  } else {
    // Default fallback
    objectUrl = `${endpoint}/${bucketName}/${fileName}`;
  }

  return objectUrl;
};
