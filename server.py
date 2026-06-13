import asyncio
import websockets
import random
import string
import os
import json

PORT = int(os.environ.get("PORT", 6000))
connected_clients = {}  # In-memory map: ID -> {"ws": websocket, "password": pwd}

async def handler(websocket, path):
    my_id = None
    print("[Server] Inbound connection handshake initiated.")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # --- HANDLE ACTIVE BOOTSTRAP HANDSHAKE ---
            if msg_type == "REGISTER":
                my_id = data.get("id")
                
                # Check if this permanent ID already has a password set, otherwise make a default
                if my_id in connected_clients:
                    default_pwd = connected_clients[my_id]["password"]
                else:
                    default_pwd = ''.join(random.choices(string.digits, k=4))
                
                # Save the websocket session to activate the state mapping
                connected_clients[my_id] = {"ws": websocket, "password": default_pwd}
                print(f"[Server] SUCCESS: Host {my_id} is now ACTIVE.")
                
                # Confirm back to the client app to turn its UI "Online"
                await websocket.send(json.dumps({"type": "CREDENTIALS", "id": my_id, "pwd": default_pwd}))
            
            elif msg_type == "SET_CUSTOM_PASSWORD":
                custom_pwd = data.get("password", "").strip()
                if custom_pwd.isdigit() and my_id in connected_clients:
                    connected_clients[my_id]["password"] = custom_pwd
                    print(f"[Server] Host {my_id} customized password to: {custom_pwd}")
                    await websocket.send(json.dumps({"type": "PASSWORD_UPDATED", "pwd": custom_pwd}))
            
            elif msg_type == "CONNECT":
                target_id = data.get("target_id")
                target_pwd = data.get("target_pwd")
                
                if target_id in connected_clients and target_id != my_id:
                    if connected_clients[target_id]["password"] == target_pwd:
                        target_ws = connected_clients[target_id]["ws"]
                        # Connect both sides together
                        await target_ws.send(json.dumps({"type": "PAIR_AS_SENDER", "peer_id": my_id}))
                        await websocket.send(json.dumps({"type": "PAIR_AS_RECEIVER", "peer_id": target_id}))
                    else:
                        await websocket.send(json.dumps({"type": "ERROR", "msg": "Incorrect Password"}))
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "Invalid ID or Partner Offline"}))
                    
            elif msg_type in ["STREAM_DATA", "INPUT_EVENT", "FILE_CHUNK"]:
                # Instantly forward streams and controls to the paired partner
                target_id = data.get("target_id")
                if target_id in connected_clients:
                    await connected_clients[target_id]["ws"].send(json.dumps(data))
                    
    except websockets.ConnectionClosed:
        pass
    finally:
        if my_id in connected_clients:
            del connected_clients[my_id]
        print(f"[Server] Host {my_id} disconnected. Removed from active map.")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())