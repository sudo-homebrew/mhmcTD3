import numpy as np
import copy

import torch
import torch.nn.functional as F
import torch.nn as nn

from ..common.settings import POLICY_NOISE, POLICY_NOISE_CLIP, POLICY_UPDATE_FREQUENCY
from ..common.ounoise import OUNoise

from .off_policy_agent import OffPolicyAgent, Network

LINEAR = 0
ANGULAR = 1

# Reference for network structure: https://arxiv.org/pdf/2102.10711.pdf
# https://github.com/hanlinniu/turtlebot3_ddpg_collision_avoidance/blob/main/turtlebot_ddpg/scripts/original_ddpg/ddpg_network_turtlebot3_original_ddpg.py
# https://github.com/djbyrne/TD3
# Modified by: Seunghyeop
# Description: This code has been modified to train the Turtlebot3 Waffle_pi model.


class Actor(Network):
    def __init__(self, name, state_size, action_size, hidden_size):
        super(Actor, self).__init__(name)
        # --- define layers here ---
        self.dropout = nn.Dropout(0.3)

        self.fa1 = nn.Linear(state_size, hidden_size)
        self.fa2 = nn.Linear(hidden_size, int(hidden_size * 2))
        self.fa3 = nn.Linear(int(hidden_size * 2), int(hidden_size * 2))
        self.fa4 = nn.Linear(int(hidden_size * 2), int(hidden_size * 2))
        self.fa5 = nn.Linear(int(hidden_size * 2), hidden_size)

        self.fa5_1 = nn.Linear(hidden_size, int(hidden_size / 2 ** 1))
        self.fa5_2 = nn.Linear(int(hidden_size / 2 ** 1), int(hidden_size / 2 ** 1))
        self.fa5_3 = nn.Linear(int(hidden_size / 2 ** 1), hidden_size)

        # Resize Phase
        self.fa6 = nn.Linear(hidden_size, hidden_size)
        self.fa7 = nn.Linear(hidden_size, hidden_size)
        self.fa8 = nn.Linear(hidden_size, int(hidden_size * 2))
        self.fa9 = nn.Linear(int(hidden_size * 2), int(hidden_size * 2))
        self.fa10 = nn.Linear(int(hidden_size * 2), int(hidden_size * 2))
        self.fa11 = nn.Linear(int(hidden_size * 2), hidden_size)

        # Output Phase
        self.fa12 = nn.Linear(hidden_size, int(hidden_size / 2 ** 1))
        self.fa13 = nn.Linear(int(hidden_size / 2 ** 1), int(hidden_size / 2 ** 2))
        self.fa14 = nn.Linear(int(hidden_size / 2 ** 2), int(hidden_size / 2 ** 3))
        self.fa15 = nn.Linear(int(hidden_size / 2 ** 3), action_size)

        # SE blocks
        self.se_block1 = nn.Linear(int(hidden_size * 2), int(hidden_size / 2 ** 4))
        self.se_block2 = nn.Linear(int(hidden_size / 2 ** 4), hidden_size * 2)

        # Layer Normalisation blocks
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(int(hidden_size * 2))
        self.layer_norm3 = nn.LayerNorm(int(hidden_size / 2 ** 1))
        self.layer_norm4 = nn.LayerNorm(int(hidden_size / 2 ** 2))
        self.layer_norm5 = nn.LayerNorm(int(hidden_size / 2 ** 3))
        # self.layer_norm_action = nn.LayerNorm(action_size)

        self.apply(super().init_weights)

    def forward(self, states, visualize=False):
        # --- define forward pass here ---
        x = torch.relu(self.fa1(states))
        # x = self.layer_norm1(x)
        x = torch.relu(self.fa2(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.relu(self.fa3(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.relu(self.fa4(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.sigmoid(self.fa5(x))
        # x = self.layer_norm1(x)

        x = torch.sigmoid(self.fa5_1(x))
        x = torch.relu(self.fa5_2(x))
        x = torch.relu(self.fa5_3(x))

        # Resize Phase
        x = torch.relu(self.fa6(x))
        # x = self.layer_norm1(x)

        x = torch.relu(self.fa7(x))
        # x = self.layer_norm1(x)
        # x = self.layer_norm4(x)
        x = torch.relu(self.fa8(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.relu(self.fa9(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.relu(self.fa10(x))
        # x = self.dropout(x)
        # x = self.layer_norm2(x)
        x = torch.sigmoid(self.fa11(x))
        # x = self.layer_norm1(x)

        # Output Phase
        x = torch.sigmoid(self.fa12(x))
        # x = self.layer_norm3(x)
        x = torch.sigmoid(self.fa13(x))
        # x = self.layer_norm4(x)
        x = torch.sigmoid(self.fa14(x))
        # x = self.layer_norm5(x)
        action = torch.tanh(self.fa15(x))

        # -- define layers to visualize here (optional) ---
        if visualize and self.visual:
            self.visual.update_layers(states, action, [x1, x2], [self.fa1.bias, self.fa2.bias])
        # -- define layers to visualize until here ---
        return action

class Critic(Network):
    def __init__(self, name, state_size, action_size, hidden_size):
        super(Critic, self).__init__(name)

        # Q1
        # --- define layers here ---
        self.l1 = nn.Linear(state_size, hidden_size)
        self.l2 = nn.Linear(action_size, hidden_size)
        self.l3 = nn.Linear(hidden_size * 2, hidden_size * 2)
        self.l4 = nn.Linear(hidden_size * 2, hidden_size)
        self.l5 = nn.Linear(hidden_size, int(hidden_size / 2))
        self.l6 = nn.Linear(int(hidden_size / 2), int(hidden_size / 2 ** 2))
        self.l7 = nn.Linear(int(hidden_size / 2 ** 2), 1)

        # Q2
        # --- define layers here ---
        self.l8 = nn.Linear(state_size, hidden_size)
        self.l9 = nn.Linear(action_size, hidden_size)
        self.l10 = nn.Linear(hidden_size * 2, hidden_size * 2)
        self.l11 = nn.Linear(hidden_size * 2, hidden_size)
        self.l12 = nn.Linear(hidden_size, int(hidden_size / 2))
        self.l13 = nn.Linear(int(hidden_size / 2), int(hidden_size / 2 ** 2))
        self.l14 = nn.Linear(int(hidden_size / 2 ** 2), 1)

        self.layer_norm1 = nn.LayerNorm(hidden_size)

        self.apply(super().init_weights)

    def forward(self, states, actions):

        xs = torch.relu(self.l1(states))
        xa = torch.relu(self.l2(actions))
        x = torch.cat((xs, xa), dim=1)
        x = torch.relu(self.l3(x))
        x = torch.relu(self.l4(x))
        x = torch.relu(self.l5(x))
        x = torch.relu(self.l6(x))
        x1 = self.l7(x)

        xs = torch.relu(self.l8(states))
        xa = torch.relu(self.l9(actions))
        x = torch.cat((xs, xa), dim=1)
        x = torch.relu(self.l10(x))
        x = torch.relu(self.l11(x))
        x = torch.relu(self.l12(x))
        x = torch.relu(self.l13(x))
        x2 = self.l14(x)

        return x1, x2

    def Q1_forward(self, states, actions):
        xs = torch.relu(self.l1(states))
        xa = torch.relu(self.l2(actions))
        x = torch.cat((xs, xa), dim=1)
        x = torch.relu(self.l3(x))
        x = torch.relu(self.l4(x))
        x = torch.relu(self.l5(x))
        x = torch.relu(self.l6(x))
        x1 = self.l7(x)
        return x1

class TD3(OffPolicyAgent):
    def __init__(self, device, sim_speed):
        super().__init__(device, sim_speed)

        # DRL parameters
        self.noise = OUNoise(action_space=self.action_size, max_sigma=0.1, min_sigma=0.1, decay_period=8000000)

        # TD3 parameters
        self.policy_noise   = POLICY_NOISE
        self.noise_clip     = POLICY_NOISE_CLIP
        self.policy_freq    = POLICY_UPDATE_FREQUENCY

        self.last_actor_loss = 0

        self.actor = self.create_network(Actor, 'actor')
        self.actor_target = self.create_network(Actor, 'target_actor')
        self.actor_optimizer = self.create_optimizer(self.actor)

        self.critic = self.create_network(Critic, 'critic')
        self.critic_target = self.create_network(Critic, 'target_critic')
        self.critic_optimizer = self.create_optimizer(self.critic)

        self.hard_update(self.actor_target, self.actor)
        self.hard_update(self.critic_target, self.critic)

    def get_action(self, state, is_training, step, visualize=False):
        state = torch.from_numpy(np.asarray(state, np.float32)).to(self.device)
        action = self.actor(state, visualize)
        if is_training:
            noise = torch.from_numpy(copy.deepcopy(self.noise.get_noise(step))).to(self.device)
            action = torch.clamp(torch.add(action, noise), -1.0, 1.0)
        return action.detach().cpu().data.numpy().tolist()

    def get_action_random(self):
        return [np.clip(np.random.uniform(-1.0, 1.0), -1.0, 1.0), np.clip(np.random.uniform(-1.0, 1.0), -1.0, 1.0)]

    def train(self, state, action, reward, state_next, done):
        noise = (torch.randn_like(action) * self.policy_noise).clamp(-self.noise_clip, self.noise_clip)
        action_next = (self.actor_target(state_next) + noise).clamp(-1.0, 1.0)
        Q1_next, Q2_next = self.critic_target(state_next, action_next)
        Q_next = torch.min(Q1_next, Q2_next)

        Q_target = reward + (1 - done) * self.discount_factor * Q_next
        Q1, Q2 = self.critic(state, action)

        loss_critic = self.loss_function(Q1, Q_target) + self.loss_function(Q2, Q_target)
        self.critic_optimizer.zero_grad()
        loss_critic.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), max_norm=2.0, norm_type=2)
        self.critic_optimizer.step()

        if self.iteration % self.policy_freq == 0:
            # optimize actor
            loss_actor = -1 * self.critic.Q1_forward(state, self.actor(state)).mean()
            self.actor_optimizer.zero_grad()
            loss_actor.backward()
            nn.utils.clip_grad_norm_(self.actor.parameters(), max_norm=2.0, norm_type=2)
            self.actor_optimizer.step()

            self.soft_update(self.actor_target, self.actor, self.tau)
            self.soft_update(self.critic_target, self.critic, self.tau)
            self.last_actor_loss = loss_actor.mean().detach().cpu()
        return [loss_critic.mean().detach().cpu(), self.last_actor_loss]