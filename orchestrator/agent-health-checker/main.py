"""
This script checks the status of remote agents and updates their status in Firestore.
"""
import requests
from google.cloud import firestore

def main():
    """
    Checks the status of each remote agent and updates Firestore.
    """
    db = firestore.Client()
    agents_ref = db.collection('agent_status')
    agents = agents_ref.stream()

    for agent in agents:
        agent_dict = agent.to_dict()
        url = agent_dict.get('url')
        status = 'offline'

        if url:
            try:
                # Add a timeout to avoid hanging indefinitely
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    status = 'online'
                else:
                    status = 'error'
            except requests.exceptions.RequestException:
                status = 'offline'

        agents_ref.document(agent.id).update({
            'status': status,
            'last_checked': firestore.SERVER_TIMESTAMP
        })
        print(f"Updated status for {agent.id}: {status}")

if __name__ == "__main__":
    main()
