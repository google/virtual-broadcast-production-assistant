# EVS Agent

## Agent card

```bash
curl -sS http://a2a.ibc-accelerator.evs.com:10010/.well-known/agent.json | jq
```

```json
{
  "capabilities": {
    "streaming": true
  },
  "defaultInputModes": [
    "text",
    "file",
    "video/mp4",
    "video/quicktime"
  ],
  "defaultOutputModes": [
    "text",
    "file",
    "video/mp4",
    "video/quicktime"
  ],
  "description": "### **Description** An agent powered by EVS technology for advanced, broadcast-quality video processing. It provides distinct capabilities to apply visual effects, perform intelligent reframing, and blur specific subjects within a video. The agent accepts a video file via URL or local path and returns an artifact containing a link to the processed video. Edits can be applied to specific segments using a start time and duration in seconds.\n        ### **Capabilities** The agent's functionalities are split into three main actions:\n        \n        * **`apply_xtrafx`**: Applies a specified visual effect to the video. This includes cinematic looks, deblurring, and slow-motion.\n        * **`apply_reframing`**: Intelligently reframes video to a new aspect ratio, with an option to track a specific subject described in a prompt.\n        * **`blur_subjects`**: Blurs subjects within the video based on a descriptive prompt (e.g., blurring all faces).\n    \n        ### **Parameters by Capability**\n        \n        #### **`apply_xtrafx`**\n        Use these parameters to apply standard visual effects.\n        \n        | Parameter | Type | Required | Description |\n        | :--- | :--- | :--- | :--- |\n        | `input_uri` | `string` | **Yes** | URL or local path to the source video. |\n        | `effect_name` | `string` | **Yes** | Effect to apply. Must be one of: **`\"bokeh\"`** (or `\"cinematic\"` or `\"depth dependant blur \"` or `\"shallow depth of field\"`), **`\"deblur\"`**, or **`\"xtramotion\"`** or (`\"xmo\"` or `\"slow down\"`). |\n        | `start_time` | `integer` | No | Start time in seconds for the effect. Defaults to `0`. |\n        | `duration` | `integer` | No | Duration in seconds to process from the `start_time`. Defaults to `0` (processes to the end). |\n        \n        #### **`apply_reframing`**\n        Use these parameters to change the video's aspect ratio.\n        \n        | Parameter | Type | Required | Description |\n        | :--- | :--- | :--- | :--- |\n        | `input_uri` | `string` | **Yes** | URL or local path to the source video. |\n        | `aspect_ratio`| `string` | **Yes** | Target aspect ratio (e.g., `\"9:16\"`, `\"1:1\"`). |\n        | `prompt` | `string` | No | Optional text describing the subject to track (e.g., \"the person in the red shirt\"). If omitted, the agent auto-detects the main subject. |\n        | `start_time` | `integer` | No | Start time in seconds. Defaults to `0`. |\n        | `duration` | `integer` | No | Duration in seconds to process. Defaults to `0` (processes to the end). |\n        \n        #### **`blur_subjects`**\n        Use these parameters to blur objects or people.\n        \n        | Parameter | Type | Required | Description |\n        | :--- | :--- | :--- | :--- |\n        | `input_uri` | `string` | **Yes** | URL or local path to the source video. |\n        | `prompt` | `string` | **Yes** | Text describing the subject to blur. **Note:** To blur faces, use `\"face\"` or `\"faces\"` exclusively. |\n        | `start_time` | `integer` | No | Start time in seconds. Defaults to `0`. |\n        | `duration` | `integer` | No | Duration in seconds to process. Defaults to `0` (processes to the end). |\n        \n        ### **Output**\n        The agent returns a JSON object with `kind: \"artifact-update\"`. The result is located in the `artifact.parts` array, which contains a `text` confirmation and a `file` object with the `uri` of the processed video.\n        \n        ```json\n        {\n          \"artifact\": {\n            \"artifactId\": \"8e9c97bd-b6ea-4a77-bd06-53439c6b0795\",\n            \"parts\": [\n              {\n                \"kind\": \"text\",\n                \"text\": \"Effect applied to the video!\"\n              },\n              {\n                \"file\": {\n                  \"mimeType\": \"video/quicktime\",\n                  \"uri\": \"https://[...]/output/processed_video.mov?X-Amz-...\"\n                },\n                \"kind\": \"file\"\n              }\n            ]\n          },\n          \"kind\": \"artifact-update\"\n        }",
  "name": "EVS Agent",
  "security": [
    {
      "ApiKeyAuth": []
    }
  ],
  "skills": [
    {
      "description": "Reframe a video in another format (9:16, 1:1, 4:3, 16:9).",
      "examples": [
        "Reframe this video to 9:16 by focusing on the presenter",
        "Reframe this video to 1:1",
        "Change the aspect ratio of this video to 4:3",
        "Crop this video to 16:9 focusing on the person in the red shirt",
        "Reframe this video to 9:16",
        "Change the aspect ratio of this video to 1:1 at 15 seconds for a duration of 10 seconds",
        "Crop this video to 4:3 focusing on the cat for a duration of 20 seconds",
        "Reframe this video to 16:9 starting at 30 seconds",
        "Reframe this video to 9:16 focusing on the dog for the first 15 seconds"
      ],
      "id": "evs_video_reframing",
      "name": "Video reframing",
      "tags": [
        "reframing",
        "9:16",
        "1:1",
        "4:3",
        "16:9",
        "reframe",
        "crop",
        "resize",
        "change aspect ratio"
      ]
    },
    {
      "description": "Apply evs effect (bokeh, deblur or xtramotion/xmo) to video.",
      "examples": [
        "Apply deblur effect to video",
        "Apply bokeh effect to video",
        "Apply xtramotion effect to video",
        "Apply xmo effect to video",
        "Apply cinematic effect to video",
        "Apply slow down effect to video",
        "Apply depth dependant blur effect to video",
        "Apply shallow depth of field effect to video",
        "Slow down this video",
        "Add bokeh effect to this video for the first 15 seconds",
        "Add cinematic effect to this video  starting at 30 seconds",
        "Add xmo effect to this video at 15 seconds for a duration of 10 seconds",
        "Add deblur effect to this video for a duration of 20 seconds"
      ],
      "id": "evs_effect",
      "name": "EVS effect",
      "tags": [
        "effect",
        "bokeh",
        "deblur",
        "xtramotion",
        "xmo",
        "cinematic",
        "slow motion",
        "motion blur",
        "depth dependant blur",
        "shallow depth of field"
      ]
    },
    {
      "description": "Automatically blur objects or faces in a video based on a prompt",
      "examples": [
        "Apply face blur effect to video",
        "Blur faces in video",
        "Blur all faces in the video",
        "Blur the person in the red shirt",
        "Blur the car in the video",
        "Blur faces in this video for the first 15 seconds",
        "Blur all faces in this video starting at 30 seconds",
        "Blur the person in the red shirt in this video at 15 seconds for a duration of 10 seconds",
        "Blur the ball in this video for a duration of 20 seconds",
        "Blur the sheet of papers in the video"
      ],
      "id": "evs_object_blur",
      "name": "EVS automatic objects blurring",
      "tags": [
        "face blur",
        "blur faces",
        "blur objects",
        "add blur",
        "blur subjects",
        "blur subject",
        "blur people",
        "blur person"
      ]
    }
  ],
  "url": "http://a2a.ibc-accelerator.evs.com:10010/",
  "version": "1.0.0"
}
```
