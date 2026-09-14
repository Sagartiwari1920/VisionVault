const handleChat = async (req, res) => {
    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: 'Query is required' });
    }
 
    try {
        // 1. Forward the query to the Python FastAPI microservice
        const pythonResponse = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        if (!pythonResponse.ok) {
            throw new Error(`Python API responded with status: ${pythonResponse.status}`);
        }

        // 2. Extract the LLM response and retrieved text chunks
        const data = await pythonResponse.json();

        // 3. Send the final data back to the React frontend
        res.json({
            text: data.response,
            context: data.context
        });

    } catch (error) {
        console.error('[Chat Proxy Error]:', error);
        res.status(500).json({ error: 'Failed to process chat query via Python worker' });
    }
};

module.exports = { handleChat };  