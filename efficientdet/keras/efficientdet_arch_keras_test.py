# Lint as: python3
# Copyright 2020 Google Research. All Rights Reserved.
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
"""Tests for efficientdet_arch_keras."""
from absl import logging
import tensorflow.compat.v1 as tf

import efficientdet_arch as legacy_arch
import hparams_config
import utils
import numpy as np
from keras import efficientdet_arch_keras


class KerasBiFPNTest(tf.test.TestCase):

  def test_variables(self):
    config = hparams_config.get_efficientdet_config()
    feat_sizes = utils.get_feat_sizes(config.image_size, config.max_level)
    with tf.Graph().as_default():
      feats = [
          tf.random.uniform([1, 64, 64, 40]),
          tf.random.uniform([1, 32, 32, 112]),
          tf.random.uniform([1, 16, 16, 320]),
          tf.random.uniform([1, 8, 8, 64]),
          tf.random.uniform([1, 4, 4, 64])
      ]
      efficientdet_arch_keras.build_bifpn_layer(feats, feat_sizes, config)
      vars1 = [var.name for var in tf.global_variables()]

    with tf.Graph().as_default():
      feats = [
          tf.random.uniform([1, 64, 64, 40]),
          tf.random.uniform([1, 32, 32, 112]),
          tf.random.uniform([1, 16, 16, 320]),
          tf.random.uniform([1, 8, 8, 64]),
          tf.random.uniform([1, 4, 4, 64])
      ]
      legacy_arch.build_bifpn_layer(feats, feat_sizes, config)
      vars2 = [var.name for var in tf.global_variables()]

    self.assertEqual(vars1, vars2)


class KerasTest(tf.test.TestCase):
  def test_model_variables(self):
    with tf.Graph().as_default():
      feats = tf.random.uniform([1, 512, 512, 3])
      efficientdet_arch_keras.efficientdet('efficientdet-d0')(feats)
      vars1 = [var.name for var in tf.global_variables()]

    with tf.Graph().as_default():
      feats = tf.random.uniform([1, 512, 512, 3])
      legacy_arch.efficientdet(feats, 'efficientdet-d0')
      vars2 = [var.name for var in tf.global_variables()]

    self.assertEqual(vars1, vars2)

  def test_resample_feature_map(self):
    feat = tf.random.uniform([1, 16, 16, 320])
    for apply_bn in [True, False]:
      for is_training in [True, False]:
        for strategy in ['tpu', '']:
          with self.subTest(apply_bn=apply_bn,
                            is_training=is_training,
                            strategy=strategy):
            tf.random.set_random_seed(111111)
            expect_result = legacy_arch.resample_feature_map(
                feat,
                name='resample_p0',
                target_height=8,
                target_width=8,
                target_num_channels=64,
                apply_bn=apply_bn,
                is_training=is_training,
                strategy=strategy)
            tf.random.set_random_seed(111111)
            resample_layer = efficientdet_arch_keras.ResampleFeatureMap(
                name='resample_p0',
                target_height=8,
                target_width=8,
                target_num_channels=64,
                apply_bn=apply_bn,
                is_training=is_training,
                strategy=strategy)
            actual_result = resample_layer(feat)
            self.assertAllCloseAccordingToType(expect_result, actual_result)

  def test_op_name(self):
    with tf.Graph().as_default():
      feat = tf.random.uniform([1, 16, 16, 320])
      resample_layer = efficientdet_arch_keras.ResampleFeatureMap(
          name='resample_p0',
          target_height=8,
          target_width=8,
          target_num_channels=64)
      resample_layer(feat)
      vars1 = [var.name for var in tf.trainable_variables()]

    with tf.Graph().as_default():
      feat = tf.random.uniform([1, 16, 16, 320])
      legacy_arch.resample_feature_map(feat,
                                       name='p0',
                                       target_height=8,
                                       target_width=8,
                                       target_num_channels=64)
      vars2 = [var.name for var in tf.trainable_variables()]

    self.assertEqual(vars1, vars2)


class EfficientDetVariablesNamesTest(tf.test.TestCase):

  def build_model(self, keras=False):
    with tf.Graph().as_default():
      config = hparams_config.get_efficientdet_config()
      inputs_shape = [1, 512, 512, 3]
      inputs = dict()
      for i in range(config.min_level, config.max_level + 1):
        inputs[i] = tf.ones(shape=inputs_shape, name='input', dtype=tf.float32)

      if not keras:
        legacy_arch.build_class_and_box_outputs(inputs, config)
      else:
        efficientdet_arch_keras.build_class_and_box_outputs(inputs, config)
      return [n.name for n in tf.global_variables()]

  def test_graph_variables_name_compatibility(self):
    legacy_names = self.build_model(False)
    keras_names = self.build_model(True)

    self.assertEqual(legacy_names, keras_names)


if __name__ == '__main__':
  logging.set_verbosity(logging.WARNING)
  tf.test.main()
