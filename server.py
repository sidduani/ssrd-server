import asyncio
import websockets
import hashlib
import random
import string
import os
import json

PORT = int(os.environ.get("PORT", 6000))
connected_clients = {}  # Maps ID -> {"ws": websocket, "password": pwd}

async def handler(websocket, path):
    my_id = None
    print("[Server] New connection handshake initiated.")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # --- REGISTER WITH HARDWARE PERMANENT ID ---
            if msg_type == "REGISTER":
                my_id = data.get("id")
                # If client didn't supply a password history, generate a numeric default
                default_pwd = ''.join(random.choices(string.digits, k=4))
                
                connected_clients[my_id] = {"ws": websocket, "password": default_pwd}
                print(f"[Server] Registered Host ID: {my_id} with default Pwd: {default_pwd}")
                await websocket.send(json.dumps({"type": "CREDENTIALS", "id": my_id, "pwd": default_pwd}))
            
            elif msg_type == "SET_CUSTOM_PASSWORD":
                custom_pwd = data.get("password", "").strip()
                if custom_pwd.isdigit() and my_id in connected_clients:
                    connected_clients[my_id]["password"] = custom_pwd
                    print(f"[Server] Host {my_id} updated password to: {custom_pwd}")
                    await websocket.send(json.dumps({"type": "PASSWORD_UPDATED", "pwd": custom_pwd}))
            
            elif msg_type == "CONNECT":
                target_id = data.get("target_id")
                target_pwd = data.get("target_pwd")
                
                if target_id in connected_clients and target_id != my_id:
                    if connected_clients[target_id]["password"] == target_pwd:
                        target_ws = connected_clients[target_id]["ws"]
                        # Alert both sides to open stream ports
                        await target_ws.send(json.dumps({"type": "PAIR_AS_SENDER", "peer_id": my_id}))
                        await websocket.send(json.dumps({"type": "PAIR_AS_RECEIVER", "peer_id": target_id}))
                    else:
                        await websocket.send(json.dumps({"type": "ERROR", "msg": "Incorrect Password"}))
                else:
                    await websocket.send(json.dumps({"type": "ERROR", "msg": "Invalid ID or Partner Offline"}))
                    
            elif msg_type in ["STREAM_DATA", "INPUT_EVENT"]:
                # Seamlessly forward video frames or mouse/keyboard actions to the linked partner
                target_id = data.get("target_id")
                if target_id in connected_clients:
                    await connected_clients[target_id]["ws"].send(json.dumps(data))
                    
    except websockets.ConnectionClosed:
        pass
    finally:
        if my_id in connected_clients:
            del connected_clients[my_id]
        print(f"[Server] Session ended for Host ID: {my_id}")

async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())