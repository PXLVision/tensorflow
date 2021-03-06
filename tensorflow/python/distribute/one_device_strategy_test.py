# Copyright 2018 The TensorFlow Authors. All Rights Reserved.
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
"""Tests for class OneDeviceStrategy."""

from tensorflow.python import tf2
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.distribute import combinations
from tensorflow.python.distribute import distribute_lib
from tensorflow.python.distribute import input_lib
from tensorflow.python.distribute import strategy_combinations
from tensorflow.python.distribute import strategy_test_lib
from tensorflow.python.eager import context
from tensorflow.python.eager import test
from tensorflow.python.framework import device as tf_device


@combinations.generate(
    combinations.combine(
        distribution=[
            strategy_combinations.one_device_strategy,
            strategy_combinations.one_device_strategy_gpu
        ],
        mode=["eager", "graph"]))
class OneDeviceStrategyTest(
    strategy_test_lib.DistributionTestBase,
    strategy_test_lib.OneDeviceDistributionTestBase):

  def testMinimizeLoss(self, distribution):
    if context.executing_eagerly():
      self._test_minimize_loss_eager(distribution)
    else:
      self._test_minimize_loss_graph(distribution)

  def testReplicaId(self, distribution):
    self._test_replica_id(distribution)

  def testCallAndMergeExceptions(self, distribution):
    self._test_call_and_merge_exceptions(distribution)

  def testReplicateDataset(self, distribution):
    if tf2.enabled() and not context.executing_eagerly():
      self.skipTest("Skipping test since we do not support graph mode in TF 2")
    dataset_fn = lambda: dataset_ops.Dataset.range(10)
    expected_values = [[i] for i in range(10)]
    input_fn = self._input_fn_to_test_input_context(
        dataset_fn,
        expected_num_replicas_in_sync=1,
        expected_num_input_pipelines=1,
        expected_input_pipeline_id=0)
    self._test_input_fn_iterable(distribution, input_fn, expected_values)

  def testMakeInputFnIteratorWithDataset(self, distribution):
    dataset_fn = lambda: dataset_ops.Dataset.range(10)
    expected_values = [[i] for i in range(10)]
    input_fn = self._input_fn_to_test_input_context(
        dataset_fn,
        expected_num_replicas_in_sync=1,
        expected_num_input_pipelines=1,
        expected_input_pipeline_id=0)
    iterator = distribution.make_input_fn_iterator(input_fn)
    self._test_input_fn_iterator(
        iterator, distribution.extended.worker_devices, expected_values)

  def testMakeInputFnIteratorWithCallable(self, distribution):
    def fn():
      dataset = dataset_ops.Dataset.range(10)
      it = dataset_ops.make_one_shot_iterator(dataset)
      return it.get_next
    expected_values = [[i] for i in range(10)]
    input_fn = self._input_fn_to_test_input_context(
        fn,
        expected_num_replicas_in_sync=1,
        expected_num_input_pipelines=1,
        expected_input_pipeline_id=0)
    iterator = distribution.make_input_fn_iterator(input_fn)
    self._test_input_fn_iterator(
        iterator, distribution.extended.worker_devices, expected_values,
        test_reinitialize=False, ignore_order=True)

  def testNumpyDataset(self, distribution):
    self._test_numpy_dataset(distribution)

  def testRun(self, distribution):
    self._test_run(distribution)

  def testAllReduceSum(self, distribution):
    self._test_all_reduce_sum(distribution)

  def testAllReduceSumGradients(self, distribution):
    self._test_all_reduce_sum_gradients(distribution)

  def testAllReduceSumGradientTape(self, distribution):
    self._test_all_reduce_sum_gradient_tape(distribution)

  def testAllReduceMean(self, distribution):
    self._test_all_reduce_mean(distribution)

  def testAllReduceMeanGradients(self, distribution):
    self._test_all_reduce_mean_gradients(distribution)

  def testAllReduceMeanGradientTape(self, distribution):
    self._test_all_reduce_mean_gradient_tape(distribution)

  def testTrainableVariables(self, distribution):
    self._test_trainable_variable(distribution)

  def test_prefetch_to_device_dataset(self, distribution):
    input_options = distribute_lib.InputOptions(
        experimental_fetch_to_device=True)
    dataset = dataset_ops.Dataset.range(100)
    dataset = dataset.batch(distribution.num_replicas_in_sync)
    dataset = distribution.experimental_distribute_dataset(
        dataset, options=input_options)
    if context.executing_eagerly():
      item = next(iter(dataset))
    else:
      if isinstance(dataset, input_lib.DistributedDatasetV1):
        item = dataset.make_initializable_iterator().get_next()
      else:
        self.skipTest("unsupported test combination")
    device_types = (
        tf_device.DeviceSpec.from_string(item.device).device_type)
    expected_device_types = (
        tf_device.DeviceSpec.from_string(
            distribution.extended.worker_devices[0]).device_type)
    self.assertAllEqual(device_types, expected_device_types)

  def test_prefetch_to_host_dataset(self, distribution):
    input_options = distribute_lib.InputOptions(
        experimental_fetch_to_device=False)
    dataset = dataset_ops.Dataset.range(100)
    dataset = dataset.batch(distribution.num_replicas_in_sync)
    dataset = distribution.experimental_distribute_dataset(
        dataset, options=input_options)
    if context.executing_eagerly():
      item = next(iter(dataset))
    else:
      if isinstance(dataset, input_lib.DistributedDatasetV1):
        item = dataset.make_initializable_iterator().get_next()
      else:
        self.skipTest("unsupported test combination")
    self.assertAllEqual(
        tf_device.DeviceSpec.from_string(item.device).device_type, "CPU")


@combinations.generate(
    combinations.combine(
        distribution=[
            strategy_combinations.one_device_strategy_on_worker_1,
            strategy_combinations.one_device_strategy_gpu_on_worker_1
        ],
        mode=["eager", "graph"]))
class OneDeviceStrategyOnRemoteWorkerTest(
    strategy_test_lib.DistributionTestBase,
    strategy_test_lib.OneDeviceDistributionTestBase):

  def testDeviceAndInputDeviceAreColocated(self, distribution):
    self._test_device_and_input_device_are_colocated(distribution)

  def testDeviceAndInputDeviceAreColocatedWithFunction(self, distribution):
    self._test_device_and_input_device_are_colocated_with_function(distribution)


if __name__ == "__main__":
  test.main()
