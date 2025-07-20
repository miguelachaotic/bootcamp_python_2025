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
    random_subset_choice_with_tracking
)


from server import host
import asyncio
from websockets.asyncio.server import Server as WSServer, serve
from client import client, PlayerHostType


async def main() -> None:
    # Ask to user to host or join another host
    if mode := input('Host or Join? (H/J) ').capitalize()[0]:
        if mode.startswith('H'):
            
            await asyncio.gather(host(), client(PlayerHostType.HOST))
            
        if mode.startswith('J'):
            # Client mode
            await client(PlayerHostType.PLAYER)
    
    
    
if __name__ == '__main__':
    asyncio.run(main())