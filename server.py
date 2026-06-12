import asyncio
import websockets
import random
import string
import os
import json

PORT = int(os.environ.get("PORT", 6000))
connected_clients = {}

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
    print(f"[Server] Connected: {my_id}")
    
    try:
        await websocket.send(json.dumps({"type": "CREDENTIALS", "id": my_id, "pwd": my_pwd}))
        
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "CONNECT":
                target_id = data.get("target_id")
                target_pwd = data.get("target_pwd")
                if target_id in connected_clients and target_id != my_id:
                    if connected_clients[target_id]["password"] == target_pwd:
                        await connected_clients[target_id]["ws"].send(json.dumps({"type": "PAIR_AS_SENDER", "peer_id": my_id}))
                        await websocket.send(json.dumps({"type": "PAIR_AS_RECEIVER", "peer_id": target_id}))
                    else:
                        await websocket.send(json.dumps({"type": "ERROR", "msg": "Incorrect Password"}))
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "Invalid ID or Partner Offline"}))
                    
            elif msg_type == "STREAM_DATA":
                target_id = data.get("target_id")
                if target_id in connected_clients:
                    await connected_clients[target_id]["ws"].send(json.dumps({"type": "FRAME", "frame": data.get("frame")}))
            
            # --- NEW: FILE TRANSFER RELAY ---
            elif msg_type == "FILE_CHUNK":
                target_id = data.get("target_id")
                if target_id in connected_clients:
                    await connected_clients[target_id]["ws"].send(json.dumps({
                        "type": "RECEIVE_FILE_CHUNK",
                        "filename": data.get("filename"),
                        "chunk": data.get("chunk"),
                        "is_last": data.get("is_last")
                    }))
                    
    except websockets.ConnectionClosed:
        pass
    finally:
        if my_id in connected_clients: del connected_clients[my_id]
        print(f"[Server] Disconnected: {my_id}")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())