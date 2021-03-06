"""A simple wrapper for Random Tree regression"""

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from copy import deepcopy
from collections import Counter


class RTLearner(object):

    def __init__(self, leaf_size=1, verbose=False, tree=None):
        """Initalize a Random Tree Learner

        Parameters:
        leaf_size: The maximum number of samples to be aggregated at a leaf. 
        verbose: If True, information about the learner will be printed out
        tree: If None, the learner instance has no data. If not None, tree is a numpy ndarray. 
        Its columns are the features of data and its rows are the individual samples. The four 
        columns are feature indices (index for a leaf is -1), splitting values (or Y values for
        leaves), and starting rows, from the current root, for its left and right subtrees (if any)
        
        Returns: A instance of Random Tree Learner
        """
        self.leaf_size = leaf_size
        self.verbose = verbose
        self.tree = deepcopy(tree)
        if verbose:
            self.get_learner_info()
        

    def __build_tree(self, dataX, dataY):
        """Builds the Random Tree recursively by randomly choosing a feature to split on. 
        The splitting value is the mean of feature values of two random rows. If none of the 
        features can split the data into two groups, return leaf

        Parameters:
        dataX: A numpy ndarray of X values at each node
        dataY: A numpy 1D array of Y values at each node
        
        Returns:
        tree: A numpy ndarray. Its columns are the features of data and its rows are the 
        individual samples. The four columns are feature indices (index for a leaf is -1), 
        splitting values(or Y values for leaves), and starting rows, from the current root, 
        for its left and right subtrees (if any)

        """
        # Get the number of samples (rows) and features (columns) of dataX
        num_samples = dataX.shape[0]
        num_feats = dataX.shape[1]

        # Leaf value is the most common dataY
        leaf = np.array([-1, Counter(dataY).most_common(1)[0][0], np.nan, np.nan])
        
        # If there are <= leaf_size samples or all data in dataY are the same, return leaf
        if num_samples <= self.leaf_size or len(np.unique(dataY)) == 1:
            return leaf
        
        avail_feats_for_split = list(range(num_feats))

        # If a randomly-chosen feature can't split the data, choose another one randomly
        while len(avail_feats_for_split) > 0:
            # Randomly choose a feature to split on
            rand_feat_i = np.random.choice(avail_feats_for_split)

            # Randomly choose two rows
            rand_rows = [np.random.randint(0, num_samples), np.random.randint(0, num_samples)]
            
            # If the two rows are the same, reselect them until they are different
            while rand_rows[0] == rand_rows[1] and num_samples > 1:
                rand_rows = [np.random.randint(0, num_samples), np.random.randint(0, num_samples)]

            # Split the data by computing the mean of feature values of two random rows
            split_val = np.mean([dataX[rand_rows[0], rand_feat_i], 
                            dataX[rand_rows[1], rand_feat_i]])

            # Logical arrays for indexing
            left_index = dataX[:, rand_feat_i] <= split_val
            right_index = dataX[:, rand_feat_i] > split_val

            # If we can split the data into two groups, then break out of the loop            
            if len(np.unique(left_index)) != 1:
                break
            
            avail_feats_for_split.remove(rand_feat_i)
        
        # If we complete the while loop and run out of features to split, return leaf
        if len(avail_feats_for_split) == 0:
            return leaf

        # Build left and right branches and the root
        lefttree = self.__build_tree(dataX[left_index], dataY[left_index])
        righttree = self.__build_tree(dataX[right_index], dataY[right_index])

        # Set the starting row for the right subtree of the current root
        if lefttree.ndim == 1:
            righttree_start = 2 # The right subtree starts 2 rows down
        elif lefttree.ndim > 1:
            righttree_start = lefttree.shape[0] + 1
        root = np.array([rand_feat_i, split_val, 1, righttree_start])

        return np.vstack((root, lefttree, righttree))
        

    def __tree_search(self, point, row):
        """A private function to be used with query. It recursively searches 
        the random tree matrix and returns a predicted value for point

        Parameters:
        point: A numpy 1D array of test query
        row: The row of the random tree matrix to search
    
        Returns 
        pred: The predicted value
        """

        # Get the feature on the row and its corresponding splitting value
        feat, split_val = self.tree[row, 0:2]
        
        # If splitting value of feature is -1, we have reached a leaf so return it
        if feat == -1:
            return split_val

        # If the corresponding feature's value from point <= split_val, go to the left tree
        elif point[int(feat)] <= split_val:
            pred = self.__tree_search(point, row + int(self.tree[row, 2]))

        # Otherwise, go to the right tree
        else:
            pred = self.__tree_search(point, row + int(self.tree[row, 3]))
        
        return pred


    def addEvidence(self, dataX, dataY):
        """Add training data to learner

        Parameters:
        dataX: A numpy ndarray of X values of data to add
        dataY: A numpy 1D array of Y training values

        Returns: An updated tree matrix for RTLearner
        """

        new_tree = self.__build_tree(dataX, dataY)

        # If self.tree is currently None, simply assign new_tree to it
        if self.tree is None:
            self.tree = new_tree

        # Otherwise, append new_tree to self.tree
        else:
            self.tree = np.vstack((self.tree, new_tree))

        # If there is only a single row, expand tree to a numpy ndarray for consistency
        if len(self.tree.shape) == 1:
            self.tree = np.expand_dims(self.tree, axis=0)
        
        if self.verbose:
            self.get_learner_info()
        
        
    def query(self, points):
        """Estimates a set of test points given the model we built
        
        Parameters:
        points: A numpy ndarray of test queries

        Returns: 
        preds: A numpy 1D array of the estimated values
        """

        preds = []
        for point in points:
            preds.append(self.__tree_search(point, row=0))
        return np.asarray(preds)


    def get_learner_info(self):
        print ("leaf_size =", self.leaf_size)
        if self.tree is not None:
            print ("tree shape =", self.tree.shape)
            print ("tree as a matrix:")
            # Create a dataframe from tree for a user-friendly view
            df_tree = pd.DataFrame(self.tree, 
                columns=["factor", "split_val", "left", "right"])
            df_tree.index.name = "node"
            print (df_tree)
        else:
            print ("Tree has no data")
        print ("")


if __name__=="__main__":
    print ("This is a Random Tree Learner\n")

    # Some data to test the RTLearner
    x0 = np.array([0.885, 0.725, 0.560, 0.735, 0.610, 0.260, 0.500, 0.320])
    x1 = np.array([0.330, 0.390, 0.500, 0.570, 0.630, 0.630, 0.680, 0.780])
    x2 = np.array([9.100, 10.900, 9.400, 9.800, 8.400, 11.800, 10.500, 10.000])
    x = np.array([x0, x1, x2]).T
    
    y = np.array([4.000, 5.000, 6.000, 5.000, 3.000, 8.000, 7.000, 6.000])

    # Create a tree learner from given train X and y
    rtl = RTLearner(verbose=True, leaf_size=1)
    print ("\nAdd data")
    rtl.addEvidence(x, y)

    print ("\nCreate another tree learner from an existing tree")
    rtl2 = RTLearner(tree=rtl.tree)

    # rtl2 should have the same tree as rtl
    assert np.any(rtl.tree == rtl2.tree)

    rtl2.get_learner_info()

    # Modify the rtl2.tree and assert that this doesn't affect rtl.tree
    rtl2.tree[0] = np.arange(rtl2.tree.shape[1])
    assert np.any(rtl.tree != rtl2.tree)

    # Query with dummy data
    rtl.query(np.array([[1, 2, 3], [0.2, 12, 12]]))

    # Another dataset to test that "If the best feature doesn't split the data into two
    # groups, choose the second best one and so on; if none of the features does, return leaf"
    print ("Another dataset for testing")
    x2 = np.array([
     [  0.26,    0.63,   11.8  ],
     [  0.26,    0.63,   11.8  ],
     [  0.32,    0.78,   10.   ],
     [  0.32,    0.78,   10.   ],
     [  0.32,    0.78,   10.   ],
     [  0.735,   0.57,    9.8  ],
     [  0.26,    0.63,   11.8  ],
     [  0.61,    0.63,    8.4  ]])
        
    y2 = np.array([ 8.,  8.,  6.,  6.,  6.,  5.,  8.,  3.])
        
    rtl3 = RTLearner(verbose=True)
    rtl3.addEvidence(x2, y2)