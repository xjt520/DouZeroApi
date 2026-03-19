import torch
import numpy as np
from typing import List, Tuple, Dict, Any

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
from douzero.env.move_generator import MovesGener
from douzero.env import move_detector as md
from douzero.env import move_selector as ms
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
                    legal_actions = ms.filter_type_1_single(mg.gen_type_1_single(), last_move_env)
                elif rival_move_type == md.TYPE_2_PAIR:
                    legal_actions = ms.filter_type_2_pair(mg.gen_type_2_pair(), last_move_env)
                elif rival_move_type == md.TYPE_3_TRIPLE:
                    legal_actions = ms.filter_type_3_triple(mg.gen_type_3_triple(), last_move_env)
                elif rival_move_type == md.TYPE_6_3_1:
                    legal_actions = ms.filter_type_6_3_1(mg.gen_type_6_3_1(), last_move_env)
                elif rival_move_type == md.TYPE_7_3_2:
                    legal_actions = ms.filter_type_7_3_2(mg.gen_type_7_3_2(), last_move_env)
                elif rival_move_type == md.TYPE_8_SERIAL_SINGLE:
                    legal_actions = ms.filter_type_8_serial_single(mg.gen_type_8_serial_single(rival_move_len), last_move_env)
                elif rival_move_type == md.TYPE_9_SERIAL_PAIR:
                    legal_actions = ms.filter_type_9_serial_pair(mg.gen_type_9_serial_pair(rival_move_len), last_move_env)
                elif rival_move_type == md.TYPE_10_SERIAL_TRIPLE:
                    legal_actions = ms.filter_type_10_serial_triple(mg.gen_type_10_serial_triple(rival_move_len), last_move_env)
                elif rival_move_type == md.TYPE_11_SERIAL_3_1:
                    legal_actions = ms.filter_type_11_serial_3_1(mg.gen_type_11_serial_3_1(rival_move_len), last_move_env)
                elif rival_move_type == md.TYPE_12_SERIAL_3_2:
                    legal_actions = ms.filter_type_12_serial_3_2(mg.gen_type_12_serial_3_2(rival_move_len), last_move_env)
                elif rival_move_type == md.TYPE_13_4_2:
                    legal_actions = ms.filter_type_13_4_2(mg.gen_type_13_4_2(), last_move_env)
                elif rival_move_type == md.TYPE_14_4_22:
                    legal_actions = ms.filter_type_14_4_22(mg.gen_type_14_4_22(), last_move_env)
                elif rival_move_type == md.TYPE_4_BOMB:
                    legal_actions = ms.filter_type_4_bomb(mg.gen_type_4_bomb(), last_move_env) + mg.gen_type_5_king_bomb()
                elif rival_move_type == md.TYPE_5_KING_BOMB:
                    legal_actions = []

                # 非炸弹牌型都可以用炸弹/火箭压
                if rival_move_type not in [md.TYPE_0_PASS, md.TYPE_4_BOMB, md.TYPE_5_KING_BOMB]:
                    legal_actions.extend(mg.gen_type_4_bomb())
                    legal_actions.extend(mg.gen_type_5_king_bomb())
                
                # 对方出了牌才能 pass
                if len(last_move_env) > 0:
                    legal_actions.append([])
                    
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
            
            last_pid_found = False
            for i, move in enumerate(reversed(request.last_moves)):
                player_idx = (current_idx - 1 - i) % 3
                player_pos = play_order[player_idx]
                env_m = CardConverter.real_to_env(move) if move else []
                if i < 2:
                    infoset.last_two_moves[1 - i] = env_m
                if not infoset.last_move_dict[player_pos]:
                    infoset.last_move_dict[player_pos] = env_m
                # last_pid 应该是最后一个真实出牌（非空）的玩家
                if not last_pid_found and env_m:
                    infoset.last_pid = player_pos
                    last_pid_found = True
                infoset.card_play_action_seq.insert(0, env_m)
            
            # 如果所有 last_moves 都是空，使用默认值
            if not last_pid_found:
                infoset.last_pid = 'landlord'
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
