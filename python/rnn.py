import math
import tensorflow as tf

from tensorflow.python.ops import math_ops
from tensorflow.python.ops.math_ops import sigmoid
from tensorflow.python.ops.math_ops import tanh
from tensorflow.python.ops import variable_scope
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import nn_ops


flags = tf.flags
flags.DEFINE_string("data_path", None, "data_path")
FLAGS = flags.FLAGS

class RNN(object):
    
    def __init__(self, input_size, state_size, label_size, activation=tanh):
        self._input_size = input_size
        self._state_size = state_size
        self._label_size = label_size
        self._activation = activation
    
    def cell_inference(self, cell_inputs, previous_state, scope=None, dropout=False):
        with variable_scope.variable_scope(scope or type(self).__name__):            
            state_weights = tf.get_variable("state_weights", \
                                            shape=[self._state_size, self._state_size])
#                 initializer= tf.random_uniform([self._state_size, self._state_size], \
#                                                -1.0/math.sqrt(self._state_size), \
#                                                1.0/math.sqrt(self._state_size)))
            input_weights = tf.get_variable("input_weights", \
                                            shape=[self._input_size, self._state_size])
#                 initializer= tf.random_uniform([self._input_size, self._state_size], \
#                                                -1.0/math.sqrt(self._input_size), \
#                                                1.0/math.sqrt(self._input_size)))
            b = tf.get_variable("b", initializer=tf.zeros([self._state_size]))
            c = tf.get_variable("c", initializer=tf.zeros([self._label_size]))
            
            if dropout:
                cell_inputs = nn_ops.dropout(cell_inputs, 0.8)

            if dropout:
                linear_states = math_ops.matmul(previous_state, state_weights) \
                    + math_ops.matmul(cell_inputs, input_weights) + b
            else:
                linear_states = math_ops.matmul(previous_state, state_weights) \
                    + math_ops.matmul(cell_inputs, tf.scalar_mul(0.8, input_weights)) + b
                    
            cell_states = self._activation(linear_states)
            
            output_weights = tf.get_variable("output_weight", \
                                             shape=[self._state_size, self._label_size])
#                 initializer= tf.random_uniform([self._state_size, self._label_size], \
#                                                -1.0/math.sqrt(self._state_size), \
#                                                1.0/math.sqrt(self._state_size)))
            if dropout:
                cell_outputs = math_ops.matmul(nn_ops.dropout(cell_states, 0.5), output_weights) + c
            else:
                cell_outputs = math_ops.matmul(cell_states, tf.scalar_mul(0.5, output_weights)) + c

        return cell_states, cell_outputs
    
    def reference(self, inputs, dropout=False):
        logits = []
        batch_size = inputs.get_shape()[0]
        time_steps = inputs.get_shape()[1] 
        previous_states = tf.zeros([batch_size, self._state_size], tf.float32)
        for time_step in range(time_steps):
            if time_step > 0: tf.get_variable_scope().reuse_variables()
            cell_states, cell_outputs = self.cell_inference(inputs[:,time_step,:], 
                                                           previous_states, 
                                                           dropout=dropout)
            logits.append(cell_outputs)
            previous_states = cell_states

        return logits
    
    def loss(self, logits, targets):
        time_steps = len(logits)
        
        crossents = []
        for time_step in range(time_steps):
            logit = logits[time_step]
            target = targets[time_step]
            crossent = nn_ops.sparse_softmax_cross_entropy_with_logits(
                logit, target)
            crossents.append(crossent)
          
        loss = tf.reduce_mean(math_ops.add_n(crossents))
#         loss = tf.reduce_mean(nn_ops.sparse_softmax_cross_entropy_with_logits(
#             logits[-1], targets))
        return loss
    
    def simple_loss(self, logits, targets, lamda=0.05):
        state_weights = tf.get_variable("state_weights", shape=[self._state_size, self._state_size])
        input_weights = tf.get_variable("input_weights", shape=[self._input_size, self._state_size])
        output_weights = tf.get_variable("output_weight", shape=[self._state_size, self._label_size])
        b = tf.get_variable("b", shape=[self._state_size])
        c = tf.get_variable("c", shape=[self._label_size])
        
                                        
        loss = tf.reduce_mean(nn_ops.sparse_softmax_cross_entropy_with_logits(
            logits[-1], targets)) + lamda * tf.nn.l2_loss(state_weights) + \
            lamda * tf.nn.l2_loss(input_weights) + \
            lamda * tf.nn.l2_loss(output_weights) + \
            lamda * tf.nn.l2_loss(b) + \
            lamda * tf.nn.l2_loss(c)
            
        return loss
    
    def evaluation(self, logits, labels):
        """Evaluate the quality of the logits at predicting the label.
        Args:
          logits: Logits tensor, float - [batch_size, NUM_CLASSES].
          labels: Labels tensor, int32 - [batch_size], with values in the
            range [0, NUM_CLASSES).
        Returns:
          A scalar int32 tensor with the number of examples (out of batch_size)
          that were predicted correctly.
        """
        # For a classifier model, we can use the in_top_k Op.
        # It returns a bool tensor with shape [batch_size] that is true for
        # the examples where the label is in the top k (here k=1)
        # of all logits for that example.
        #correct = tf.nn.in_top_k(logits[-1], labels, 1)
        predicts = tf.cast(tf.argmax(logits[-1], axis=1), tf.int32)
        correct = tf.equal(predicts, labels)
        # Return the number of true entries.
        return tf.reduce_sum(tf.cast(correct, tf.int32))
    
    def subjects_evaluation(self, logits, labels, time_steps):
        """Evaluate the quality of the logits at predicting the label.
        Args:
          logits: Logits tensor, float - [batch_size, NUM_CLASSES].
          labels: Labels tensor, int32 - [batch_size], with values in the
            range [0, NUM_CLASSES).
        Returns:
          A scalar int32 tensor with the number of examples (out of batch_size)
          that were predicted correctly.
        """
        # For a classifier model, we can use the in_top_k Op.
        # It returns a bool tensor with shape [batch_size] that is true for
        # the examples where the label is in the top k (here k=1)
        # of all logits for that example.
        predicts = logits[-1]
        subject_logits, subject_labels = self._get_subjects(predicts, labels, time_steps)
        predict_subject_labels = []
        for subject_logit in subject_logits:
            #subject_softmax = tf.nn.softmax(subject_logit)
            subject_predict_labels = tf.argmax(subject_logit, axis=1)
            positive_pred = tf.less(subject_predict_labels.get_shape()[0], \
                                    tf.scalar_mul(2, \
                                                  tf.cast(tf.reduce_sum(subject_predict_labels), tf.int32)))
            
            subject_predict_label = tf.cond(positive_pred, lambda: tf.Variable(1), lambda: tf.Variable(0))
            predict_subject_labels.append(subject_predict_label)
        
        correct_subjects = tf.equal(predict_subject_labels, subject_labels)
        correct_num = tf.reduce_sum(tf.cast(correct_subjects, tf.int32))
        return correct_num
    
    def _get_subjects(self, logits, labels, time_steps):
        subject_logits = []
        subject_labels = []
        
        group_size = 120/time_steps
        logtis_num = logits.get_shape()[0]
        #assert logtis_num % group_size == 0
        subjects_num = logtis_num / group_size
        
        for i in range(subjects_num):
            start = i*group_size
            end = i*group_size + group_size
            subject_logits.append(logits[start:end])
            subject_labels.append(labels[start])
        
        return subject_logits, subject_labels
    
    def train(self, loss, learning_rate):
        # Create the gradient descent optimizer with the given learning rate.
        #optimizer = tf.train.GradientDescentOptimizer(learning_rate)
        optimizer = tf.train.AdadeltaOptimizer(learning_rate)
        # Create a variable to track the global step.
        global_step = tf.Variable(0, name='global_step', trainable=False)
        # Use the optimizer to apply the gradients that minimize the loss    
        train_op = optimizer.minimize(loss)
        return train_op
     
