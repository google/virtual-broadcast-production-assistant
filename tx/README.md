# AI TX Agent for Live Broadcast: Conceptual Overview

This document outlines a conceptual framework for an AI-powered Transmission (TX) Agent system designed to assist live broadcast production teams, particularly directors and editors, by providing real-time information about what has already occurred in the broadcast.

## Core Concept

The system comprises two main components:

1. **TX Worker (Content Logger):** This automated component continuously monitors the live broadcast feed, processes its content, and logs relevant information into a structured database. Each piece of information (e.g., a transcript snippet, a visual scene description) is stored with a precise timestamp from the original broadcast.
2. **TX Agent (Conversational Interface):** This AI agent allows production team members (and potentially other automated systems) to query the logged information using natural language. It retrieves relevant data based on time and content, then uses an LLM to synthesize answers.

## 1. TX Worker: Real-time Content Ingestion and Logging

The TX Worker is the backbone of the system, responsible for capturing and understanding the broadcast content as it happens. Its primary role is to ensure all analyzed data is accurately timestamped for later synchronization and retrieval.

**Responsibilities:**

* **Ingest Live Feed:** Securely tap into the live broadcast output (SDI, NDI, IP stream).
* **Timestamping:** Assign a precise UTC timestamp and broadcast timecode to every segment of data processed. This is crucial for synchronization.
* **Content Analysis (Multi-modal):**
  * **Audio Transcription:** Convert spoken words into text (e.g., using Google Cloud Speech-to-Text with Chirp for streaming and diarization). Results are logged with their corresponding timestamps.
  * **Video Scene/Content Description:** Identify key visual elements, scenes, actions, on-screen graphics (e.g., using Google Cloud Video AI with Gemini models). Results are logged with their corresponding timestamps.
  * **Video Frame Extraction:** Periodically save key video frames, linked by timestamp.
  * **Metadata Extraction:** Log timecodes, programme segment information, and any other available broadcast metadata, all associated with timestamps.
* **Data Structuring & Logging:** Organize the extracted information into distinct, timestamped log entries in the database. For instance, a transcript snippet and a visual scene description for the same moment would be separate entries sharing very close timestamps.


## 2. TX Agent: Conversational Access to Broadcast History

The TX Agent uses an LLM with a Retrieval Augmented Generation (RAG) approach.

**Responsibilities:**

* **Natural Language Understanding (NLU):** Interpret user queries.
* **Query Formulation for Database:**
    1. Determine the relevant time window or key events from the user's query.
    2. Query the database (e.g., Firestore) for all relevant log entries (audio, video, graphics, etc.) within that time window or associated with those events, using timestamps as the primary linking mechanism.
* **Contextual Data Retrieval:** Gather the disparate log entries (e.g., a transcript, a scene description, an on-screen graphic text) that correspond to the same broadcast moment or period.
* **Information Synthesis & Presentation (via LLM):** Pass the retrieved, time-correlated data along with the original query to the LLM. The LLM then synthesizes this information into a coherent answer.


## 3. Technologies:

- Python 3.8+
- FFmpeg
- ADK (Agent Development Kit)
- Google Cloud Gemini
- Google Cloud Firestore



### Example Interaction Flow (Simplified):

1. **Director:** "TX Agent, what did the commentator say when Smith scored that goal around 01:15?"
2. **TX Agent:**
    * Identifies "Smith," "goal," and time "01:15" as key entities.
    * Queries Firestore for `log_type: "video_scene_description"` containing "Smith" and "goal" around `timecode: "01:15:xx:xx"`. Finds `video_event_001` at `timecode: "01:15:33:00"`.
    * Queries Firestore for `log_type: "audio_transcript_segment"` with `timecode` very close to `01:15:33:00`. Finds `audio_event_001`.
    * Queries for other relevant logs like `on_screen_graphic` around the same time. Finds `osg_event_001`.
    * Provides the LLM with the question and the content of `audio_event_001`, `video_event_001`, and `osg_event_001`.
3. **LLM (via TX Agent):** "At 01:15:33, when Smith scored the goal (described as 'Player #10 (Smith) scores a goal. Ball enters top left of net. Crowd celebrating.'), Commentator A said: 'And that's a fantastic goal from Smith! What a strike from outside the box!'. The score graphic showed 'Team A 1 - 0 Team B'."

## 4. Overall System Architecture (Simplified)

```mermaid
graph LR
    A[Live Broadcast Feed] --> B(TX Worker);

    subgraph TX Worker Process
        B -- Timestamped Segments --> C{Audio Ingest};
        B -- Timestamped Segments --> D{Video Ingest};
        C --> E[Audio Transcription];
        D --> F[Video Analysis];
        D --> G[Keyframe Extraction];
    end

    E -- Timestamped Log Entry --> H[Firestore Database];
    F -- Timestamped Log Entry --> H;
    G -- Timestamped Log Entry --> H;

    I(TX Agent - ADK);
    I -- Queries by Time/Content --> H;
    H -- Returns Multiple Log Entries --> I;
    J[Production Team User] <--> I;
    K[Other AI Agents/Systems] <--> I;
```

## 5. Installation & Usage

```bash
python3 -m venv .venv
pip install -r requirements.txt
```

Run the main file:

```bash
python3 main.py --stream-url https://somedomain.com/stream.m3u8
```

