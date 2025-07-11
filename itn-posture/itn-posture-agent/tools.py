import requests
import json

## These are only example tools, they need to be connected to backend services to function properly

def GetStacks():
    """Retrieves information about the available stacks within the running order

    Args:
        None

    Returns:
        list: returns a list of dicts where each dict is a stack available
        Some stacks are enabled, and some are disabled, make sure the user is aware of this.
        The returning structure of a stack will something like this:
        {
            "id": "c0250fd0-88fb-4951-b210-1ccc0dadb79a",
            "label": "Channel 4 Evening News",
            "enabled": True,
            "startTime": "0700",
            "endTime": "2200"
        },
    """
    
    return []

def GetStackStats(stackId: str) -> dict:
    
    """Retrieves overall error stats about a running order provided its stackId

    Args:
        stackId: str -> dict

    Returns:
        dict: A dictionary containing a 'posture' key which contains textural counts of the errors found
    """

    return {}

def GetStack(stackId: str) -> dict:
    
    """Retrieves the full stack for a running order

    Args:
        stackId: str -> dict

    Returns:
        dict: A dictionary containing a list of stories, each with a list of elements.
        You may also be asked to identify a story with a specific label, if this occurs, use the 'label' key in the story.
        Stories and elements each contain a 'posture' key which provides access to spelling, sequence, factual, and enhancement checks
        For example: here's one with sequence and spelling
        "posture": {
            "sequence": "Sequence times not set",
            "spelling": "Count: 1 [Jerusalen -> [Jerusalem]]"
        }
        In spelling for instance, the number of errors are provided, and an array of the spelling mistake followed by -> [] where the embedded array are the suggestions.
        The enhancement and facutal string may be empty (if so just ignore them) however if they aren't read it to see if it's worth telling the user.
    """

    return {}