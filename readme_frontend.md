# ChatWidget.vue Frontend: Code Explanation & Usage

## Overview
This component implements the chat interface for the UAVLogViewer application, allowing users to interact with the backend AI system for UAV log analysis. It provides a modern, responsive chat UI, handles user input, displays messages, and communicates with the backend API.

---

## Component Structure
- **Template**: Defines the chat UI, including the header, message display area, and input box.
- **Script**: Contains the logic for message handling, API communication, state management, and UI behavior.
- **Style**: Provides scoped CSS for a modern, dark-themed chat experience.

---

## Template Breakdown
- `<div class="chat-widget">` — Main container, toggles minimized state.
- **Header**: Clickable bar to minimize/maximize the chat.
- **Messages Area**: Scrollable list displaying user, bot, and system messages with timestamps.
- **Input Area**: Text input and send button for user queries.

---

## Script Logic
- **State Management**: Uses a shared `store` (imported from `Globals.js`) to access file and log data.
- **Data Properties**:
  - `messages`: Array of chat messages (user, bot, system).
  - `newMessage`: Current input value.
  - `isMinimized`: Whether the chat is minimized.
  - `apiUrl`: Backend endpoint for chat queries.
- **Methods**:
  - `sendMessage()`: Handles sending user input to the backend, updating the chat, and error handling.
  - `generateStatistics()`: Computes basic stats for each message type (count, timestamps, fields) to send as context.
  - `getUniqueFields()`: Helper to extract unique field names from messages.
  - `formatTime()`: Formats timestamps for display.
  - `scrollToBottom()`: Ensures the latest message is visible.
  - `toggleMinimize()`: Toggles the minimized state of the chat.
- **API Integration**:
  - Sends a POST request to `/api/chat` with the user message and file/log context.
  - Handles both success and error responses, updating the chat accordingly.
- **Reactivity**:
  - Watches for file changes in the store to notify the user when a new file is loaded.

---

## Data Flow
1. **User types a message** and presses Enter or clicks Send.
2. **Message is added** to the chat as a user message.
3. **API request** is sent to the backend with the message and current file/log context.
4. **Bot response** (or error) is added to the chat upon receiving the backend's reply.
5. **Chat scrolls** to the latest message automatically.

---

## Customization & Extensibility
- **Styling**: Easily adjustable via the `<style scoped>` section for colors, layout, and responsiveness.
- **API URL**: Change `apiUrl` if the backend endpoint changes.
- **State Integration**: Uses a global store for file/log context; can be extended for more context or user/session info.
- **Message Types**: Supports user, bot, and system messages; can be extended for more types or richer formatting.

---

## Connecting to the Backend
- Expects the backend to be running at `http://127.0.0.1:5000/api/chat` (configurable).
- Sends a JSON payload with:
  - `message`: User's question.
  - `fileInfo`: File name, type, metadata, parsed messages, and statistics.
- Handles backend responses, displaying the answer or an error message.

---

## Example Usage
- Load a UAV log file in the app.
- Open the chat widget and ask questions like "What was the max altitude?" or "Were there any GPS dropouts?"
- The chat will display both your question and the AI's answer, with timestamps.

---

## File Location
- `src/components/ChatWidget.vue`: Main chat component.
- `src/components/Globals.js`: Shared state for file/log context.

---

## Further Improvements
- Add support for file uploads or drag-and-drop.
- Implement message streaming for real-time bot responses.
- Add user avatars or richer message formatting.
- Integrate with authentication/session management if needed. 