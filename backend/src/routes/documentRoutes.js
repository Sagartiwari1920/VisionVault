const express = require('express');
const multer = require('multer');

const {uploadDocument} = require('../controllers/documentController');

const documentRouter = express.Router();

const upload = multer({
    storage: multer.memoryStorage()
});

documentRouter.post(
    '/upload',
    upload.single('file'),
    uploadDocument
);

module.exports = { documentRouter };