from json import load
from html import unescape
from pydantic import BaseModel, AfterValidator
from pydantic.dataclasses import dataclass
from typing import Annotated, Optional
from enum import Enum, auto
from itertools import cycle
import random

MAX_LENGTH_USER = 100
HAND_SIZE = 5

class TypePlayer(Enum):
    ZAR    = auto()
    NORMAL = auto()


class Card(BaseModel):
    text: Annotated[str, AfterValidator(unescape)]
    
    def __eq__(self, value: object) -> bool:
        return self.text == value
    
    def __hash__(self) -> int:
        return hash(self.text)

class WhiteCard(Card):
    pass
    
class BlackCard(Card):
    pick: int


class Player(BaseModel):
    player_id: int 
    name: Annotated[str, AfterValidator(lambda s: s if len(s) < MAX_LENGTH_USER else s[:MAX_LENGTH_USER])]
    player_type: TypePlayer = TypePlayer.NORMAL
    
    points: int = 0
    
    cards: list[WhiteCard] = []
    
    
    def set_zar(self):
        self.player_type = TypePlayer.ZAR
        return self
    
    def set_normal(self):
        self.player_type = TypePlayer.NORMAL
        return self

    def show_white_cards(self):
        for i, card in enumerate(self.cards):
            print(
f'''  +{'-'*(len(card.text) + 2)}+
{i+1} | {card.text} |
  +{'-'*(len(card.text) + 2)}+''')
            
    def select_cards(self, pick: int):
        picked_cards: set[int] = set()
        print(f'Cartas del jugador {self.name}')
        for p in range(pick):
            index: int = int(input(f'Selecciona la carta {p+1}: '))
            while index < 1 or index > HAND_SIZE:
                index = int(input(f'Índice inválido. Vuelva a seleccionarla: '))
            if index in picked_cards:
                index = int(input(f'Carta ya introducida. Vuelva a seleccionarla: '))
            picked_cards.add(index)
        return [card for i, card in enumerate(self.cards) if (i + 1) in picked_cards]


def check_no_repeating(cards: list[Card]) -> list[Card]:
        card_set: list[Card] = list(set(cards))
        if len(card_set) < len(cards):
            raise ValueError('Hay cartas repetidas')
        return cards

@dataclass
class Deck:
    black_cards: Annotated[list[BlackCard], AfterValidator(check_no_repeating)]
    white_cards: Annotated[list[WhiteCard], AfterValidator(check_no_repeating)]
    
    def shuffle_cards(self, seed: Optional[int] = None, num_shuffles: Optional[int] = None) -> None:
        if seed is None:
            seed = 0
        if num_shuffles is None:
            num_shuffles = 5
        random.seed(seed)
        shuffle = 0
        while shuffle < num_shuffles:
            random.shuffle(self.black_cards)
            random.shuffle(self.white_cards)
            shuffle += 1
            
    def draw_black_card(self) -> Optional[BlackCard]:
        try:
            return self.black_cards.pop()
        except IndexError:
            return None
        

class Game:
    players: list[Player]
    player_ordering: cycle #type: ignore
    zar: Player
    deck: Deck
    
    used_deck: Deck
    
    def __init__(self, players: list[Player], deck: Deck):
        self.players = players
        self.deck = deck
        self.player_ordering_list: list[int] = []
        self.random_zar()
        self.used_deck = Deck(white_cards=[], black_cards=[])
        self.init_game()

    def random_zar(self):
        self.zar = random.choice(self.players).set_zar()
            
        zar_id = self.zar.player_id
        for i in range(len(self.players)):
            self.player_ordering_list.append((zar_id + i) % len(self.players))
            
        self.player_ordering = cycle(self.player_ordering_list)
        next(self.player_ordering) #type: ignore
        
        
    def init_game(self):
        for _ in range(HAND_SIZE):
            for player in self.players:
                choice = random.choice(self.deck.white_cards)
                player.cards.append(choice)
                self.deck.white_cards.remove(choice)
    
    def show_choices(self, choices: list[tuple[Player, list[WhiteCard]]]):
        for i, choice in enumerate(choices):
            for j in range(len(choice[1])):
                print(
f'''  +{'-'*(len(choice[1][j].text) + 2)}+
{i+1 if j == 0 else ' '} | {choice[1][j].text} |
  +{'-'*(len(choice[1][j].text) + 2)}+''', end='\n')
            print()
        
    
    
    def play(self):
        print(f'El ZAR es {self.zar.name}')
        black_card: Optional[BlackCard] = self.deck.draw_black_card()
        if black_card is None:
            raise RuntimeError('No quedan cartas negras')
        print(f'Hay que escoger {black_card.pick} cartas en esta ronda.')
        print(f'CARTA NEGRA: {black_card.text.replace('_', '_'*5)}')
        actual_players: list[Player] = list(filter(lambda player: player.player_type != TypePlayer.ZAR, self.players))
        choices: list[tuple[Player, list[WhiteCard]]] = []
        self.get_player_choices(black_card, actual_players, choices)
        random.shuffle(choices)
        self.show_choices(choices)
        winner = int(input(f'ZAR {self.zar.name}, elige la mejor respuesta para tu gusto: '))
        while winner not in range(1, len(actual_players) + 1):
            winner = int(input(f'Introduce una opción correcta: (1-{len(actual_players) + 1})'))
        print(f'El ganador de esta ronda es {choices[winner - 1][0].name}!!')
        choices[winner - 1][0].points += 1
        self.next_zar()
        self.draw_new_cards(black_card, actual_players)

    def draw_new_cards(self, black_card: BlackCard, actual_players: list[Player]):
        for player in actual_players:
            for _ in range(black_card.pick):
                new_card = random.choice(self.deck.white_cards)
                player.cards.append(new_card)
                self.deck.white_cards.remove(new_card)

    def next_zar(self):
        self.zar.set_normal()
        self.zar = self.players[next(self.player_ordering)].set_zar() #type: ignore

    def get_player_choices(self, black_card: BlackCard, actual_players: list[Player], choices: list[tuple[Player, list[WhiteCard]]]) -> None:
        for player in actual_players:
            print(f'Turno de {player.name}')
            player.show_white_cards()
            selected_cards = player.select_cards(black_card.pick)
            choices.append((player, selected_cards))
            for card in selected_cards:
                player.cards.remove(card)
        
        
    def show_scoreboard(self):
        for player in self.players:
            print('-'*20)
            print(f'{player.name}: {player.points}')
        print('-'*20)
            
    @property
    def winner(self) -> Optional[Player]:
        for player in self.players:
            if player.points == 5:
                return player
        return None
    
    def end(self) -> bool:
        return self.winner is not None
        

def get_deck() -> Deck:
    with open('./decks/CAH.json', 'r', encoding='utf-8') as cah_file:
        json_deck = load(cah_file)
        deck = Deck(
            white_cards=[WhiteCard(text=_) for _ in json_deck['whiteCards']],
            black_cards=[BlackCard(text=card["text"], pick=card["pick"]) for card in json_deck['blackCards']]
        )
        return deck
        

def main() -> None:
    deck: Deck = get_deck()
    num_players = int(input('Introduce el número de jugadores: '))
    players: list[Player] = []
    for player in range(num_players):
        name = input(f'Jugador {player + 1}, Introduce tu nombre: ')
        players.append(Player(name=name, player_id=player))
        
    seed: Optional[int] = None
    num_shuffles: Optional[int] = None
    try:
        seed = int(input('Introduce una semilla (opcional): '))
    except ValueError:
        seed = random.randint(0, 100000)
    try:
        num_shuffles = int(input('Introduce el número de barajeos (opcional): '))
    except ValueError:
        num_shuffles = random.randint(1, 5)
    deck.shuffle_cards(seed=seed, num_shuffles=num_shuffles)
    
    game = Game(players=players, deck=deck)   
    
    print('-------------------------------------')
    print('Orden de Zar: ', ' -> '.join([players[next(game.player_ordering)].name for _ in range(num_players)])) #type: ignore
    print('-------------------------------------')
    
    while not game.end():
        game.play()
        game.show_scoreboard()
    
    print(f'¡¡¡El ganador es {game.winner}!!!')
    
if __name__ == '__main__':
    main()