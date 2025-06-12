# Shure Audio Control Agent

A specialized AI agent for controlling Shure audio equipment in broadcast production environments. This agent integrates with the Virtual Broadcast Production Assistant ecosystem and uses Azure OpenAI for natural language understanding.

## Features

- **Audio Channel Control**: Monitor and adjust audio channel settings
- **Gain Management**: Precise control of channel gain levels (-60dB to +60dB)
- **Mute Control**: Mute/unmute individual channels or groups
- **Phantom Power**: Control phantom power for condenser microphones
- **Preset Management**: Apply predefined configurations for different broadcast scenarios
- **Device Monitoring**: Real-time status monitoring of Shure equipment
- **Natural Language Interface**: Control audio equipment using conversational commands

## Supported Operations

### Channel Status
- Get status of individual channels or all channels
- Monitor gain levels, mute status, and phantom power state
- View EQ settings and channel configurations

### Audio Control
- Adjust channel gain with precise dB control
- Mute/unmute channels individually or in groups
- Enable/disable phantom power for condenser mics

### Presets
- **broadcast_news**: Optimized for news broadcast (channels 1-2 active)
- **live_sports**: Optimized for live sports commentary (channels 1-4 active)
- **reset_all**: Reset all channels to default settings

## Requirements

- Python 3.8+
- Azure OpenAI account with GPT-4 deployment
- Shure audio equipment (SCM820 or compatible)
- Network access to Shure device

## Installation

### 1. Create & Activate Virtual Environment

```bash
python -m venv .venv
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

**Windows CMD:**
```bash
.venv\Scripts\activate.bat
```

**Windows PowerShell:**
```bash
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

Copy the environment example file and configure your settings:

```bash
cp .env-example .env
```

Edit `.env` with your configuration:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Shure Audio Device Configuration
SHURE_DEVICE_IP=192.168.1.100
SHURE_DEVICE_PORT=8080
```

## Running the Agent

### Start the Agent Server

```bash
python -m shure-audio-agent
```

**With custom host/port:**
```bash
python -m shure-audio-agent --host 0.0.0.0 --port 10003
```

**With debug logging:**
```bash
python -m shure-audio-agent --log-level DEBUG
```

### Agent Card

Once running, you can view the agent card at:
```
http://localhost:10003/.well-known/agent.json
```

Example agent card:
```json
{
  "name": "Shure Audio Control Agent",
  "description": "Controls Shure audio equipment for broadcast production environments.",
  "version": "1.0.0",
  "url": "http://localhost:10003/",
  "capabilities": {
    "streaming": true
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    {
      "id": "get_channel_status",
      "name": "Get Channel Status",
      "description": "Get the current status of audio channels including gain, mute, and phantom power settings.",
      "examples": [
        "What's the status of channel 1?",
        "Show me all channel levels",
        "Are any channels muted?"
      ]
    }
  ]
}
```

## Usage Examples

### Basic Channel Control

```
User: "What's the status of channel 1?"
Agent: "Channel 1 is currently unmuted with a gain of -12.0 dB and phantom power enabled."

User: "Mute channel 3"
Agent: "Successfully muted channel 3."

User: "Set channel 2 gain to -15 dB"
Agent: "Successfully set channel 2 gain to -15.0 dB."
```

### Phantom Power Control

```
User: "Enable phantom power on channel 1"
Agent: "Successfully enabled phantom power for channel 1."

User: "Which channels have phantom power enabled?"
Agent: "Phantom power is currently enabled on channels 1, 2, and 4."
```

### Preset Management

```
User: "Apply broadcast news preset"
Agent: "Successfully applied preset: broadcast_news. Channels 1-2 are configured for news broadcast with -12 dB gain and phantom power enabled."

User: "Set up for live sports commentary"
Agent: "Successfully applied preset: live_sports. Channels 1-4 are configured for sports commentary."
```

### Device Information

```
User: "What's the device status?"
Agent: "Connected to Shure SCM820, firmware version 2.4.1. Device is running normally with 8 channels available."
```

## Integration with Orchestrator

This agent can be controlled by the main orchestrator agent. Add it to your orchestrator configuration:

```python
# In orchestrator configuration
AUDIO_AGENT_URL = "http://localhost:10003"
```

## Development

### Project Structure

```
shure-audio-control/
├── requirements.txt          # Python dependencies
├── .env-example             # Environment configuration template
├── README.md               # This file
└── shure-audio-agent/      # Main agent package
    ├── __init__.py         # Package initialization
    ├── __main__.py         # Entry point and server setup
    ├── agent.py            # Agent definition and Azure OpenAI integration
    ├── agent_executor.py   # ADK executor implementation
    └── audio_control.py    # Shure device control logic (placeholder)
```

### Audio Control Implementation

The current implementation includes placeholder functions for Shure device control. To integrate with real hardware:

1. Replace placeholder functions in `audio_control.py` with actual Shure API calls
2. Implement device-specific protocols (HTTP, WebSocket, or proprietary)
3. Add error handling for network connectivity issues
4. Implement device discovery and authentication

### Testing

Test the agent endpoints:

```bash
# Health check
curl http://localhost:10003/health

# Agent card
curl http://localhost:10003/.well-known/agent.json

# Task execution (requires A2A protocol)
# Use the orchestrator or A2A client for testing
```

## Architecture

- **Framework**: Google Agent Development Kit (ADK) + A2A SDK
- **LLM**: Azure OpenAI GPT-4
- **Communication**: A2A (Agent-to-Agent) protocol
- **Audio Control**: Placeholder implementation for Shure devices
- **Server**: FastAPI with Uvicorn

## Security Considerations

- Secure Azure OpenAI API keys in environment variables
- Implement network security for Shure device communication
- Consider authentication for agent endpoints in production
- Validate all audio control parameters to prevent equipment damage

## Troubleshooting

### Common Issues

1. **Azure OpenAI Connection Failed**
   - Verify API key and endpoint configuration
   - Check network connectivity to Azure
   - Ensure deployment name matches your Azure OpenAI model

2. **Shure Device Not Found**
   - Verify device IP address and port
   - Check network connectivity to audio equipment
   - Ensure device is powered on and network-enabled

3. **Agent Not Starting**
   - Check all required environment variables are set
   - Verify Python dependencies are installed
   - Review logs for specific error messages

### Logs

Enable debug logging for troubleshooting:
```bash
python -m shure-audio-agent --log-level DEBUG
```

## Contributing

Follow the project's contribution guidelines. When adding new features:

1. Extend the audio control logic in `audio_control.py`
2. Add corresponding tools in `agent.py`
3. Update the agent skills in `__main__.py`
4. Add usage examples to this README

## License

This project follows the same license as the parent Virtual Broadcast Production Assistant project. 