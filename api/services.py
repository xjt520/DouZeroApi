import torch
import numpy as np
from typing import List, Tuple, Dict, Any

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
from douzero.env.move_generator import MovesGener
from douzero.env import move_detector as md
from douzero.env.game import InfoSet
from douzero.env.env import get_obs

from api.utils import CardConverter, ActionTypeDetector, ALL_ENV_CARDS
from api.models import PlayRequest, ActionResponse, ActionsResponse

class DouZeroService:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def evaluate_action(self, request: PlayRequest) -> Tuple[List[int], float, List[Tuple[List[int], float]]]:
        """Evaluate the best action for the given state using DouZero."""
        agent = self.model_manager.get_model(request.position)

        my_cards_env = CardConverter.real_to_env(request.my_cards)
        landlord_cards_env = CardConverter.real_to_env(request.landlord_cards) if request.landlord_cards else []
        
        # Calculate played cards
        played_cards_env = {}
        for pos in ['landlord', 'landlord_up', 'landlord_down']:
            played = request.played_cards.get(pos, "")
            played_cards_env[pos] = CardConverter.real_to_env(played) if played else []
        
        # Resolve other cards and missing info
        all_played = played_cards_env['landlord'] + played_cards_env['landlord_up'] + played_cards_env['landlord_down']
        other_cards_env = []
        for card in set(ALL_ENV_CARDS):
            count = ALL_ENV_CARDS.count(card) - my_cards_env.count(card) - all_played.count(card)
            other_cards_env.extend([card] * count)
        other_cards_env = sorted(other_cards_env)

        # Resolve card counts
        if request.cards_left:
            num_cards_left_dict = {
                'landlord': request.cards_left.get('landlord', 20),
                'landlord_up': request.cards_left.get('landlord_up', 17),
                'landlord_down': request.cards_left.get('landlord_down', 17)
            }
        else:
            num_cards_left_dict = {
                'landlord': 20 - len(played_cards_env['landlord']),
                'landlord_up': 17 - len(played_cards_env['landlord_up']),
                'landlord_down': 17 - len(played_cards_env['landlord_down'])
            }
            num_cards_left_dict[request.position] = len(my_cards_env)

        # Resolve last move
        last_move_env = []
        if request.last_moves:
            for move in reversed(request.last_moves):
                if move:
                    last_move_env = CardConverter.real_to_env(move)
                    break
        
        legal_actions = []
        try:
            mg = MovesGener(my_cards_env)
            if not last_move_env:
                legal_actions = mg.gen_moves()
            else:
                rival_type = md.get_move_type(last_move_env)
                rival_move_type = rival_type['type']
                rival_move_len = rival_type.get('len', 1)
                
                if rival_move_type == md.TYPE_0_PASS:
                    legal_actions = mg.gen_moves()
                elif rival_move_type == md.TYPE_1_SINGLE:
                    legal_actions = mg.gen_type_1_single()
                elif rival_move_type == md.TYPE_2_PAIR:
                    legal_actions = mg.gen_type_2_pair()
                elif rival_move_type == md.TYPE_3_TRIPLE:
                    legal_actions = mg.gen_type_3_triple()
                elif rival_move_type == md.TYPE_4_TRIPLE_WITH_ONE:
                    legal_actions = mg.gen_type_4_triple_with_one()
                elif rival_move_type == md.TYPE_5_TRIPLE_WITH_TWO:
                    legal_actions = mg.gen_type_5_triple_with_two()
                elif rival_move_type == md.TYPE_6_FOUR_WITH_TWO:
                    legal_actions = mg.gen_type_6_four_with_two()
                elif rival_move_type == md.TYPE_7_STRAIGHT:
                    legal_actions = mg.gen_type_7_straight(rival_move_len)
                elif rival_move_type == md.TYPE_8_STRAIGHT_PAIR:
                    legal_actions = mg.gen_type_8_straight_pair(rival_move_len)
                elif rival_move_type == md.TYPE_9_PLANE_WITH_ONE:
                    legal_actions = mg.gen_type_9_plane_with_one(rival_move_len)
                elif rival_move_type == md.TYPE_10_PLANE_WITH_TWO:
                    legal_actions = mg.gen_type_10_plane_with_two(rival_move_len)
                elif rival_move_type == md.TYPE_11_BOMB:
                    legal_actions = mg.gen_type_11_bomb()
                elif rival_move_type == md.TYPE_12_ROCKET:
                    legal_actions = []

                if not legal_actions:
                    legal_actions = [[]]
        except Exception:
            legal_actions = [[]]

        # Construct InfoSet manually
        infoset = InfoSet(request.position)
        infoset.player_hand_cards = my_cards_env
        infoset.three_landlord_cards = landlord_cards_env
        infoset.bomb_num = request.bomb_count
        infoset.legal_actions = legal_actions
        infoset.last_move = last_move_env
        infoset.num_cards_left_dict = num_cards_left_dict
        infoset.other_hand_cards = other_cards_env
        infoset.played_cards = played_cards_env
        
        infoset.last_two_moves = [[], []]
        infoset.last_move_dict = {'landlord': [], 'landlord_up': [], 'landlord_down': []}
        infoset.card_play_action_seq = []
        
        if request.last_moves:
            play_order = ['landlord', 'landlord_down', 'landlord_up']
            current_idx = play_order.index(request.position)
            
            for i, move in enumerate(reversed(request.last_moves)):
                player_idx = (current_idx - 1 - i) % 3
                player_pos = play_order[player_idx]
                env_m = CardConverter.real_to_env(move) if move else []
                if i < 2:
                    infoset.last_two_moves[1 - i] = env_m
                if not infoset.last_move_dict[player_pos]:
                    infoset.last_move_dict[player_pos] = env_m
                if i == 0:
                    infoset.last_pid = player_pos
                if env_m:
                    infoset.card_play_action_seq.insert(0, env_m)
        else:
            infoset.last_pid = 'landlord'

        infoset.all_handcards = {
            'landlord': my_cards_env if request.position == 'landlord' else [],
            'landlord_up': my_cards_env if request.position == 'landlord_up' else [],
            'landlord_down': my_cards_env if request.position == 'landlord_down' else []
        }

        if len(legal_actions) == 1:
            return legal_actions[0], 1.0, [(legal_actions[0], 1.0)]

        # Custom forward pass to get all Q-values
        obs = get_obs(infoset) 
        z_batch = torch.from_numpy(obs['z_batch']).float()
        x_batch = torch.from_numpy(obs['x_batch']).float()
        if torch.cuda.is_available():
            z_batch, x_batch = z_batch.cuda(), x_batch.cuda()
            
        with torch.no_grad():
            y_pred = agent.model.forward(z_batch, x_batch, return_value=True)['values']
        y_pred = y_pred.detach().cpu().numpy().flatten()
        
        best_action_index = np.argmax(y_pred)
        best_action = infoset.legal_actions[best_action_index]
        best_confidence = float(y_pred[best_action_index])

        # Create sorted list of actions and their confidence
        action_list = []
        for i, action in enumerate(infoset.legal_actions):
            # Scale Q-value to [0, 1] roughly. Q-values are mostly [-1, 1]
            q_val = float(y_pred[i])
            win_rate = (q_val + 1.0) / 2.0
            win_rate = max(0.0, min(1.0, win_rate))
            action_list.append((action, win_rate))
        
        action_list.sort(key=lambda x: x[1], reverse=True)
        best_win_rate = max(0.0, min(1.0, (best_confidence + 1.0) / 2.0))

        return best_action, best_win_rate, action_list
