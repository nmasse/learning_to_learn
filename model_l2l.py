import tensorflow as tf
import numpy as np
import task
import matplotlib.pyplot as plt
from parameters import par
from convolutional_layers import apply_convolutional_layers
import os, sys

# Ignore "use compiled version of TensorFlow" errors
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
print('TensorFlow version:\t', tf.__version__)
print('Using EI Network:\t', par['EI'])
print('Synaptic configuration:\t', par['synapse_config'], "\n")

"""
Model setup and execution
"""
class Model:

    def __init__(self, input_data, target_data, actual_reward, pred_reward, actual_action, advantage, mask, new_trial, h_init):

        # Load the input activity, the target data, and the training mask for this batch of trials
        self.input_data = tf.unstack(input_data, axis=0)
        self.target_data = tf.unstack(target_data, axis=0)
        self.pred_reward = tf.unstack(pred_reward, axis=0)
        self.actual_action = tf.unstack(actual_action, axis=0)
        self.actual_reward = tf.unstack(actual_reward, axis=0)
        self.advantage = tf.unstack(advantage, axis=0)
        self.new_trial = tf.unstack(new_trial)
        self.W_ei = tf.constant(par['EI_matrix'])

        self.time_mask = tf.unstack(mask, axis=0)

        # Load the initial hidden state activity to be used at the start of each trial
        self.h_init = h_init

        # Build the TensorFlow graph
        self.rnn_cell_loop(self.h_init)

        # Train the model
        self.optimize()
    """

    def convolutional_layers()

    for rnn_input self.input_data:

        x = apply_convolutional_layers(rnn_input, par['conv_weight_fn'])
        self.conv_output = tf.transpose(x)

    """

    def rnn_cell_loop(self, h):


        self.W_ei = tf.constant(par['EI_matrix'])
        self.h = [] # RNN activity
        self.pol_out = [] # policy output
        self.val_out = [] # value output
        self.syn_x = [] # STP available neurotransmitter
        self.syn_u = [] # STP calcium concentration

        # we will add the first element to these lists since we need to input the previous action and reward
        # into the RNN
        self.action = []
        self.action.append(tf.constant(np.zeros((par['n_pol'], par['batch_size']), dtype = np.float32)))
        self.reward = []
        self.reward.append(tf.constant(np.zeros((par['n_val'], par['batch_size']), dtype = np.float32)))

        self.mask = []
        self.mask.append(tf.constant(np.ones((1, par['batch_size']), dtype = np.float32)))

        """
        Initialize weights and biases
        """
        with tf.variable_scope('recurrent_pol'):
            if par['include_ff_layer']:
                W_in0 = tf.get_variable('W_in0', initializer = par['W_in0_init'])
                b_in0 = tf.get_variable('b_in0', initializer = par['b_in0_init'])
            W_in1 = tf.get_variable('W_in1', initializer = par['W_in1_init'])
            W_rnn = tf.get_variable('W_rnn', initializer = par['W_rnn_pol_init'])
            b_rnn = tf.get_variable('b_rnn', initializer = par['b_rnn_init'])
            W_reward_pos = tf.get_variable('W_reward_pos', initializer = par['W_reward_pos_init'])
            W_reward_neg = tf.get_variable('W_reward_neg', initializer = par['W_reward_neg_init'])
            W_pol_out = tf.get_variable('W_pol_out', initializer = par['W_pol_out_init'])
            b_pol_out = tf.get_variable('b_pol_out', initializer = par['b_pol_out_init'])
            W_action = tf.get_variable('W_action', initializer = par['W_action_init'])
            W_val_out = tf.get_variable('W_val_out', initializer = par['W_val_out_init'])
            b_val_out = tf.get_variable('b_val_out', initializer = par['b_val_out_init'])


        """
        Loop through the neural inputs to the RNN, indexed in time
        """
        for rnn_input, target, time_mask, new_trial in zip(self.input_data, self.target_data, self.time_mask, self.new_trial):

            x = apply_convolutional_layers(rnn_input, par['conv_weight_fn'])
            self.conv_output = tf.transpose(x)

            h, action, pol_out, val_out, mask, reward  = self.rnn_cell(self.conv_output, h, self.action[-1], self.reward[-1], \
                self.mask[-1], target, time_mask, new_trial)

            self.h.append(h)
            self.action.append(tf.transpose(action))
            self.pol_out.append(pol_out)
            self.val_out.append(val_out)
            self.mask.append(mask)
            self.reward.append(tf.reshape(reward, [par['n_val'], par['batch_size']]))

        self.mask = self.mask[1:]
        # actions will produce a reward on the next time step
        self.reward = self.reward[1:]
        self.action = self.action[1:]


    def rnn_cell(self, x, h, prev_action, prev_reward, mask, target, time_mask, new_trial):

        # in TF v1.8, I can use reuse = tf.AUTO_REUSE, and get rid of weight initialization above
        with tf.variable_scope('recurrent_pol', reuse = True):
            if par['include_ff_layer']:
                W_in0 = tf.get_variable('W_in0')
                b_in0 = tf.get_variable('b_in0')
            W_in1 = tf.get_variable('W_in1')
            W_rnn = tf.get_variable('W_rnn')
            W_reward_pos = tf.get_variable('W_reward_pos')
            W_reward_neg = tf.get_variable('W_reward_neg')
            b_rnn = tf.get_variable('b_rnn')
            W_pol_out = tf.get_variable('W_pol_out')
            b_pol_out = tf.get_variable('b_pol_out')
            W_action = tf.get_variable('W_action')
            W_val_out = tf.get_variable('W_val_out')
            b_val_out = tf.get_variable('b_val_out')

        # Modify the recurrent weights if using excitatory/inhibitory neurons
        if par['EI']:
            W_rnn = tf.matmul(tf.nn.relu(W_rnn), self.W_ei)

        # pass the output of the convolutional layers through the feedforward layer(s)
        if par['include_ff_layer']:
            x = tf.nn.relu(tf.matmul(W_in0, x) + b_in0)

        h = tf.nn.relu(h*(1-par['alpha']) + par['alpha']*(tf.matmul(W_in1, x) + tf.matmul(W_rnn, h) \
            + mask*(tf.matmul(W_reward_pos, tf.nn.relu(prev_reward)) + tf.matmul(W_reward_neg, tf.nn.relu(-prev_reward)) \
            + tf.matmul(W_action, prev_action)) + b_rnn + tf.random_normal([par['n_hidden'], par['batch_size']], 0, par['noise_rnn'], dtype=tf.float32)))

        # calculate the policy output and choose an action
        pol_out = tf.matmul(W_pol_out, h) + b_pol_out
        action_index = tf.multinomial(tf.transpose(pol_out), 1)
        action = tf.one_hot(tf.squeeze(action_index), par['n_pol'])
        action = tf.reshape(action, [par['batch_size'], par['n_pol']])
        pol_out = tf.nn.softmax(pol_out, dim = 0)

        val_out = tf.matmul(W_val_out, h) + b_val_out

        # if previous reward was non-zero, then end the trial, unless the new trial signal cue is on
        continue_trial = tf.cast(tf.equal(prev_reward, 0.), tf.float32)
        mask *= continue_trial
        mask = tf.maximum(new_trial, mask)
        continue_trial = tf.maximum(new_trial, continue_trial)

        reward = tf.reduce_sum(action*target, axis = 1)*mask*time_mask

        return h, action, pol_out, val_out, mask, reward


    def optimize(self):

        epsilon = 1e-7
        """
        Calculate the loss functions and optimize the weights
        """
        #Z = tf.reduce_sum(tf.stack([tf.reduce_sum(time_mask*mask) for (mask, time_mask) in zip(self.mask, self.time_mask)]))

        self.pol_loss = -tf.reduce_sum(tf.stack([advantage*time_mask*mask*tf.reduce_sum(act*tf.log((epsilon + pol_out)), axis = 0) \
            for (pol_out, advantage, act, mask, time_mask) in zip(self.pol_out, self.advantage, \
            self.actual_action, self.mask, self.time_mask)]))

        self.entropy_loss = -tf.reduce_sum(tf.stack([time_mask*mask*pol_out*tf.log(epsilon+pol_out) \
            for (pol_out, mask, time_mask) in zip(self.pol_out, self.mask, self.time_mask)]))

        self.val_loss = 0.5*tf.reduce_sum(tf.stack([time_mask*mask*tf.square(val_out - actual_reward) \
                for (val_out, mask, time_mask, actual_reward) in zip(self.val_out, self.mask, self.time_mask, self.actual_reward)]))

        # L2 penalty term on hidden state activity to encourage low spike rate solutions
        self.spike_loss = tf.reduce_mean(tf.stack([par['spike_cost']*tf.reduce_mean(tf.square(h), axis=0) for h in self.h]))

        adam_opt = tf.train.AdamOptimizer(learning_rate = par['learning_rate'])

        """
        Apply any applicable weights masks to the gradient and clip
        """
        grads_and_vars_pol = adam_opt.compute_gradients(self.pol_loss + self.val_loss + self.spike_loss - 0.1*self.entropy_loss, var_list = pol_vars)
        capped_gvs = []
        for grad, var in grads_and_vars_pol:
            if var.name == "recurrent_pol/W_rnn:0":
                grad *= par['w_rnn_mask']
            capped_gvs.append((tf.clip_by_norm(grad, 1.), var))
        self.train_opt = adam_opt.apply_gradients(capped_gvs)


def main(gpu_id = None):

    if gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu_id

    """
    Reset TensorFlow before running anything
    """
    tf.reset_default_graph()

    """
    Create the stimulus class to generate trial paramaters and input activity
    """
    stim = task.Stimulus()

    """
    Define all placeholder
    """
    par['n_time_steps'] = 60 # TEMPORARAY FIX!!!!
    mask = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['batch_size']])
    x = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['batch_size'], 32, 32, 3])  # input data
    target = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['batch_size'], par['n_pol']])  # input data
    actual_reward = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['n_val'], par['batch_size']])
    pred_reward = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['n_val'], par['batch_size']])
    actual_action = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['n_pol'], par['batch_size']])
    advantage  = tf.placeholder(tf.float32, shape=[par['n_time_steps'], par['n_val'], par['batch_size']])
    new_trial  = tf.placeholder(tf.float32, shape=[par['n_time_steps']])
    h_init =  tf.placeholder(tf.float32, shape=[par['n_hidden'],par['batch_size']])

    config = tf.ConfigProto()
    #config.gpu_options.allow_growth=True

    with tf.Session(config=config) as sess:

        if gpu_id is not None:
            model = Model(x, target, actual_reward, pred_reward, actual_action, advantage, mask, new_trial, h_init)
        else:
            with tf.device("/gpu:0"):
                model = Model(x, target, actual_reward, pred_reward, actual_action, advantage, mask, new_trial, h_init)
        init = tf.global_variables_initializer()
        sess.run(init)

        # keep track of the model performance across training
        model_performance = {'accuracy': [], 'loss': [], 'perf_loss': [], 'spike_loss': [], 'trial': []}

        hidden_init = np.array(par['h_init'])

        for i in range(par['num_iterations']):

            # generate batch of batch_train_size
            input_data, reward_data, trial_mask, new_trial_signal = stim.generate_batch_task1(0)

            """
            Run the model
            """
            pol_out_list, val_out_list, h, action, mask_list, reward_list = sess.run([model.pol_out, model.val_out, model.h, model.action, \
                 model.mask, model.reward], {x: input_data, target: reward_data, mask: trial_mask, new_trial: new_trial_signal, h_init:hidden_init})


            pol_out = np.stack(pol_out_list)
            val_out = np.stack(val_out_list)
            stacked_mask = np.stack(mask_list)[:,0,:]*trial_mask
            trial_reward = np.stack(reward_list)
            future_reward = np.zeros_like(trial_reward)
            """
            for j in range(par['n_time_steps'] - 1):
                future_reward[j,:] = np.sum(trial_reward[j+1:,:],axis = 0)/np.sum(stacked_mask,axis=0,keepdims=True)
            """

            adv = trial_reward - val_out
            trial_action = np.stack(action)

            _, pol_loss, val_loss, entropy_loss = sess.run([model.train_opt, model.pol_loss, model.val_loss, model.entropy_loss], \
                {x: input_data, target: reward_data, mask: trial_mask, actual_reward: trial_reward, pred_reward: val_out, \
                actual_action:trial_action, advantage:adv, new_trial: new_trial_signal, h_init:hidden_init})

            hidden_init = np.array(h[-1])

            """
            Save the network model and output model performance to screen
            """
            if i%par['iters_between_outputs']==0 and i > 0:
                r = np.squeeze(np.sum(np.stack(trial_reward),axis=0))
                print('Mean mask' , np.mean(stacked_mask), ' pol loss ', pol_loss, ' val loss ', val_loss, \
                    ' entropy_loss', entropy_loss, ' reward ', np.mean(r), np.max(r), ' mean activity ', np.mean(np.stack(h)))

                if i%100==0 and i>0:
                    for k in range(4):
                        plt.subplot(4,2,2*k+1)
                        plt.plot(adv[:,0,k],'b')
                        plt.plot(stacked_mask[:,k],'r')
                        plt.plot(val_out[:,0,k],'g')
                        plt.subplot(4,2,2*k+2)
                        plt.plot(pol_out[:,0,k],'b')
                        plt.plot(pol_out[:,1,k],'r')
                        plt.plot(pol_out[:,2,k],'g')
                    plt.show()


def append_model_performance(model_performance, accuracy, loss, perf_loss, spike_loss, trial_num):

    model_performance['accuracy'].append(accuracy)
    model_performance['loss'].append(loss)
    model_performance['perf_loss'].append(perf_loss)
    model_performance['spike_loss'].append(spike_loss)
    model_performance['trial'].append(trial_num)

    return model_performance

def eval_weights():

    with tf.variable_scope('rnn_cell', reuse=True):
        W_in = tf.get_variable('W_in')
        W_rnn = tf.get_variable('W_rnn')
        b_rnn = tf.get_variable('b_rnn')

    with tf.variable_scope('output', reuse=True):
        W_out = tf.get_variable('W_out')
        b_out = tf.get_variable('b_out')

    weights = {
        'w_in'  : W_in.eval(),
        'w_rnn' : W_rnn.eval(),
        'w_out' : W_out.eval(),
        'b_rnn' : b_rnn.eval(),
        'b_out'  : b_out.eval()
    }

    return weights

def print_results(iter_num, trials_per_iter, perf_loss, spike_loss, state_hist, accuracy):

    print('Iter. {:4d}'.format(iter_num) + ' | Accuracy {:0.4f}'.format(accuracy) +
      ' | Perf loss {:0.4f}'.format(perf_loss) + ' | Spike loss {:0.4f}'.format(spike_loss) +
      ' | Mean activity {:0.4f}'.format(np.mean(state_hist)))