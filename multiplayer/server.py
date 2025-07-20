from models import (
    BlackCard,
    WhiteCard,
    Card,
    Phase,
    GameState,
    Deck,
    CAHDrawingListEmpty,
    Player,
    PlayerRole,
    random_subset_choice_with_tracking,
    GameSettings,
    NetworkRequest,
    Message
)
import threading
import asyncio
from websockets.exceptions import ConnectionClosed
from websockets.asyncio.server import ServerConnection, Server as WebSocketServer, serve
from loguru import logger
import time
from typing import Optional, Callable, Self, Any

from pydantic import Field
from pathlib import Path
import os
import json
from uuid import uuid4, UUID
from dataclasses import dataclass



CAH_DECKS_PATH: Path = Path(__file__).parent.parent / 'decks'
JSON_EXTENSION: str = '.json'


PLAYER_COUNT_DEFAULT: int = 10
MIN_PLAYER_COUNT: int = 3
MAX_PLAYER_COUNT: int = 20


HAND_SIZE_DEFAULT: int = 5
MIN_HAND_SIZE: int = 4
MAX_HAND_SIZE: int = MIN_HAND_SIZE * 2


ROUND_TIME_DEFAULT: int = 30
MIN_ROUND_TIME: int = ROUND_TIME_DEFAULT
MAX_ROUND_TIME: int = MIN_ROUND_TIME * 4


ROUND_COUNT_DEFAULT: int = 3
MIN_ROUND_COUNT: int = ROUND_COUNT_DEFAULT
MAX_ROUND_COUNT: int = 50


WINNING_SCORE_DEFAULT: int = 5
MIN_WINNING_SCORE: int = 3
MAX_WINNING_SCORE: int = 15

DEFAULT_HOST: str = 'localhost'
DEFAULT_PORT: int = 8765



@dataclass
class Server:
    game_state: GameState
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    clients: dict[UUID, Player] = Field(default_factory=dict)
    _websocket: WebSocketServer | None = None
    
    async def handle_network_request(self, websocket: ServerConnection) -> None:
        protocol: dict[NetworkRequest, Callable[[ServerConnection, Self, Message], Future[None]]] = { #type: ignore
            NetworkRequest.DISCONNECT:          handle_disconnect,
            NetworkRequest.GET_GAME_STATE:      handle_get_game_state,
            NetworkRequest.SET_PLAYER_CHOICES:  handle_set_player_choices,
            NetworkRequest.SET_PLAYER_INFO:     handle_set_player_info
        }
        message: Message | None = None
        message_dict = json.loads(await websocket.recv())
        message = Message.model_validate(message_dict)
        
        try:
            await protocol[message.type](websocket, self, message)
            
        except Exception:
            logger.info(f'{'a'}')
            
            
    async def serve(self) -> None:
        async with serve(self.handle_network_request, host=self.host, port=self.port) as server:
            await server.serve_forever()
            
        
        
async def handle_disconnect(
    websocket: ServerConnection, 
    server: Server, 
    message: Message
) -> None:
    logger.info(f'Client disconnected from {websocket.remote_address}')
    server.clients.pop(websocket.id)
    if len(server.clients.keys()) < MIN_PLAYER_COUNT:
        logger.warning('Closing program: not enough players at the moment.')
        if server._websocket is None:
            raise RuntimeError('This should not happen')
        await server._websocket.close() # type: ignore
        # If less than 3 players, then shut the game
    await websocket.close()
    
    
async def handle_get_game_state(
    websocket: ServerConnection, 
    server: Server, 
    message: Message
) -> None:
    logger.info(f'Client {websocket.remote_address} requesting game state')
    

async def handle_set_player_info(
    websocket: ServerConnection, 
    server: Server, 
    message: Message
) -> None:
    logger.info(f'Creating new user from {websocket.remote_address}.')
    player_info = json.loads(await websocket.recv())
    player_info['uuid'] = websocket.id
    player = Player(**player_info)
    logger.info(f'User registered as {player}')
    
    


async def handle_set_player_choices(
    websocket: ServerConnection, 
    server: Server, 
    message: Message
) -> None:
    logger.info(f'Assigning new card choices for {websocket.remote_address}')

async def handle_ready(
    websocket: ServerConnection,
    server: Server,
    message: Message
) -> None:
    logger.info(f'Checking if the game can start')
    await websocket.send(Message(type=NetworkRequest.READY, data={
        'players': len(server.game_state.players)
    }).model_dump_json())

async def handle_start(
    websocket: ServerConnection,
    server: Server,
    message: Message
) -> None:
    logger.info(f'Trying to start game')
    await websocket.send(Message(type=NetworkRequest.START).model_dump_json())


def list_decks(print_to_stdout: bool = True) -> list[str]:
    print('Select one Deck to play with: ', end='')
    decks = []
    files = os.listdir(CAH_DECKS_PATH)
    for file in files:
        file_path = os.path.join(CAH_DECKS_PATH, file)
        if os.path.isfile(file_path):
             decks.append(file)
    
    if print_to_stdout:    
        [print(f'- {deck[:-len(JSON_EXTENSION)]}', end='\n') for deck in decks]
    return decks

def select_deck() -> str:
    decks = list_decks()
    selected_deck: str = input('')
    while selected_deck + JSON_EXTENSION not in decks:
        logger.warning('Deck does not exist, try again')
        selected_deck = input('')
    logger.info(f'Selected Deck: {selected_deck}')
    return selected_deck
    

def get_max_player_count() -> int:
    max_player_count = MIN_PLAYER_COUNT
    try:
        max_player_count = int(input('Max count of players (optional): '))
        while MIN_PLAYER_COUNT > max_player_count or max_player_count > MAX_PLAYER_COUNT:
            logger.warning(f'Max count of players must be between {MIN_PLAYER_COUNT} and {MAX_PLAYER_COUNT}. Try again: ')
            max_player_count = int(input(''))
    except ValueError:
        max_player_count = PLAYER_COUNT_DEFAULT
    logger.info(' '.join([a.capitalize() for a in f'{max_player_count = } '.split('_')]))
    return max_player_count

def get_max_hand_size() -> int:
    max_hand_size = MIN_HAND_SIZE
    try:
        max_hand_size = int(input('Max hand size (optional): '))
        while MIN_HAND_SIZE > max_hand_size or max_hand_size > MAX_HAND_SIZE:
            logger.warning(f'Max hand size must be between {MIN_HAND_SIZE} and {MAX_HAND_SIZE}. Try again: ')
            max_hand_size = int(input(''))
    except ValueError:
        max_hand_size = HAND_SIZE_DEFAULT
    logger.info(' '.join([a.capitalize() for a in f'{max_hand_size = } '.split('_')]))
    return max_hand_size

def get_max_round_time() -> int:
    max_round_time = MIN_ROUND_TIME
    try:
        max_round_time = int(input('Max round time (optional): '))
        while MIN_ROUND_TIME > max_round_time or max_round_time > MAX_ROUND_TIME:
            logger.warning(f'Max round time must be between {MIN_ROUND_TIME} and {MAX_ROUND_TIME}. Try again: ')
            max_round_time = int(input(''))
    except ValueError:
        max_round_time = ROUND_TIME_DEFAULT
    logger.info(' '.join([a.capitalize() for a in f'{max_round_time = } '.split('_')]))
    return max_round_time


def get_max_round_count() -> int:
    max_round_count = MIN_ROUND_COUNT
    try:
        max_round_count = int(input('Max rounds (optional): '))
        while MIN_ROUND_COUNT > max_round_count or max_round_count > MAX_ROUND_COUNT:
            logger.warning(f'Max rounds must be between {MIN_ROUND_COUNT} and {MAX_ROUND_COUNT}. Try again: ')
            max_round_count = int(input(''))
    except ValueError:
        max_round_count = ROUND_COUNT_DEFAULT
    logger.info(' '.join([a.capitalize() for a in f'{max_round_count = } '.split('_')]))
    return max_round_count

def get_max_winning_score() -> int:
    max_winning_score = MIN_ROUND_COUNT
    try:
        max_winning_score = int(input('Max winning score (optional): '))
        while MIN_WINNING_SCORE > max_winning_score or max_winning_score > MAX_WINNING_SCORE:
            logger.warning(f'Max rounds must be between {MIN_WINNING_SCORE} and {MAX_WINNING_SCORE}. Try again: ')
            max_winning_score = int(input(''))
    except ValueError:
        max_winning_score = WINNING_SCORE_DEFAULT
    logger.info(' '.join([a.capitalize() for a in f'{max_winning_score = } '.split('_')]))
    return max_winning_score

def get_seed() -> int:
    seed = int(time.time())
    if input_seed := input('Random Seed (optional): '):
        try:
            seed = int(input_seed)
        except ValueError:
            pass
    logger.info(' '.join([a.capitalize() for a in f'{seed = } '.split('_')]))
    return seed 

async def host() -> None:
    # Host mode
    # 2.a -> GAME SETTINGS 
    # DECK SETTINGS
    deck_path: str = select_deck()
    deck: Optional[Deck] = None
    with open(CAH_DECKS_PATH / (deck_path + JSON_EXTENSION), 'r', encoding='utf-8') as deck_file:
        deck = Deck(**json.load(deck_file))
        
    max_player_count = get_max_player_count()
    max_hand_size = get_max_hand_size()
    max_round_time = get_max_round_time()
    max_round_count = get_max_round_count()
    # max_winning_score = get_max_winning_score() NICE TO HAVE, BUT NOT YET
    seed = get_seed()
    
    game_settings = GameSettings(
        deck=deck,
        max_hand_size=max_hand_size,
        max_player_count=max_player_count,
        max_round_time=max_round_time,
        max_rounds=max_round_count,
        random_seed=seed
    )
    
    server = Server(GameState(settings=game_settings))
    
    await server.serve()
    
    