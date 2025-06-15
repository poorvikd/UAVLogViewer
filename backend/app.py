from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message')
        file_info = data.get('fileInfo', {})
        
        # Log the received message
        logger.info(f"Received chat message: {message}")
        
        # Log file information in a structured way
        logger.info("File Information:")
        logger.info(f"  Name: {file_info.get('name')}")
        logger.info(f"  Type: {file_info.get('type')}")
        logger.info(f"  Timestamp: {file_info.get('timestamp')}")
        print(file_info.get('messages')['GPS[0]']['Alt'])
        # Log metadata if present
        if metadata := file_info.get('metadata'):
            logger.info("Metadata:")
            logger.info(json.dumps(metadata, indent=2))
        
        # Log message statistics if present
        if stats := file_info.get('statistics'):
            logger.info("Message Statistics:")
            for msg_type, stat in stats.items():
                logger.info(f"  {msg_type}:")
                logger.info(f"    Count: {stat.get('count')}")
                logger.info(f"    Time Span: {stat.get('timeSpan')}ms")
                logger.info(f"    Fields: {', '.join(stat.get('fields', []))}")
        
        # Log message types and counts
        if messages := file_info.get('messages'):
            logger.info("Message Types:")
            for msg_type, msgs in messages.items():
                logger.info(f"  {msg_type}: {len(msgs)} messages")
        
        # Here you can add any processing logic for the message
        # For now, we'll just echo back a simple response with some data summary
        response = {
            "status": "success",
            "message": f"Received your message about {file_info.get('name')}. Found {sum(len(msgs) for msgs in file_info.get('messages', {}).values())} total messages across {len(file_info.get('messages', {}))} message types.",
            "timestamp": datetime.now().isoformat(),
            "fileInfo": {
                "name": file_info.get('name'),
                "type": file_info.get('type'),
                "messageCount": sum(len(msgs) for msgs in file_info.get('messages', {}).values()),
                "messageTypes": list(file_info.get('messages', {}).keys())
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True) 