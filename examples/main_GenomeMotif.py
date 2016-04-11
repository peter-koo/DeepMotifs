#/bin/python
import sys
import os
import numpy as np
sys.path.append('..')
from src import NeuralNet
from src import train_minibatch, test_model_all
from src import make_directory 
from models import load_model
from data import load_data
np.random.seed(247) # for reproducibility
import sys, os
sys.path.append(os.path.join(os.path.realpath('..')))
from src import build_network

#------------------------------------------------------------------------------
# load data

name = 'DeepSea'
datapath = '/home/peter/Data/DeepSea'
options = {"num_include": 1000000, "class_range": range(100)}
train, valid, test = load_data(name, datapath, options)
shape = (None, train[0].shape[1], train[0].shape[2], train[0].shape[3])
num_labels = np.round(train[1].shape[1])

#-------------------------------------------------------------------------------------

# load model parameters
model_name = "genome_motif_model"
network, input_var, target_var, optimization = load_model(model_name, shape, num_labels)

# build model
nnmodel = NeuralNet(network, input_var, target_var, optimization)

# set output file paths
outputname = 'binary'
datapath = make_directory(datapath, 'Results')
filepath = os.path.join(datapath, outputname)

# train model
nnmodel = train_minibatch(nnmodel, train, valid, batch_size=256, num_epochs=500, patience=5, verbose=1, filepath=filepath)

# set best model --> lowest cross-validation error
nnmodel.set_best_model(filepath)

# save best model
savepath = filepath + "_best.pickle"
nnmodel.save_model_parameters(savepath)

# test set perfomance
nnmodel.test_model(test, "test")

# save all performance metrics (train, valid, test)
nnmodel.save_all_metrics(filepath)

# monitor/save test performance with parameters for each training epoch
num_train_epochs = nnmodel.get_num_epochs()
performance = test_model_all(nnmodel, test, num_train_epochs, filepath)

# save test performance
performance.save_metrics(filepath)











