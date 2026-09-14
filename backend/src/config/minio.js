const Minio = require('minio');
require('dotenv').config(); // Ensure your .env variables are loaded

// 1. Initialize the MinIO Client
const minioClient = new Minio.Client({
  endPoint: 'localhost',
  port: 9000,           // The API port exposed in docker-compose.yml
  useSSL: false,        // Set to false for local development
  accessKey: process.env.MINIO_ROOT_USER || 'admin', 
  secretKey: process.env.MINIO_ROOT_PASSWORD || 'password123',
});

// Define the bucket where all RAG documents will be stored
const BUCKET_NAME = 'rag-documents';

// 2. Helper function to ensure the bucket exists on server startup
async function initializeMinio() {
  try {
    const exists = await minioClient.bucketExists(BUCKET_NAME);
    
    if (!exists) {
      // Create the bucket in the default region if it doesn't exist
      await minioClient.makeBucket(BUCKET_NAME, 'us-east-1');
      console.log(`[MinIO] Bucket '${BUCKET_NAME}' created successfully.`);
    } else {
      console.log(`[MinIO] Bucket '${BUCKET_NAME}' is ready.`);
    }

    // Optional: Set a bucket policy to allow the frontend to read files via presigned URLs
    const policy = {
      Version: '2012-10-17',
      Statement: [
        {
          Effect: 'Allow',
          Principal: '*',
          Action: ['s3:GetObject'],
          Resource: [`arn:aws:s3:::${BUCKET_NAME}/*`],
        },
      ],
    };
    await minioClient.setBucketPolicy(BUCKET_NAME, JSON.stringify(policy));

  } catch (error) {
    console.error('[MinIO] Initialization error:', error.message);
  }
}

// Export the client and the init function so other parts of your app can use them
module.exports = { 
  minioClient, 
  BUCKET_NAME, 
  initializeMinio 
};