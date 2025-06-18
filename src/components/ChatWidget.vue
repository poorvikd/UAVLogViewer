<template>
    <div class="chat-widget" :class="{ minimized: isMinimized }">
        <div class="chat-header" @click="toggleMinimize">
            <span>Chat</span>
            <i :class="['fas', isMinimized ? 'fa-chevron-up' : 'fa-chevron-down']"></i>
        </div>
        <div v-show="!isMinimized" class="chat-content">
            <div class="messages" ref="messagesContainer">
                <div v-for="(message, index) in messages" :key="index" :class="['message', message.type]">
                    <div class="message-content">
                        <span class="message-text">{{ message.text }}</span>
                        <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                    </div>
                </div>
            </div>
            <div class="input-area">
                <input
                    v-model="newMessage"
                    @keyup.enter="sendMessage"
                    placeholder="Type a message..."
                    type="text"
                />
                <button @click="sendMessage" class="send-button">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import { store } from './Globals'
import axios from 'axios'

export default {
    name: 'ChatWidget',
    data () {
        return {
            state: store,
            messages: [],
            newMessage: '',
            isMinimized: false,
            apiUrl: 'http://127.0.0.1:5000/api/chat'
        }
    },
    methods: {
        async sendMessage () {
            if (this.newMessage.trim() && this.state.file) {
                // Store the message content and clear input immediately
                const messageText = this.newMessage
                this.newMessage = ''
                
                // Add user message to chat
                const userMessage = {
                    text: messageText,
                    type: 'user',
                    timestamp: new Date()
                }
                this.messages.push(userMessage)
                
                // Prepare message for API with complete parsed data
                const messageData = {
                    message: messageText,
                    fileInfo: {
                        name: this.state.file,
                        type: this.state.logType,
                        timestamp: new Date().toISOString(),
                        metadata: this.state.metadata || {},
                        messages: this.state.messages || {},
                        statistics: this.generateStatistics()
                    }
                }
                try {
                    // Send message to backend
                    const response = await axios.post(this.apiUrl, messageData)
                    // Add bot response to chat
                    if (response.data.status === 'success') {
                        this.messages.push({
                            text: response.data.message,
                            type: 'bot',
                            timestamp: new Date(response.data.timestamp)
                        })
                    } else {
                        throw new Error(response.data.message)
                    }
                } catch (error) {
                    console.error('Error sending message:', error)
                    // Add error message to chat
                    this.messages.push({
                        text: 'Sorry, there was an error processing your message.',
                        type: 'bot',
                        timestamp: new Date()
                    })
                }

                // Scroll to bottom after response
                this.$nextTick(() => {
                    this.scrollToBottom()
                })
            }
        },
        generateStatistics () {
            if (!this.state.messages) return {}

            const stats = {}
            for (const [type, messages] of Object.entries(this.state.messages)) {
                if (messages && messages.length > 0) {
                    stats[type] = {
                        count: messages.length,
                        firstTimestamp: messages[0]?.time_boot_ms,
                        lastTimestamp: messages[messages.length - 1]?.time_boot_ms,
                        timeSpan: messages[messages.length - 1]?.time_boot_ms - messages[0]?.time_boot_ms,
                        fields: this.getUniqueFields(messages)
                    }
                }
            }
            return stats
        },
        getUniqueFields (messages) {
            if (!messages || messages.length === 0) return []
            const fields = new Set()
            messages.forEach(msg => {
                Object.keys(msg).forEach(key => fields.add(key))
            })
            return Array.from(fields)
        },
        formatTime (date) {
            return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        },
        scrollToBottom () {
            const container = this.$refs.messagesContainer
            container.scrollTop = container.scrollHeight
        },
        toggleMinimize () {
            this.isMinimized = !this.isMinimized
        }
    },
    watch: {
        'state.file' (newFile) {
            if (newFile) {
                this.messages.push({
                    text: `File "${newFile}" loaded successfully`,
                    type: 'system',
                    timestamp: new Date()
                })
            }
        }
    }
}
</script>

<style scoped>
.chat-widget {
    position: relative;
    width: 100%;
    background: rgb(29, 36, 52);
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    margin: 10px 0;
    display: flex;
    flex-direction: column;
    max-height: 400px;
}

.chat-header {
    padding: 10px 15px;
    background: rgb(37, 47, 71);
    border-radius: 8px 8px 0 0;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: white;
}

.chat-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
}

.messages {
    flex: 1;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: 300px;
}

.message {
    max-width: 85%;
    padding: 8px 12px;
    border-radius: 12px;
    margin: 2px 0;
}

.message.user {
    align-self: flex-end;
    background: rgb(37, 47, 71);
    color: white;
}

.message.bot {
    align-self: flex-start;
    background: rgb(45, 55, 79);
    color: white;
}

.message-content {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.message-time {
    font-size: 0.7em;
    opacity: 0.7;
    align-self: flex-end;
}

.input-area {
    display: flex;
    padding: 10px;
    gap: 10px;
    background: rgb(37, 47, 71);
    border-radius: 0 0 8px 8px;
    align-items: center;
}

.input-area input {
    flex: 1;
    padding: 8px 12px;
    border: none;
    border-radius: 4px;
    background: rgb(45, 55, 79);
    color: white;
    font-size: 14px;
}

.input-area input:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
}

.send-button {
    background: rgb(45, 55, 79);
    border: none;
    border-radius: 4px;
    color: white;
    padding: 8px 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
}

.send-button:hover {
    background: rgb(55, 65, 89);
}

.send-button:active {
    background: rgb(35, 45, 69);
}

.minimized .chat-content {
    display: none;
}

.messages::-webkit-scrollbar {
    width: 6px;
}

.messages::-webkit-scrollbar-track {
    background: rgb(37, 47, 71);
    border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb {
    background: rgb(55, 65, 89);
    border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
    background: rgb(65, 75, 99);
}
</style>
