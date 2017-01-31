# Copyright 2015 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""A binary to train CIFAR-10 using a single GPU.
Accuracy:
cifar10_train.py achieves ~86% accuracy after 100K steps (256 epochs of
data) as judged by cifar10_eval.py.
Speed: With batch_size 128.
System        | Step Time (sec/batch)  |     Accuracy
------------------------------------------------------------------
1 Tesla K20m  | 0.35-0.60              | ~86% at 60K steps  (5 hours)
1 Tesla K40m  | 0.25-0.35              | ~86% at 100K steps (4 hours)
Usage:
Please see the tutorial and website for how to download the CIFAR-10
data set, compile the program and train the model.
http://tensorflow.org/tutorials/deep_cnn/
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import types

from datetime import datetime
import os.path
import time

import numpy as np
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf

import small_cnn as fish_cnn

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_string('train_dir', 'tmp/fish_train',
                           """Directory where to write event logs """
                           """and checkpoint.""")
#modified the steps
tf.app.flags.DEFINE_integer('max_steps', 10,
                            """Number of batches to run.""")
tf.app.flags.DEFINE_boolean('log_device_placement', False,
                            """Whether to log device placement.""")


# def makePrintingOp(op, name=None):
#     with tf.op_scope([???], name=name):

def whatIsIt(tfThing):
    if isinstance(tfThing, tf.Operation):
        return ('Operation %s of type %s, inputs %s'
                % (tfThing.name, tfThing.type,
                   [t.name for t in tfThing.inputs]))
    elif isinstance(tfThing, tf.Tensor):
        return ('Tensor %s with shape %s'
                % (tfThing.name, tfThing.get_shape()))
    else:
        return 'I have no idea'


# def monkeyPatchTensor(t):
#     oldEval = t.eval
#     oldStr = t.__str__
#     def newEval(feed_dict, sess):
#         print('Evaluating %s' % t.name)
#         result = oldEval(feed_dict, sess)
#         print('%s.eval(...) -> %s' % (t.name, result))
#         return result
#     t.eval = types.MethodType(newEval, t)
#     def newStr(self):
#         return('WRAP(' + oldStr() + ')')
#     t.__str__ = types.MethodType(newStr, t)
#     print ('monkeypatch in progress: %s' % t.__str__())
#     print ('More in progress: %s' % str(t))
#     return t
#     
# 
# def monkeyPatchTensorClass(tC):
#     oldEval = tC.eval
#     oldStr = tC.__str__
#     def newEval(self, feed_dict, sess):
#         print('Evaluating %s' % self.name)
#         result = oldEval(self, feed_dict, sess)
#         print('%s.eval(...) -> %s' % (self.name, result))
#         return result
#     tC.eval = newEval
#     def newStr(self):
#         return('WRAP(' + oldStr(self) + ')')
#     tC.__str__ = newStr
    

def train():
  """Train CIFAR-10 for a number of steps."""
  with tf.Graph().as_default():
    global_step = tf.Variable(0, trainable=False)

    # Get images and labels for CIFAR-10.
    inputs = fish_cnn.inputs(shuffle=True,evall="train")

    images, labels= inputs

  

    # Build a Graph that computes the logits predictions from the
    # inference model.
    logits = fish_cnn.inference(images)

    # Calculate loss.
    loss = fish_cnn.loss(logits, labels)

    # Build a Graph that trains the model with one batch of examples and
    # updates the model parameters.
    train_op = fish_cnn.train(loss, global_step)

    # Create a saver.
    saver = tf.train.Saver(tf.all_variables())

    # Build the summary operation based on the TF collection of Summaries.
    summary_op = tf.merge_all_summaries()

    # Build an initialization operation to run below.
    init = tf.initialize_all_variables()

    print ("start a session")

    # Start running operations on the Graph.
    sess = tf.Session(config=tf.ConfigProto(
        log_device_placement=FLAGS.log_device_placement))
    sess.run(init)

    # Start the queue runners.
    tf.train.start_queue_runners(sess=sess)

    summary_writer = tf.train.SummaryWriter(FLAGS.train_dir, sess.graph)
    
    print ('type for logits is %s' % whatIsIt(logits))
    print ('type for loss is %s' % whatIsIt(loss))
    print ('type for train_op is %s' % whatIsIt(train_op))
    

    # This is from https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/client/timeline_test.py
    run_options = tf.RunOptions(trace_level=tf.RunOptions.NO_TRACE)
    run_metadata = tf.RunMetadata()


    print ("start on training")

    for step in xrange(FLAGS.max_steps):

        print (step)


        start_time = time.time()
        
        print ("start")
        _, loss_value = sess.run([train_op, loss],
                                 options=run_options,
                                 run_metadata=run_metadata)
        print ("end")
        duration = time.time() - start_time
      
        # More from https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/client/timeline_test.py
        if run_metadata.HasField('step_stats'):
            step_stats = run_metadata.step_stats
            tl = tf.python.client.timeline.Timeline(step_stats)
            ctf = tl.generate_chrome_trace_format()
            print('ctf: %s' % ctf)
        else:
            print('run_metadata has no steps')


        assert not np.isnan(loss_value), 'Model diverged with loss = NaN'

        if step % 1 == 0:
            num_examples_per_step = FLAGS.batch_size
            examples_per_sec = num_examples_per_step / duration
            sec_per_batch = float(duration)
    
            format_str = ('%s: step %d, loss = %.2f (%.1f examples/sec; %.3f '
                          'sec/batch)')
            print (format_str % (datetime.now(), step, loss_value,
                                 examples_per_sec, sec_per_batch))

        if step % 100 == 0:
            summary_str = sess.run(summary_op)
            summary_writer.add_summary(summary_str, step)

        # Save the model checkpoint periodically.
        if step % 1000 == 0 or (step + 1) == FLAGS.max_steps:
            checkpoint_path = os.path.join(FLAGS.train_dir, 'model.ckpt')
            saver.save(sess, checkpoint_path, global_step=step)

def main(argv=None):  # pylint: disable=unused-argument
  #cifar10.maybe_download_and_extract()
  if tf.gfile.Exists(FLAGS.train_dir):
    tf.gfile.DeleteRecursively(FLAGS.train_dir)
  tf.gfile.MakeDirs(FLAGS.train_dir)
  train()
  
if __name__ == '__main__':
  tf.app.run()






