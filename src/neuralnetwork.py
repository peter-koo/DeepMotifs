#!/bin/python
import os
import sys
import numpy as np
from six.moves import cPickle
import time
import theano
import theano.tensor as T
from lasagne import layers, nonlinearities, objectives, updates, regularization, init
from utils import calculate_metrics, batch_generator

#------------------------------------------------------------------------------------------
# Neural Network model class
#------------------------------------------------------------------------------------------

class NeuralNets:
	"""Class to build and train a feed-forward neural network"""

	def __init__(self, layers, input_var, target_var, optimization):

		# build model 
		network, train_fun, test_fun = build_model(model_layers, input_var, target_var, optimization)

		self.network = network
		self.train_fun = train_fun
		self.test_fun = test_fun
		self.best_parameters = []
		self.train_monitor = MonitorPerformance(name="train")
		self.test_monitor = MonitorPerformance(name=" test")
		self.valid_monitor = MonitorPerformance(name="cross-validation")
		self.num_train_epochs = 0


	def get_model_parameters(self):
		return layers.get_all_param_values(self.network)


	def set_model_parameters(self, all_param_values):
		self.network = layers.set_all_param_values(self.network, all_param_values)


	def save_model_parameters(self, filepath):
		print "saving model parameters to: " + filepath
		all_param_values = layers.get_all_param_values(self.network)
		f = open(filepath, 'wb')
		cPickle.dump(all_param_values, f, protocol=cPickle.HIGHEST_PROTOCOL)
		f.close()


	def set_best_model(self, filepath):
		min_cost, min_index = self.valid_monitor.get_min_cost()    
		savepath = filepath + "_" + str(min_index) + ".pickle"
		f = open(savepath, 'rb')
		self.best_parameters = cPickle.load(f)
		f.close()
		self.set_model_parameters(self.best_parameters)


	def test_results(self, test):
		test_cost, test_prediction = self.test_fun(test[0].astype(np.float32), test[1].astype(np.int32)) 
		return test_cost, test_prediction


	def epoch_train(self,  mini_batches, num_batches, verbose):        
		"""Train a mini-batch --> single epoch"""

		# set timer for epoch run
		performance = MonitorPerformance(verbose)
		performance.set_start_time(start_time = time.time())

		# train on mini-batch with random shuffling
		epoch_cost = 0
		for index in range(num_batches):
			X, y = next(mini_batches)
			cost, prediction = self.train_fun(X, y)
			epoch_cost += cost
			performance.progress_bar(index, num_batches, epoch_cost/(index+1))
		print "" 
		return epoch_cost/num_batches


	def train_model(self, train, valid, batch_size=128, num_epochs=500, 
					patience=10, verbose=1, filepath='.'):
		"""Train a model with cross-validation data and test data"""
		# setup generator for mini-batches
		num_train_batches = len(train[0]) // batch_size
		train_batches = batch_generator(train[0], train[1], batch_size)

		# train model
		for epoch in range(num_epochs):
			if verbose == 1:
				sys.stdout.write("\rEpoch %d out of %d \n"%(epoch+1, num_epochs))

			# training set
			train_cost = self.epoch_train(train_batches, num_train_batches, verbose)
			self.train_monitor.add(train_cost)

			# validation set
			valid_cost, valid_prediction = self.test_results(valid)		
			self.valid_monitor.update(valid_cost, valid_prediction, valid[1])
			self.valid_monitor.print_results("valid", epoch, num_epochs) 

			# save model
			if filepath:
				self.num_train_epochs += 1
				savepath = filepath + "_" + str(epoch) + ".pickle"
				self.save_model_parameters(savepath)

			# check for early stopping					
			status = self.valid_monitor.early_stopping(valid_cost, epoch, patience)
			if not status:
				break


	def save_best_model(self, filepath):
		""" update model with best parameters on cross-validation and save"""
		self.set_best_model(filepath)
		savepath = filepath + "_best.pickle"
		self.save_model_parameters(savepath)


	def test_model(self, test):
		test_cost, test_prediction = self.test_results(test)
		self.test_monitor.update(test_cost, test_prediction, test[1])
		self.test_monitor.print_results("test")   


	def save_metrics(self, filepath, name):
		if name == "train":
			self.train_monitor.save_metrics(filepath)
		elif name == "test":
			self.test_monitor.save_metrics(filepath)
		elif name == "valid":
			self.valid_monitor.save_metrics(filepath)


	def save_all_metrics(self, filepath):
		self.save_metrics(filepath, "train")
		self.save_metrics(filepath, "test")
		self.save_metrics(filepath, "valid")


	def test_model_all(self, test, filepath):
		"""loops through training parameters for epochs min_index 
		to max_index located in filepath and calculates metrics for 
		test data """

		performance = MonitorPerformance("test_all")
		for epoch in range(self.num_train_epochs):
			if verbose == 1:
				sys.stdout.write("\rEpoch %d out of %d \n"%(epoch+1, self.num_train_epochs))
			
			# load model parameters for a given training epoch
			savepath = filepath + "_" + str(min_index) + ".pickle"
			f = open(savepath, 'rb')
			self.best_parameters = cPickle.load(f)
			f.close()

			self.set_model_parameters(self.best_parameters)
			test_cost, test_prediction = self.test_results(test)
			self.performance.update(test_cost, test_prediction, test[1])
			self.valid_monitor.print_results("test", epoch, num_epochs) 

		self.valid_monitor.save_metrics(filepath)


#----------------------------------------------------------------------------------------------------
# Monitor performance metrics class
#----------------------------------------------------------------------------------------------------

class MonitorPerformance():
	"""helper class to monitor and store performance metrics during 
	   training. This class uses the metrics for early stopping. """

	def __init__(self, name = '', verbose=1):
		self.cost = []
		self.metric = np.empty(3)
		self.metric_std = np.empty(3)
		self.verbose = verbose
		self.name = name
		self.roc = []
		self.pr = []


	def set_verbose(self, verbose):
		self.verbose = verbose


	def get_metrics(self, prediction, label):
		mean, std, roc, pr = calculate_metrics(label, prediction)
		self.roc = roc
		self.pr = pr 
		return mean, std, roc, pr


	def add(self, cost, mean=[], std=[]):
		self.cost.append(cost)
		if mean:
			self.metric = np.vstack([self.metric, mean])
		if std:
			self.metric_std = np.vstack([self.metric_std, std])


	def update(self, cost, prediction, label):
		mean, std, roc, pr = self.get_metrics(prediction, label)
		self.add(cost, mean, std)


	def get_mean_values(self):
		results = self.metric[-1,:]
		return results[0], results[1], results[2]


	def get_error_values(self):
		results = self.metric_std[-1,:]
		return results[0], results[1], results[2]


	def get_min_cost(self):
		min_cost = min(self.cost)
		min_index = np.argmin(self.cost)
		return min_cost, min_index


	def early_stopping(self, current_cost, current_epoch, patience):
		min_cost, min_epoch = self.get_min_cost()
		status = True
		if min_cost < current_cost:
			if patience - (current_epoch - min_epoch) < 0:
				status = False
				print "Patience ran out... Early stopping."
		return status


	def set_start_time(self, start_time):
		if self.verbose == 1:
			self.start_time = start_time


	def print_results(self, name, epoch=0, num_epochs=0): 
		if self.verbose == 1:
			accuracy, auc_roc, auc_pr = self.get_mean_values()
			accuracy_std, auc_roc_std, auc_pr_std = self.get_error_values()
			print("  " + name + " cost:\t\t{:.4f}".format(self.cost[-1]/1.))
			print("  " + name + " accuracy:\t{:.4f}+/-{:.4f}".format(accuracy, accuracy_std))
			print("  " + name + " auc-roc:\t{:.4f}+/-{:.4f}".format(auc_roc, auc_roc_std))
			print("  " + name + " auc-pr:\t\t{:.4f}+/-{:.4f}".format(auc_pr, auc_pr_std))
			#print("  " + name + " accuracy:\t{:.2f} %".format(float(accuracy)*100))


	def progress_bar(self, index, num_batches, cost, bar_length=30):
		if self.verbose == 1:
			remaining_time = (time.time()-self.start_time)*(num_batches-index-1)/(index+1)
			percent = (index+1.)/num_batches
			progress = '='*int(round(percent*bar_length))
			spaces = ' '*int(bar_length-round(percent*bar_length))
			sys.stdout.write("\r[%s] %.1f%% -- time=%ds -- cost=%.4f" \
			%(progress+spaces, percent*100, remaining_time, cost))
			sys.stdout.flush()


	def save_metrics(self, filepath):
		savepath = filepath + "_" + self.name +".pickle"
		
		f = open(savepath, 'wb')
		cPickle.dump(self.name, f, protocol=cPickle.HIGHEST_PROTOCOL)
		cPickle.dump(self.cost, f, protocol=cPickle.HIGHEST_PROTOCOL)
		cPickle.dump(self.metric, f, protocol=cPickle.HIGHEST_PROTOCOL)
		cPickle.dump(self.metric_std, f, protocol=cPickle.HIGHEST_PROTOCOL)
		cPickle.dump(self.roc, f, protocol=cPickle.HIGHEST_PROTOCOL)
		cPickle.dump(self.pr, f, protocol=cPickle.HIGHEST_PROTOCOL)
		f.close()


#------------------------------------------------------------------------------------------
# Neural network model building functions
#------------------------------------------------------------------------------------------

def build_model(model_layers, input_var, target_var, optimization):

	# build model based on layers
	network = build_layers(model_layers, input_var)

	# build cost function
	prediction = layers.get_output(network, deterministic=False)
	cost = build_cost(network, target_var, prediction, optimization)

	# calculate and clip gradients
	params = layers.get_all_params(network, trainable=True)    
	if "weight_norm" in optimization:
		grad = calculate_gradient(network, cost, params, weight_norm=optimization["weight_norm"])
	else:
		grad = calculate_gradient(network, cost, params)
	  
	# setup parameter updates
	update_op = optimizer(grad, params, optimization)

	# test/validation set 
	test_prediction = layers.get_output(network, deterministic=True)
	test_cost = build_cost(network, target_var, test_prediction, optimization)

	# create theano function
	train_fun = theano.function([input_var, target_var], [cost, prediction], updates=update_op)
	test_fun = theano.function([input_var, target_var], [test_cost, test_prediction])

	return network, train_fun, test_fun


def build_layers(model_layers, input_var):
	""" build all layers in the model """

	def single_layer(model_layer, network=[]):
		""" build a single layer"""
		# input layer
		if model_layer['layer'] == 'input':
			network = layers.InputLayer(layer['shape'], input_var=model_layer['input_var'])

		# dense layer
		elif model_layer['layer'] == 'dense':
			network = layers.DenseLayer(network, num_units=model_layer['num_units'],
												 W=model_layer['W'],
												 b=model_layer['b'])

		# convolution layer
		elif model_layer['layer'] == 'convolution':
			network = layers.Conv2DLayer(network, num_filters = model_layer['num_filters'],
												  filter_size = model_layer['filter_size'],
											 	  W=model_layer['W'],
										   		  b=model_layer['b'])
		return network

	# loop to build each layer of network
	network = []
	for model_layer in model_layers:

		# create base layer
		network = single_layer(model_layer, network)
				
		# add Batch normalization layer
		if 'norm' in model_layer:
			if model_layer['norm'] == 'batch':
				network = layers.BatchNormLayer(network)

		# add activation layer
		if 'activation' in model_layer:
			network = activation_layer(network, model_layer['activation']) 
			
		# add dropout layer
		if 'dropout' in model_layer:
			layers.DropoutLayer(network, p=model_layer['dropout'])

		# add max-pooling layer
		if model_layer['layer'] == 'convolution':            
			network = layers.MaxPool2DLayer(network, pool_size=model_layer['pool_size'])

	return network


def activation_layer(network, activation):

	if activation == 'prelu':
		network = layers.ParametricRectifierLayer(network,
												  alpha=init.Constant(0.25),
												  shared_axes='auto')
	elif activation == 'sigmoid':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.sigmoid)

	elif activation == 'softmax':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.softmax)

	elif activation == 'linear':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.linear)

	elif activation == 'tanh':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.tanh)

	elif activation == 'softplus':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.softplus)

	elif activation == 'leakyrelu':
			network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.leaky_rectify)
	
	elif activation == 'veryleakyrelu':
			network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.very_leaky_rectify)
		
	elif activation == 'relu':
		network = layers.NonlinearityLayer(network, nonlinearity=nonlinearities.rectify)
	
	return network


def build_cost(network, target_var, prediction, optimization):
	""" setup cost function with weight decay regularization """

	if optimization["objective"] == 'categorical':
		cost = objectives.categorical_crossentropy(prediction, target_var)
	elif optimization["objective"] == 'binary':
		cost = objectives.binary_crossentropy(prediction, target_var)
	elif optimization["objective"] == 'mse':
		cost = objectives.squared_error(prediction, target_var)
	cost = cost.mean()

	# weight-decay regularization
	if "l1" in optimization:
		l1_penalty = regularization.regularize_network_params(network, l1) * optimization["l1"]
		test_cost += l1_penalty
	if "l2" in optimization:
		l2_penalty = regularization.regularize_network_params(network, l2) * optimization["l2"]        
		test_cost += l2_penalty 

	return cost


def calculate_gradient(network, cost, params, weight_norm=[]):
	""" calculate gradients with option to clip norm """
	# calculate gradients
	grad = T.grad(cost, params)

	# gradient clipping option
	if weight_norm:
		grad = updates.total_norm_constraint(grad, weight_norm)

	return grad


def optimizer(grad, params, update_params):
	""" setup optimization algorithm """

	if update_params['optimizer'] == 'sgd':
		update_op = updates.sgd(grad, params, learning_rate=update_params['learning_rate']) 
 
	elif update_params['optimizer'] == 'nesterov_momentum':
		update_op = updates.nesterov_momentum(grad, params, 
									learning_rate=update_params['learning_rate'], 
									momentum=update_params['momentum'])
	
	elif update_params['optimizer'] == 'adagrad':
		if "learning_rate" in update_params:
			update_op = updates.adagrad(grad, params, 
							  learning_rate=update_params['learning_rate'], 
							  epsilon=update_params['epsilon'])
		else:
			update_op = updates.adagrad(grad, params)

	elif update_params['optimizer'] == 'rmsprop':
		if "learning_rate" in update_params:
			update_op = updates.rmsprop(grad, params, 
							  learning_rate=update_params['learning_rate'], 
							  rho=update_params['rho'], 
							  epsilon=update_params['epsilon'])
		else:
			update_op = updates.rmsprop(grad, params)
	
	elif update_params['optimizer'] == 'adam':
		if "learning_rate" in update_params:
			update_op = updates.adam(grad, params, 
							learning_rate=update_params['learning_rate'], 
							beta1=update_params['beta1'], 
							beta2=update_params['beta2'], 
							epsilon=update['epsilon'])
		else:
			update_op = updates.adam(grad, params)
  
	return update_op


