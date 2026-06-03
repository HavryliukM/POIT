import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://127.0.0.1:5001/ws"
    async with websockets.connect(uri) as websocket:
        # Open and start
        await websocket.send(json.dumps({"action": "open"}))
        await websocket.send(json.dumps({"action": "start"}))
        
        count = 0
        while count < 50:
            msg = await websocket.recv()
            print(msg)
            count += 1

asyncio.run(test_ws())
