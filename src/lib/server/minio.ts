import { Client } from "minio";
const MINIO_SERVER_URL = process.env.MINIO_SERVER_URL;
const MINIO_ACCESS_KEY = process.env.MINIO_ACCESS_KEY;
const MINIO_SECRET_KEY = process.env.MINIO_SECRET_KEY;
const MINIO_CLIENT_URL = process.env.MINIO_CLIENT_URL;
const MINIO_USE_SSL = process.env.MINIO_USE_SSL;
const port = MINIO_CLIENT_URL?.split(":").pop(); // 9000

const minioClient = new Client({
  endPoint: MINIO_SERVER_URL ? MINIO_SERVER_URL : "localhost",
  port: port ? parseInt(port) : 9000,
  useSSL: MINIO_USE_SSL ? MINIO_USE_SSL === "true" : false,
  accessKey: MINIO_ACCESS_KEY as string,
  secretKey: MINIO_SECRET_KEY as string,
});

export default minioClient;
