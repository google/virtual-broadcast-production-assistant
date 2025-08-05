import os
from shure_audio_agent.azure_logic_app_client import azure_logic_app_client
from shure_audio_agent.cache import cache_manager

def get_status():
    result = azure_logic_app_client.send_tool_request("get_status")
    cache_manager.set('status', result)
    return result 
    # cached = cache_manager.get('status')
    # if cached:
    #     return cached
    # with open(GQL_PATH, 'r') as f:
    #     query = f.read()
    # result = gql_client.run(query)
    # cache_manager.set('status', result)
    # return result

# def refresh_status_cache():
#     with open(GQL_PATH, 'r') as f:
#         query = f.read()
#     result = gql_client.run(query)
#     cache_manager.set('status', result)
#     return result 