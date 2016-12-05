import numpy as np
import collections

Datasets = collections.namedtuple('Datasets', ['train', 'validation', 'test'])

class Dataset(object):
    def __init__(self, examples, labels):
        """Construct a DataSet.
        one_hot arg is used only if fake_data is true.  `dtype` can be either
            `uint8` to leave the input as `[0, 255]`, or `float32` to rescale into
        `[0, 1]`.
        """
        #assert images.shape[0] == labels.shape[0]
        self._num_examples = examples.shape[0]
        self._examples = examples
        self._labels = labels
        self._epochs_completed = 0
        self._index_in_epoch = 0

    @property
    def examples(self):
        return self._examples
    
    @property
    def labels(self):
        return self._labels
    
    @property
    def num_examples(self):
        return self._num_examples
    
    @property
    def epochs_completed(self):
        return self._epochs_completed

    def next_batch_samples(self, batch_size):
        """Return the next `batch_size` examples from this data set."""
    
        start = self._index_in_epoch
        self._index_in_epoch += batch_size
        if self._index_in_epoch > self._num_examples:
            # Shuffle the data
            perm = np.arange(self._num_examples)
            np.random.shuffle(perm)
            self._examples = self._examples[perm]
            # Start next epoch
            start = 0
            self._index_in_epoch = batch_size
            assert batch_size <= self._num_examples
        elif self._index_in_epoch == self._num_examples:
            # Finished epoch
            self._epochs_completed += 1
            
        end = self._index_in_epoch
        return self._examples[start:end]
    
    def next_batch_examples(self, batch_size):
        """Return the next `batch_size` examples from this data set."""
    
        start = self._index_in_epoch
        self._index_in_epoch += batch_size
        if self._index_in_epoch > self._num_examples:
            # Shuffle the data
            perm = np.arange(self._num_examples)
            np.random.shuffle(perm)
            self._examples = self._examples[perm]
            self._labels = self._labels[perm]
            # Start next epoch
            start = 0
            self._index_in_epoch = batch_size
            assert batch_size <= self._num_examples
        elif self._index_in_epoch == self._num_examples:
            # Finished epoch
            self._epochs_completed += 1
            
        end = self._index_in_epoch
        return self._examples[start:end], self._labels[start:end]

