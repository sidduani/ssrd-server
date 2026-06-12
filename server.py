import asyncio
import websockets
import random
import string
import os
import json

PORT = int(os.environ.get("PORT", 6000))
connected_clients = {}  # Maps ID -> {"ws": websocket, "password": pwd}

def generate_credentials():
    while True:
        uid = str(random.randint(100000, 999999))
        if uid not in connected_clients:
            break
    pwd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return uid, pwd

async def handler(websocket, path):
    my_id, my_pwd = generate_credentials()
    connected_clients[my_id] = {"ws": websocket, "password": my_pwd}
    print(f"[Server] Client connected. Assigned ID: {my_id}")
    
    try:
        # Send initial registration credentials
        await websocket.send(json.dumps({"type": "CREDENTIALS", "id": my_id, "pwd": my_pwd}))
        
        async for message in websocket:
            data = json.loads(message)
            
            if data.get("type") == "CONNECT":
                target_id = data.get("target_id")
                target_pwd = data.get("target_pwd")
                
                if target_id in connected_clients and target_id != my_id:
                    if connected_clients[target_id]["password"] == target_pwd:
                        target_ws = connected_clients[target_id]["ws"]
                        
                        # Tell both apps to link together via the signaling server relay
                        await target_ws.send(json.dumps({"type": "PAIR_AS_SENDER", "peer_id": my_id}))
                        await websocket.send(json.dumps({"type": "PAIR_AS_RECEIVER", "peer_id": target_id}))
                    else:
                        await websocket.send(json.dumps({"type": "ERROR", "msg": "Incorrect Password"}))
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "Invalid ID or Partner Offline"}))
                    
            elif data.get("type") == "STREAM_DATA":
                # Relay screen frame data to the matching receiver
                target_id = data.get("target_id")
                if target_id in connected_clients:
                    await connected_clients[target_id]["ws"].send(json.dumps({
                        "type": "FRAME", 
                        "frame": data.get("frame")
                    }))
                    
    except websockets.ConnectionClosed:
        pass
    finally:
        if my_id in connected_clients:
            del connected_clients[my_id]
        print(f"[Server] Client {my_id} disconnected.")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"[Server] SSRD WebSocket Signaling active on port {PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())