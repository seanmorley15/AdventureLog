import { Client } from "minio";
import { MINIO_URL } from "$env/static/private";
import { MINIO_ACCESS_KEY } from "$env/static/private";
import { MINIO_SECRET_KEY } from "$env/static/private";
import { MINIO_ENDPOINT } from "$env/static/private";
const port = MINIO_URL?.split(":").pop(); // 9000

const minioClient = new Client({
  endPoint: MINIO_ENDPOINT ? MINIO_ENDPOINT : "localhost",
  port: port ? parseInt(port) : 9000,
  useSSL: false,
  accessKey: MINIO_ACCESS_KEY,
  secretKey: MINIO_SECRET_KEY,
});

export default minioClient;
