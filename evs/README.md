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
    "text"
  ],
  "defaultOutputModes": [
    "text"
  ],
  "description": "This agent can apply the following effects: cinematic (bokeh, depth dependant blur, shallow depth of field effect), deblur (remove motion blur), xtramotion (xmo) (slow down video), reframing (reframe a video in the desired aspect ratio), and automatic object(s) blurring (blurring object(s) or face(s) in the video). It is accessible through the A2A protocol. The tool accepts an input URI and name of the effect to be applied and returns a video URI.",
  "name": "EVS Agent",
  "skills": [
    {
      "description": "Reframe a vide in another format (9:16, 1:1, 4:3).",
      "examples": [
        "Reframe video in_video.mp4 to 9:16 by focusing on the presenter"
      ],
      "id": "evs_video_reframing",
      "name": "Video reframing",
      "tags": [
        "reframing",
        "9:16",
        "1:1",
        "4:3"
      ]
    },
    {
      "description": "Apply evs effect (bokeh, deblur or xtramotion/xmo) to video.",
      "examples": [
        "Apply deblur effect to https://example.com/video.mp4"
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
      "description": "Apply deblur (removing motion blur) effect to video.",
      "examples": [
        "Apply deblur effect to https://example.com/video.mp4"
      ],
      "id": "evs_deblur",
      "name": "EVS deblur",
      "tags": [
        "deblur",
        "remove motion blur",
        "sharpen"
      ]
    },
    {
      "description": "Automatically blur objects or faces in a video based on a prompt",
      "examples": [
        "Apply face blur effect to https://example.com/video.mp4"
      ],
      "id": "evs_object_blur",
      "name": "EVS automatic objects blurring",
      "tags": [
        "face blur",
        "blur faces",
        "blur objects",
        "add blur",
        "blur subjects",
        "blur subject"
      ]
    }
  ],
  "url": "http://a2a.ibc-accelerator.evs.com:10010/",
  "version": "1.0.0"
}
```
