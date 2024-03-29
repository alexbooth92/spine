"""Module with a dataclass targeted at a batch index or list of indexes."""

import numpy as np
import torch
from dataclasses import dataclass
from warnings import warn
from typing import Union, List

from mlreco.utils.decorators import inherit_docstring

from .base import BatchBase

__all__ = ['IndexBatch']


@dataclass
@inherit_docstring(BatchBase)
class IndexBatch(BatchBase):
    """Batched index with the necessary methods to slice it.

    Attributes
    ----------
    offsets : Union[np.ndarray, torch.Tensor]
        (B) Offsets between successive indexes in the batch
    full_counts : Union[np.ndarray, torch.Tensor]
        (B) Number of index elements per entry in the batch. This
        is the same as counts if the underlying data is a single index
    """
    offsets: Union[np.ndarray, torch.Tensor]
    full_counts: Union[np.ndarray, torch.Tensor]

    def __init__(self, data, offsets, counts=None, full_counts=None,
                 batch_ids=None, batch_size=None, is_numpy=True):
        """Initialize the attributes of the class.

        Parameters
        ----------
        data : Union[np.ndarray, torch.Tensor, 
                     List[Union[np.ndarray, torch.Tensor]]]
            Simple batched index or list of indexes
        offsets : Union[List[int], np.ndarray, torch.Tensor]
            (B) Offsets between successive indexes in the batch
        counts : Union[List[int], np.ndarray, torch.Tensor], optional
            (B) Number of indexes in the batch
        full_counts : Union[List[int], np.ndarray, torch.Tensor], optional
            (B) Number of index elements per entry in the batch. This
            is the same as counts if the underlying data is a single index
        batch_ids : Union[List[int], np.ndarray, torch.Tensor], optional
            (I) Batch index of each of the clusters. If not specified, the
            assumption is that each count corresponds to a specific entry
        batch_size : int, optional
            Number of entries in the batch. Must be specified along batch_ids
        is_numpy : bool, default True
            Weather the underlying representation is `np.ndarray` or
            `torch.Tensor`. Must specify if the input list is empty
        """
        # Check weather the input is a single index or a list
        is_list = isinstance(data, (list, tuple)) or data.dtype == object

        # Initialize the base class
        if not is_list:
            init_data = data
        elif len(data):
            init_data = data[0]
        else:
            warn("The input list is empty, underlying data type arbitrary.")
            init_data = np.empty(0, dtype=np.int64)

        super().__init__(init_data, is_list=is_list)

        # Get the counts if they are not provided for free
        if counts is None:
            assert batch_ids is not None and batch_size is not None, (
                    "Must provide `batch_size` alongside `batch_ids`.")
            counts = self.get_counts(batch_ids, batch_size)

        else:
            batch_size = len(counts)

        # Get the number of index elements per entry in the batch
        if full_counts is None:
            assert not self.is_list, (
                    "When initializing an index list, provide `full_counts`")
            full_counts = counts

        # Cast
        counts = self._as_long(counts)
        full_counts = self._as_long(full_counts)
        offsets = self._as_long(offsets)

        # Do a couple of basic sanity checks
        assert self._sum(counts) == len(data), (
                "The `counts` provided do not add up to the index length")
        assert len(counts) == len(offsets), (
                "The number of `offsets` does not match the number of `counts`")

        # Get the boundaries between successive index using the counts
        edges = self.get_edges(counts)

        # Store the attributes
        self.data = data
        self.counts = counts
        self.full_counts = full_counts
        self.edges = edges
        self.offsets = offsets
        self.batch_size = batch_size

    def __getitem__(self, batch_id):
        """Returns a subset of the index corresponding to one entry.

        Parameters
        ----------
        batch_id : int
            Entry index
        """
        # Make sure the batch_id is sensible
        if batch_id >= self.batch_size:
            raise IndexError(f"Index {batch_id} out of bound for a batch size "
                             f"of ({self.batch_size})")

        # Return
        lower, upper = self.edges[batch_id], self.edges[batch_id + 1]
        if not self.is_list:
            return self.data[lower:upper] - self.offsets[batch_id]
        else:
            entry = np.empty(upper-lower, dtype=object)
            entry[:] = self.data[lower:upper]
            return entry - self.offsets[batch_id]

    @property
    def index(self):
        """Alias for the underlying data stored.

        Returns
        -------
        Union[np.ndarray, torch.Tensor]
            Underlying index
        """
        assert not self.is_list, (
                "Underlying data is not a single index, use `index_list`")

        return self.data

    @property
    def index_list(self):
        """Alias for the underlying data list stored.

        Returns
        -------
        List[Union[np.ndarray, torch.Tensor]]
            Underlying index list
        """
        assert self.is_list, (
                "Underlying data is a single index, use `index`")

        return self.data

    @property
    def full_index(self):
        """Returns the index combining all sub-indexes, if relevant.

        Returns
        -------
        Union[np.ndarray, torch.Tensor]
            (N) Complete concatenated index
        """
        if not self.is_list:
            return self.data
        else:
            return self._cat(self.data) if len(self.data) else self._empty(0)

    @property
    def batch_ids(self):
        """Returns the batch ID of each index in the list.

        Returns
        -------
        Union[np.ndarray, torch.Tensor]
            (I) Batch ID array, one per index in the list
        """
        return self._repeat(self._arange(self.batch_size), self.counts)

    @property
    def full_batch_ids(self):
        """Returns the batch ID of each element in the full index list.

        Returns
        -------
        Union[np.ndarray, torch.Tensor]
            (N) Complete batch ID array, one per element
        """
        return self._repeat(self._arange(self.batch_size), self.full_counts)

    def split(self):
        """Breaks up the index batch into its constituents.

        Returns
        -------
        List[List[Union[np.ndarray, torch.Tensor]]]
            List of list of indexes per entry in the batch
        """
        indexes = self._split(self.data, self.splits)
        for batch_id in range(self.batch_size):
            indexes[batch_id] = indexes[batch_id] - self.offsets[batch_id]

        return indexes

    def to_numpy(self):
        """Cast underlying index to a `np.ndarray` and return a new instance.

        Returns
        -------
        TensorBatch
            New `TensorBatch` object with an underlying np.ndarray tensor.
        """
        # If the underlying data is of the right type, nothing to do
        if self.is_numpy:
            return self

        to_numpy = lambda x: x.cpu().detach().numpy()
        if not self.is_list:
            data = to_numpy(self.data)
        else:
            data = np.empty(len(data), dtype=object)
            for i in range(len(self.data)):
                data[i] = to_numpy(self.data[i])

        offsets = to_numpy(self.offsets)
        counts = to_numpy(self.counts)
        full_counts = to_numpy(self.full_counts)

        return IndexBatch(data, offsets, counts, full_counts)

    def to_tensor(self, dtype=None, device=None):
        """Cast underlying index to a `torch.tensor` and return a new instance.

        Parameters
        ----------
        dtype : torch.dtype, optional
            Data type of the tensor to create
        device : torch.device, optional
            Device on which to put the tensor

        Returns
        -------
        TensorBatch
            New `TensorBatch` object with an underlying np.ndarray tensor.
        """
        # If the underlying data is of the right type, nothing to do
        if not self.is_numpy:
            return self

        to_tensor = lambda x: torch.as_tensor(x, dtype=dtype, device=device)
        if not self.is_list:
            data = to_tensor(self.data)
        else:
            data = np.empty(len(data), dtype=object)
            for i in range(len(self.data)):
                data[i] = to_tensor(self.data[i])

        offsets = to_tensor(self.offsets)
        counts = to_tensor(self.counts)
        full_counts = to_tensor(self.full_counts)

        return IndexBatch(index, offsets, counts, full_counts)
