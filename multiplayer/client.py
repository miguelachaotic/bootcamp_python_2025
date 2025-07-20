from enum import Enum
from websockets.asyncio.client import connect, ClientConnection
from server import DEFAULT_HOST, DEFAULT_PORT, MIN_PLAYER_COUNT
import ipaddress
from models import NetworkRequest, Player, GameState, Message
from loguru import logger
from colorist import ColorRGB, BgColor
import asyncio
import msvcrt
import threading
import json



MIN_PORT = 1024
MAX_PORT = 65535

RESET_COLOR = '\033[39m'

COLORS = {
    'red': ColorRGB(255, 0, 0),
    'blue': ColorRGB(0, 0, 255),
    'green': ColorRGB(0, 255, 0),
    'yellow': ColorRGB(255, 255, 0)
}


class PlayerHostType(str, Enum):
    HOST = 'host'
    PLAYER = 'player'

PLAYER_HOST_TYPE = PlayerHostType.HOST

async def client(player_host_type: PlayerHostType) -> None:
    port = DEFAULT_PORT
    host = DEFAULT_HOST
    ready = False
    if player_host_type is PlayerHostType.PLAYER:
        host = input('Enter the host\'s IP: ')
        if not host:
            host = DEFAULT_HOST
        while not valid_ip(host) and host:
            host = input('Invalid IP format, try again: ')
        port = input('Enter the host\'s port: ')
        if not port:
            port = DEFAULT_PORT
        try:
            port = int(port)
            while not valid_port(port) and port != DEFAULT_PORT:
                port = int(input(f'Invalid port. Port must be between {MIN_PORT} and {MAX_PORT}. Try again: '))
        
        except ValueError:
            port = DEFAULT_PORT    
    uri = f'ws://{host}:{port}'

    async with connect(uri) as websocket:
        message = Message(type=NetworkRequest.SET_PLAYER_INFO)
        username = input('Enter your username: ')
        while not username.strip():
            username = input('You cannot have an empty username. Try again: ')
        
        logger.info(f'Your {username = }')
        colored_colors = [f'{v}{k}{v.OFF}' for k, v in COLORS.items()]
        color = await asyncio.to_thread(input, f'Choose a color between this: {' '.join(colored_colors)} ')
        while not any([color in c for c in COLORS]):
            color = await asyncio.to_thread(input, f'Choose a valid color between theese ones: {' '.join(colored_colors)}. Try again: ')
        
        player = Player(name=username, color=color)
        message.data = player.model_dump()
        await websocket.send(message.model_dump_json())
        
        message = Message.model_validate(json.loads(await websocket.recv()))
        
        if message.type != NetworkRequest.ACK:
            logger.critical(f'Received invalid protocol primitive {message.type}')
            raise RuntimeError('Invalid protocol primitive')
        
        async def check_enter():
            while True:
                if msvcrt.kbhit() and msvcrt.getch() == b'\r':
                    if ready:
                        await websocket.send(Message(type=NetworkRequest.START).model_dump_json())
                    
        enter_thread = threading.Thread(target=check_enter, daemon=True)
        enter_thread.start()
        
        if player_host_type == PlayerHostType.HOST:
            async for message in websocket:
                await websocket.send(Message(type=NetworkRequest.READY).model_dump_json())
                response = Message.model_validate(json.loads(await websocket.recv()))
                ready = response.data['players'] >= MIN_PLAYER_COUNT
                logger.info(f'[CLIENT] There are {response.data['players']} in lobby now. You can{' start now if you want.' if ready else 'not start by now. Wait until more people join.'}')
                if response.type == NetworkRequest.START:
                    break
        else:
            async for message in websocket:
                response = Message.model_validate(json.loads(await websocket.recv()))
                if response.type == NetworkRequest.START:
                    break
        logger.success('[CLIENT] Game starts NOW!!')
        
        
        
        
        
        
        await websocket.close()
        
        
            
        
        

def valid_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False
    
def valid_port(port: int) -> bool:
    return MIN_PORT <= port <= MAX_PORT
    