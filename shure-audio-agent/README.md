# Shure Audio Agent

A specialized AI agent for managing Shure Audio device settings, user presets, and microphone channel coverage in broadcast production environments. This agent is designed to work within the Agent-to-Agent (A2A) framework, enabling seamless integration with other broadcast production agents.

## Overview

The Shure Audio Agent provides intelligent automation for audio device management in live broadcast scenarios. It can handle device status monitoring, user preset management, microphone channel coverage configuration, EQ settings, auto positioning, and lobe steering - all critical functions for maintaining optimal audio quality during live productions.

## Features

- **Device Status Management**: Real-time monitoring of Shure Audio device states
- **User Preset Management**: Load and manage user presets for different production scenarios
- **Microphone Channel Coverage**: Configure microphone coverage areas for optimal audio capture
- **EQ Settings**: Fine-tune EQ parameters for different audio environments
- **Auto Positioning**: Automated positioning features for dynamic audio optimization
- **Lobe Steering**: Control directional audio through lobe steering technology
- **A2A Framework Integration**: Full compatibility with the Agent-to-Agent communication protocol

## Architecture

The agent is built using the Google Agent Development Kit (ADK) and follows the A2A framework for multi-agent collaboration:

```
shure-audio-agent/
├── agent.py                 # Core agent logic using ADK LlmAgent
├── task_manager.py          # A2A task manager implementing AgentExecutor
├── __main__.py             # Entry point with agent card and skill definitions
├── azure_logic_app_client.py # Client for Azure Logic App integration
├── cache/                  # Caching layer for performance optimization
├── tool/                   # Tool implementations for various audio operations
└── requirements.txt        # Python dependencies
```

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export AZURE_LOGIC_APP_WEBHOOK_URL="your_azure_logic_app_webhook_url"
export A2A_HOST="localhost"  # Optional, defaults to localhost
export A2A_PORT="8080"       # Optional, defaults to 8080
```

## Usage

### Starting the A2A Agent

```bash
python -m shure_audio_agent
```

This starts the A2A server on the configured host and port (default: localhost:8080).

### Agent Capabilities

The agent supports the following operations:

1. **Get Device Status**: Retrieve current device state and configuration
2. **Load User Preset**: Load a specific user preset by name for different production scenarios
3. **Set Microphone Coverage**: Configure microphone channel coverage areas
4. **Set EQ Settings**: Configure EQ parameters for optimal audio quality
5. **Start Auto Positioning**: Initiate automatic positioning for dynamic audio optimization
6. **Steer Lobe**: Control lobe steering for directional audio capture

## Integration with Broadcast Production

This agent is designed to work seamlessly within the Virtual Broadcast Production Assistant ecosystem:

- **Multi-Agent Collaboration**: Can be discovered and used by other A2A-compatible agents
- **Production Workflow Integration**: Supports common broadcast production scenarios
- **Real-time Audio Management**: Provides immediate response for live production needs
- **Error Prevention**: Proactively monitors and manages audio device states

## Agent Skills

The agent declares the following skill:
- **ID**: ShureAudioAgent
- **Name**: ShureAudioAgent
- **Description**: Agent to manage Shure Audio device settings, user presets, and microphone channel coverage via GraphQL
- **Tags**: audio, shure, microphone, presets, eq, positioning, broadcast, production

## Azure Logic App Integration

The agent communicates with Shure Audio devices through an Azure Logic App that handles GraphQL queries and mutations. The Logic App acts as a bridge between the agent and the on-premise Shure Audio endpoint, providing:

- Secure communication with on-premise audio systems
- GraphQL query and mutation handling
- Error handling and retry logic
- Caching for improved performance

## Error Handling

The agent includes comprehensive error handling:
- Network errors are caught and reported
- Invalid tool arguments are validated
- Task failures are properly communicated back to the A2A framework
- Graceful degradation when services are unavailable

## Development

To extend the agent with new capabilities:

1. Add new tools to the `tool/` directory
2. Update the agent's instruction in `agent.py`
3. Add new examples to the skill definition in `__main__.py`
4. Update the agent card description if needed

## Testing

The agent can be tested using the A2A framework's testing utilities:

```bash
# Test agent discovery
python -m a2a.client discover

# Test agent capabilities
python -m a2a.client execute --agent ShureAudioAgent --query "Get device status"
```

## Troubleshooting

- Ensure all environment variables are properly set
- Check that the Azure Logic App webhook URL is accessible
- Verify that the A2A framework dependencies are installed
- Check the console output for any error messages during startup

## Contributing

This agent is part of the Google Virtual Broadcast Production Assistant project. Contributions are welcome! Please follow the project's contribution guidelines and ensure all changes maintain A2A framework compatibility.

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details. 