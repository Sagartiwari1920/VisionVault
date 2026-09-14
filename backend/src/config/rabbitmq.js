const amqp = require('amqplib');

const QUEUE_NAME = 'document_processing';
let channel = null;

async function connectRabbitMQ() {
    try {
        // Connect to the RabbitMQ container
        const rabbitmqPassword=process.env.RABBITMQ_DEFAULT_PASS;
        const rabbitmqUser=process.env.RABBITMQ_DEFAULT_USER;
        const connection = await amqp.connect(`amqp://${rabbitmqUser}:${rabbitmqPassword}@localhost:5672`);
        channel = await connection.createChannel();
        
        // Ensure the queue exists before we try to send messages to it
        await channel.assertQueue(QUEUE_NAME, { durable: true });
        
        console.log(`[RabbitMQ] Connected and queue '${QUEUE_NAME}' is ready.`);
    } catch (error) {
        console.error('[RabbitMQ] Connection error:', error.message);
    }
}

// Function to send a message to the queue
async function publishToQueue(messageData) {
    if (!channel) {
        console.error('[RabbitMQ] Channel not initialized');
        return false;
    }
    
    const messageBuffer = Buffer.from(JSON.stringify(messageData));
    return channel.sendToQueue(QUEUE_NAME, messageBuffer, { persistent: true });
}

module.exports = { connectRabbitMQ, publishToQueue, QUEUE_NAME };