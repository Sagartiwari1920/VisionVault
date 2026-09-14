const { minioClient, BUCKET_NAME } = require('../config/minio');
const {publishToQueue}=require("../config/rabbitmq")

const uploadDocument = async (req, res) => {
    try {
      // console.log("access to upload document");
        if (!req.file) {
            return res.status(400).json({
                error: 'No file provided'
            });
        }

        const objectName =
            `${Date.now()}-${req.file.originalname.replace(/\s+/g, '_')}`;

        //upload file to minio
        await minioClient.putObject(
            BUCKET_NAME,
            objectName,
            req.file.buffer,
            req.file.size,
            {
                'Content-Type': req.file.mimetype
            }
        );
       //put the message into rabbitmq (just after uploading the file )
       //if the bigger file comes our backend will immediatly respond to the frontend nut our (rabbitmq+worker) will keep uploading the file in background
       //that is what we call as asynchronous process
        const taskPayload = {
            documentId: objectName,
            bucketName: BUCKET_NAME,
            status: 'Processing'
        };
        await publishToQueue(taskPayload);
        res.json({
            message: 'Upload successful',
            documentId: objectName
        });

    } catch (error) {
        console.error('[Upload Error]:', error);

        res.status(500).json({
            error: 'Failed to upload document'
        });
    }
};

module.exports = { uploadDocument };