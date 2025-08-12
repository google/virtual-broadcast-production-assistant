# Activity Agent

Code has been organsed to be run in as a package so to run naviagte to directory above and, when in relevant virtual envrionement with dependancies installed, run

```bash
python -m activity-agent
```

This agent will attempt to insert any messages it gets into a datastore. This is defined in the MCP server found in `tools/`.

Currently the data gets inserted in a JSON file serving as an activity store but the server could be updated to integrate with any other store.

The content of the activity store can be viewed in a simple local UI by running 

```bash
cd tools
np run start
```
