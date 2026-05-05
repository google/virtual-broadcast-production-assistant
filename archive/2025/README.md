# Virtual Production Assistant

A collaborative reference to using AI Agents to assist with the congnitive load
of live broadcast (News, sport etc). As part of the
[2025 IBC Accelerators program](https://show.ibc.org/2025-accelerator-media-innovation-programme)
and specifically the [AI Agents in Live Production](https://show.ibc.org/accelerator-project-ai-assistance-agents-live-production)
 where we are exploring how specialist agents can proactively look for errors and
help with both the creation and running of a program through automation tools.

## Agent of Agents

One key aim for this repo is to explore, develop and test the notion of a production
agent that can hand off to other agents specific specialist tasks and to allow
those agents to inform the Master Control room agent.

The UI will be both visual and through voice, each interface is good at specific tasks. It is unlikely
that a director will have time to type instructions, so they are likely to input
via voice, however having an agent list 28 news items that currently have issues or aren't quite
in a ready state for some reason equally is not going to be efficient.

## Getting Started

To get started with development, please see the README in the `orchestrator` directory: [orchestrator/README.md](./orchestrator/README.md).

## Agents

This repository contains a number of specialized agents that can be orchestrated to assist with broadcast production. Here is a summary of the agents currently available:

*   **BBC Newsround Graphics**: Controls on-screen graphics such as name straps, locators, headlines, and info tabs.
*   **Control Room Assistant**: An older proof-of-concept that provides a multimodal chat experience with a web UI and a websocket backend. It does not follow the current agentic architecture.
*   **Cuez Rundown**: An agent that helps with the Cuez rundown and can list episodes in a project.
*   **Cuez Stubzy**: An agent for interacting with the CUEZ rundown system and automator.
*   **ITN Posture**: Provides "Stack Checking Services" for graphics, including checking sequence orders, factual information, and spelling.
*   **Shure Audio Agent**: Manages Shure audio device settings, user presets, and microphone channel coverage.
*   **Sofie Agent**: A simple agent that uses Google Search to answer questions.
*   **TX Agent**: A two-part system with a "TX Worker" that logs live broadcast content and a "TX Agent" that provides a conversational interface to that content.
*   **Orchestrator**: The central agent that orchestrates the other agents.

## NOTE on repo governance

Each domain area or component should have a top level directory. This could include full working code or
examples of how it has been implemented else where.

There is a top level **build** directory which is where any Google Cloud specific deployment configs go.
In addition there is an **infrastructure** directory for terraform to reside for deployment of the project
to Google Cloud. **Both these directories** should mirror the top level directories in structure when required.

## Instructions for running the POC code

The `control-room-assistant` directory holds the original POC code, this is here for record and maybe
archived. It doesn't follow the agentic architecture we are now adopting.

For running locally see READMEs in control-room-assistant/client and backend/websocket-server folders.

Teraform is set up for running on Google Cloud.

## Acknowledgements

Some of the backend websocket code has been inspired by Heiko's work on

<https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide>

This is not an officially supported Google product. This project is not
eligible for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).
